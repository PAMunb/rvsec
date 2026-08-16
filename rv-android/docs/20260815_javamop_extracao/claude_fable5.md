# Lista de extração — claude_fable5 (validação externa 1)

**Fonte:** `docs/20260815_javamop_mensagens_claude_fable5.md` (751 linhas), lida integralmente.
**Alvo do casamento:** `docs/20260815_javamop_mensagens_FINAL.md` (521 linhas), lido integralmente.
**Total de itens:** 193 | carregados: 148 | parciais: 23 | ausentes: 22

Convenções: cada item é registrado na sua **primeira aparição** no arquivo-fonte; quando o mesmo
conteúdo reaparece com rótulo próprio mais adiante (tipicamente na tabela §5 `A1..A25`), o rótulo
duplo é anotado na coluna "rótulo próprio". Classes: `c-plano` = correção ao plano, `c-review` =
correção ao review, `anom` = anomalia nova, `prop` = proposta, `verif` = verificação confirmatória.

Mapa dos rótulos §5 da fonte para os IDs desta lista (é por esse mapa que o §4 do FINAL referencia
`c-C1..c-C25`): A1→C-113 · A2→C-082/C-083 · A3→C-090 · A4→C-093 · A5→C-087 · A6→C-097 · A7→C-066 ·
A8→C-140 · A9→C-067 + C-157 · A10→C-069 · A11→C-158 · A12→C-078 · A13→C-073 · A14→C-076 ·
A15→C-159 · A16→C-160 · A17→C-124 · A18→C-131 · A19→C-130 · A20→C-161 · A21→C-106 · A22→C-112 ·
A23→C-162 · A24→C-163 · A25→C-020.

| ID | linha | bloco | rótulo próprio | classe | conteúdo | status | onde no FINAL |
|---|---|---|---|---|---|---|---|
| C-001 | 32-42 | §1 veredito do plano | sem rótulo | c-plano | O diagnóstico e o pilar do plano se sustentam, mas o plano erra em quatro detalhes de mecanismo dos quais seus próprios workstreams dependem; "não executável como escrito, metade do registro sobrevive" | CARREGADO | FINAL:64-77 (F1-F4), FINAL:110-113 |
| C-002 | 38 | §1 veredito do plano | sem rótulo | c-plano | Plano está desatualizado quanto a gh100/gh101/auditoria/Estudo 03 | CARREGADO | FINAL:113 (c-A5), FINAL:73 (F10) |
| C-003 | 39 | §1 veredito do plano | sem rótulo | c-plano | Três números de manchete não reproduzem sob nenhuma definição: 73,4 %, 28 achados, grupo de 3.098 linhas | CARREGADO | FINAL:114 (c-A6..A15), FINAL:72 (F9) |
| C-004 | 40 | §1 veredito do plano | sem rótulo | c-plano | Dois "falsos positivos" do plano são semântica CrySL (D05, D06 contra as regras 1.5.2) | CARREGADO | FINAL:117 (c-A18..A20), FINAL:76 (F13) |
| C-005 | 41 | §1 veredito do plano | sem rótulo | c-plano | Um defeito de severidade A do plano (D17, `AndroidKeyStore`) é escolha de oráculo, não defeito de tradução | CARREGADO | FINAL:117, FINAL:280 (§5.3) |
| C-006 | 42 | §1 veredito do plano | sem rótulo | c-plano | Como sequenciado, o plano não tem conjunto-alvo admissível | CARREGADO | FINAL:83-88 (§3), FINAL:291 (D-A) |
| C-007 | 44-46 | §1 veredito do review | sem rótulo | verif | As 52 citações `file:line` decisórias do review foram reabertas: todas CONFIRMADAS ou erradas por uma linha; suas remedições, deixadas sem rastro, reproduzem (V2) | AUSENTE | — |
| C-008 | 47-48 | §1 veredito do review | sem rótulo | c-review | Review diz que gh101 "registra" a reversão `e204e2a4`; nada em gh101 registra | CARREGADO | FINAL:135 (c-B1), FINAL:504 (§10) |
| C-009 | 48-52 | §1 veredito do review | sem rótulo | c-review + anom | Review diz que o caso PKIX em `TrustManagerFactorySpec` "é fechado pelo merge do gh100"; o merge trocou o sintoma `found .` por dois registros mudos por fluxo correto, porque o wrapper mesclado dispara `g1` e `g2` em todo `getInstance` de um argumento | CARREGADO | FINAL:136 (c-B2), FINAL:219-246 (§5.1) |
| C-010 | 52-53 | §1 veredito do review | sem rótulo | c-review | Review chama o `CipherSpec` do `jca` de "fiel" a `Cipher.crysl` enquanto `Init+` e `Update+` não estão traduzidos (auditoria ALFA-CIP-01/02) | CARREGADO | FINAL:137 (c-B3), FINAL:76 (F13), FINAL:275 |
| C-011 | 53-55 | §1 veredito do review | sem rótulo | c-review | Review nunca abre o oráculo api30 que governa `jca_android`, sob o qual o construtor de `KeyPair` é opcional (`co?`) e D06 se inverte | CARREGADO | FINAL:138 (c-B4), FINAL:279 |
| C-012 | 55-57 | §1 veredito do review | sem rótulo | c-review | O corte T0/T1 do review é uma opção, não a única; sua premissa "os primeiros lotes do E3 darão a re-baseline" está vencida: o Estudo 03 rodou em 2026-08-13 e o `errors.csv` de 19.664 linhas está em disco | CARREGADO | FINAL:139 (c-B10), FINAL:132 (c-A41) |
| C-013 | 59-63 | §1 três coisas derrubadas #1 | sem rótulo | c-plano | "L5c é a correção isolada de maior valor" é falso: 100 % dos frames reportados no E3 carregam número de linha (19.664/19.664); censo `dexdump` offline mostra 3,9 % dos métodos perdendo posições e 0 de 693 métodos tecidos | CARREGADO | FINAL:118 (c-A21/A22), FINAL:489 (O-8) |
| C-014 | 64-67 | §1 três coisas derrubadas #2 | sem rótulo | anom | E3 mostra `TrustManagerFactorySpec` com 2.855 `InvalidSequenceOfMethodCalls`, 98 % sem gêmeo, 0 `found .`, nas linhas de `getInstance` e de `init`; a fatia `unknown` subiu de 72,9 % para 79,9 % pós-reparo | CARREGADO | FINAL:236 (§5.1), FINAL:46 (§1) |
| C-015 | 68-71 | §1 três coisas derrubadas #3 | sem rótulo | c-plano + c-review | "`unknown` ⇔ `InvalidSequenceOfMethodCalls`" é verdade no dataset de 2026-07-06 e falso no E3: 419 linhas `UnsatisfiedConstraint` carregam `unknown` (`jca/IvParameterSpec.mop:48,55`, restaurados pelo gh100) | CARREGADO | FINAL:115 (c-A16, status U/R; o ponteiro "→ §7.2" é morto: §7.2 não trata disso) |
| C-016 | 73 | §1 três confirmadas (a) | sem rótulo | verif | O pilar confirmado: `JavaFSM.java:112-142,158`; `HandlerMethod.java:34-46,106`; `O99:7480-7487` | CARREGADO | FINAL:64-65 (F1, F2) |
| C-017 | 74-78 | §1 três confirmadas (b)(c) | sem rótulo | verif | Confirmadas as correções do review à mecânica do plano (prólogo `condition()`, `:604-610` morto, forma atômica vs sincronizada, `getState()/getLastEvent()` portáveis, compor antes do `__RESET`, `TrustManagerFactorySpec.mop:63`, `Property` = 25, `generic_new` `Log.v` = 39) e a explicação por colisão de wrapper dos 8.371 valores observados vazios | CARREGADO | FINAL:66-67 (F3,F4), FINAL:74 (F11), FINAL:120 |
| C-018 | 80-89 | §1 recomendação | sem rótulo | prop | Não implementar o plano como sequenciado nem adotar o corte do review sem mudanças; Rung 0 não é "esperar o E3" e sim "ler o E3 agora"; escalar imediatamente o achado `g1+g2 → sink` ao pesquisador porque incide sobre a validade do braço `jca` do Estudo 03; depois seguir a escada do §6 | CARREGADO | FINAL:190 (c-D1.0), FINAL:293 (D-C), FINAL:395-424 (§8) |
| C-019 | 115-118 | §2 método | sem rótulo | anom | O próprio prompt de validação erra o caminho de `JavaFSM.java` (dá `.../java/rvj/logicpluginshells/fsm/`; o arquivo está em `rv-monitor/rv-monitor/src/main/java/com/runtimeverification/rvmonitor/logicpluginshells/fsm/JavaFSM.java`) | AUSENTE | — |
| C-020 | 118-120 | §2 método | A25 | anom | O §6 rung 0 do prompt supõe que as saídas do Estudo 03 são futuras; elas existem, e `experimento-comp162/README.md:182-193` "Estado" continua dizendo "campanha não executada" | CARREGADO | FINAL:169 (c-C25), FINAL:430-431 (C-0 tarefa 3) |
| C-021 | 128 | §3 V1 tallies | sem rótulo | verif | Plano, 45 linhas de citação: 39 CONFIRMADAS, 3 IMPRECISAS, 2 ERRADAS, 1 NÃO VERIFICADA | AUSENTE | — |
| C-022 | 129 | §3 V1 tallies | sem rótulo | verif | Review, 52 linhas: 49 CONFIRMADAS, 2 IMPRECISAS, 0 ERRADAS, 1 NÃO VERIFICADA | AUSENTE | — |
| C-023 | 135 | §3 V1 tabela linha 1 | sem rótulo | c-plano | FSMMin só minimiza (`FSMMin.java:24-28,56-59`, Hopcroft `:139-222`); a completação do autômato está em `JavaFSM.java:112,136,141,158` | CARREGADO | FINAL:110 (c-A1), FINAL:64 (F1) |
| C-024 | 136 | §3 V1 tabela linha 2 | sem rótulo | c-plano | `BaseMonitor.java:604-610` é código morto (`rvj/parser/ast/rvmspec/EventDefinition.java:30` sem setter, `RVM_conditionFail` = 0 nos três oráculos); o caminho vivo é `javamop/.../mopspec/EventDefinition.java:151-156` + `RVDumpVisitor.java:47-51` → `O99:7385-7388` | CARREGADO | FINAL:111 (c-A2), FINAL:67 (F4) |
| C-025 | 137 | §3 V1 tabela linha 3 | sem rótulo | c-plano + c-review | `Prop_N_state`/`RVM_lastevent` só existem na forma sincronizada; a forma é decidida por parâmetro não vinculado (`BaseMonitor.java:158-163`, `:248-250`); contagens por `extends`: O99 15 atômicos / 8 sincronizados (o review dizia 16/23), OFZ 15/8, O101 18/5 | CARREGADO | FINAL:112 (c-A3), FINAL:120 (c-B5), FINAL:66 (F3) |
| C-026 | 138 | §3 V1 tabela linha 4 | sem rótulo | c-plano | Em `TrustManagerFactorySpec.mop` há dois defeitos: `:62` array duplo e `:63` tipo de retorno | CARREGADO | FINAL:120 (c-A26), FINAL:75 (F12), FINAL:498 (§10) |
| C-027 | 139 | §3 V1 tabela linha 5 | sem rótulo | c-plano | `Property` tem 25 constantes (`Property.java:8-55`); `git show 233df18a` acrescentou `GENERATED_CIPHER` e `MACED` | CARREGADO | FINAL:120 (c-A25), FINAL:498 (§10) |
| C-028 | 140 | §3 V1 tabela linha 6 | sem rótulo | c-plano | `addError` no `jca`: 51 textuais / 50 vivos (`MessageDigestSpec.mop:57` está comentado); 25 sítios mudos = 21 `@fail` + `PBEKeySpecSpec:24,30` + `IvParameterSpec.mop:48,55` | CARREGADO | FINAL:120 ("50 live sites"), FINAL:341 (§7.2, 21 + 4 sítios) |
| C-029 | 141 | §3 V1 tabela linha 7 | sem rótulo | c-plano | `generic_new` tem 39 chamadas `Log.v`, não 44 | CARREGADO | FINAL:120, FINAL:499 (§10) |
| C-030 | 142 | §3 V1 tabela linha 8 | sem rótulo | c-plano + c-review | O oráculo `.aj:979,984,1037` é `rvsec-mop/src/main/resources/jca/MultiSpec_1MonitorAspect.aj`, **git-ignored** (`rvsec-mop/.gitignore:2`), nem "untracked" (review) nem oráculo versionado (plano); o portão de congelamento não o enxerga | CARREGADO | FINAL:120 (c-A25), FINAL:145 (c-B20), FINAL:498 (§10) |
| C-031 | 143 | §3 V1 tabela linha 9 | sem rótulo | verif | `DexWriter.java:1156-1159` (plano) vs `:1155-1158` (review) fica NÃO VERIFICADO: jar externo não aberto; efeito concordado | AUSENTE | — |
| C-032 | 144 | §3 V1 tabela linha 10 | sem rótulo | c-review | O `O99:15921-15938` do review é a raiz de despacho de `unsafe_protocol`; o clone da raiz está em `O99:15992` dentro de `SSLContextSpec_initEvent` | CARREGADO | FINAL:120 (c-B7), FINAL:502 (§10) |
| C-033 | 146-148 | §3 V1 fecho | sem rótulo | verif | As lições 1–10 do §4 do prompt de validação estão todas CONFIRMADAS em fonte; a "segunda linha fabricada" da lição 8 é PROVADA para continuações com ≥5 vírgulas e apenas INFERIDA para o re-prefixamento de segmentos `\n` pelo logcat no dispositivo | CARREGADO | FINAL:70 (F7), FINAL:166 (c-C15) |
| C-034 | 156 | §3 V2 tabela linha 1 | sem rótulo | verif | Distribuição, 19 mensagens e `unknown` ⇔ InvSeq idênticos aos dois documentos, 0 contraexemplos; definição `unique_msg.split(':::')[3]` | CARREGADO | FINAL:72 (F9), FINAL:71 (F8) |
| C-035 | 157 | §3 V2 tabela linha 2 | sem rótulo | c-plano | Shadow/órfão: 26.152 (26,96 %) sob emparelhamento mínimo, 32.411 (33,41 %) sob co-localização; com `time` 26.103/32.232; a prosa do plano descreve co-localização mas o número é emparelhamento | CARREGADO | FINAL:72 (F9), FINAL:296 (D-F) |
| C-036 | 158 | §3 V2 tabela linha 3 | sem rótulo | anom | A tabela por especificação muda materialmente com a definição: sob co-localização `MessageDigest` é 99 % shadow (10.035/10.135) e `KeyStore` 29 % | AUSENTE | — |
| C-037 | 159 | §3 V2 tabela linha 4 | sem rótulo | verif | Sítios de contagem idêntica em TMF: 1.733/1.748 (e 4.587/4.602 com timeout) confirmados | AUSENTE | — |
| C-038 | 160 | §3 V2 tabela linha 5 | sem rótulo | c-plano | Granularidade de evento 46.330/20.507/32.232 confirmada; `time` é em segundos, inteiro 0..294, monótono dentro da execução, 17.174 linhas em time=0 | PARCIAL | FINAL:72 só carrega "`time` is seconds" |
| C-039 | 161 | §3 V2 tabela linha 6 | sem rótulo | verif | Funil 661 → 207 → 136 confirmado em ambos os documentos | CARREGADO | FINAL:114 ("funnel 24–59 by definition") |
| C-040 | 162 | §3 V2 tabela linha 7 | sem rótulo | c-plano | O "28" do último estágio não é reproduzível: 53 (9 prefixos de fornecedor) / 36 (+`okio.`) / 26 (pacote próprio de 2 segmentos) / 24 (3 segmentos); as três classes de exemplo do plano são de pacote próprio, então 28 ≈ 26 + ajuste manual | CARREGADO | FINAL:72 (F9), FINAL:114 |
| C-041 | 163 | §3 V2 tabela linha 8 | sem rótulo | c-plano | "73,4 % terceiros" não reproduz sob ~15 definições; nada cai em 73,0–73,9 %; a fatia `unknown` por ferramenta é 71–74 %, possível fonte da confusão | CARREGADO | FINAL:72 (F9), FINAL:114 (a hipótese de confusão com 71-74 % não é registrada) |
| C-042 | 164 | §3 V2 tabela linha 9 | sem rótulo | c-plano | 85,44 % só com `okio.` somado (4.050 linhas, ausente da lista do plano); 88,01 % só com o prefixo de 2 segmentos (pacote completo dá 89,82 %, 81 apps sem código próprio) | CARREGADO | FINAL:114 ("`okio.` needed for 85.44 %"), FINAL:296 |
| C-043 | 165 | §3 V2 tabela linha 10 | sem rótulo | c-plano | Chaves de amplificação idênticas; 11.761 é o *excesso* (N − distintos), não linhas; as linhas pertencentes a grupos totalmente idênticos são 20.323 (20,95 %) | AUSENTE | — |
| C-044 | 166 | §3 V2 tabela linha 11 | sem rótulo | c-plano | O maior grupo idêntico é 6 na chave de 10 colunas; 3.098 é a chave de 5 colunas (dankchat / SecureRandomSpec / Ktor `NonceKt` / `unknown`); 7 colunas dá 388, 8 dá 230 | CARREGADO | FINAL:72 (F9), FINAL:114 |
| C-045 | 167 | §3 V2 tabela linha 12 | sem rótulo | c-plano | O "grupo de 1.542 linhas" não está neste CSV (maior grupo por apk,rep,tool,unique_msg = 388); 1.542 e "24 timestamps em Platform.kt:83" vêm de outros diretórios de resultado — o plano mistura fontes sem dizer | AUSENTE | — |
| C-046 | 168 | §3 V2 tabela linha 13 | sem rótulo | verif | Censo de mensagens degeneradas confirmado (`but found .` 8.843/5; espaço faltando 2.005; reticências 109; com chaves 9/14.959; sem chaves 7/11.292; só maiúsculas 4; SHA-1/SHA1/SHA 2.340), com a ressalva de 9/11.299 se as duas mensagens `invalid key size` forem contadas | AUSENTE | — |
| C-047 | 169 | §3 V2 tabela linha 14 | sem rótulo | c-plano | Os 8.371 valores observados vazios em TMF se espalham por 62 apps: `Platform` 7.174, `TlsUtil` 584, `okhttp3.internal.Util` 324, Ktor 219, `AdvancedX509TrustManager` de pacote próprio 27+24, Conscrypt 19 — 96,5 % okhttp3, não 100 % ("okhttp" do plano é impreciso) | PARCIAL | FINAL:74 (F11) carrega os 8.371 e a colisão de wrapper; o recorte por classe e o "não é 100 % okhttp" se perderam |
| C-048 | 170 | §3 V2 tabela linha 15 | sem rótulo | verif | `found X509` 643, `UnsatisfiedConstraint` 0, 3 mensagens de `UnsafeProtocol`, 7 de `InvalidKeySize`: idênticos | CARREGADO | FINAL:74 (F11) |
| C-049 | 171 | §3 V2 tabela linha 16 | sem rótulo | c-plano | O perfil de sítios das 12.400 linhas de `SecureRandomSpec` da auditoria é exato (`kotlin.uuid...secureRandomBytes` 3.962; Ktor `NonceKt` 3.104; Tink 1.532; `secureRandomUuid` 1.229; gms 818; cadeia DRBG SpongyCastle ≈1.752) — refuta "a spec não emite mais nada" | PARCIAL | FINAL:74 (F11) diz apenas "site profile at `nextBytes`"; o perfil quantificado se perdeu |
| C-050 | 173-176 | §3 V2 novos MEDIDOS | sem rótulo | anom | Novo e MEDIDO: a fatia `unknown` é plana entre ferramentas (71,2–74,0 %) e entre timeouts (72,5–73,1 %) — é propriedade das specs/pipeline, não do driver; o volume é concentrado (top-5 apks = 32 % das linhas; SSLContextSpec + TrustManagerFactorySpec = 45,7 % do CSV); todo `unique_msg` parte em exatamente 5 pedaços, sem resíduo de `\n`/`:::` | AUSENTE | — |
| C-051 | 183 | §3 V2b tabela E3 linha 1 | sem rótulo | anom | E3: 19.664 linhas, 112 de 162 apks com erro, 3 ferramentas (`ape` 7.133; `aperv:mop_off_llm_off` 6.023; `aperv:mop_on_llm_off` 6.508), timeout 300 apenas | PARCIAL | FINAL:46 e FINAL:132 carregam 19.664; a composição por ferramenta e o 112/162 se perderam |
| C-052 | 184 | §3 V2b tabela E3 linha 2 | sem rótulo | anom | Distribuição de tipos no E3: InvSeq 77,78 %; UnsafeProto 7,46 %; **UnsatCons 6,90 % (1.357)**; UnsafeAlg 6,50 %; InvKST 1,35 %; InvKS 2 linhas — os 9 eventos restaurados pelo gh100 agora emitem | AUSENTE | — |
| C-053 | 185 | §3 V2b tabela E3 linha 3 | sem rótulo | anom | Mensagens distintas caíram de 19 (2026-07-06) para 16 no E3 | AUSENTE | — |
| C-054 | 186 | §3 V2b tabela E3 linha 4 | sem rótulo | anom | Fatia `unknown` no E3 = 79,91 % (80,9 / 79,6 / 79,2 por ferramenta): subiu | CARREGADO | FINAL:46 (§1, "79.9 %, 15,714 rows") |
| C-055 | 188 | §3 V2b tabela E3 linha 6 | sem rótulo | anom | Shadow no E3: 22,21 % (emparelhamento) / 28,08 % (co-localização); linhas mudas órfãs ainda são 55,6 % do CSV | AUSENTE | — |
| C-056 | 189 | §3 V2b tabela E3 linha 7 | sem rótulo | anom | Três novas famílias de gêmeos 1:1 no E3 — SecretKeySpec 820/820, IvParameterSpec 419/419, PBEKeySpec 118/118 — órfãos restaurados que agora chegam ao DEX e afundam (mecanismo L2 do plano, ao vivo) | AUSENTE | — |
| C-057 | 190 | §3 V2b tabela E3 linha 8 | sem rótulo | anom | TMF no E3: 2.855 InvSeq; 21/543 sítios idênticos (razão 46,8); `found .` 0; `found X509` 61; mudo tanto na linha de `getInstance` quanto na de `init` (`Platform.kt:80` e `:83`) | CARREGADO | FINAL:236 (§5.1) |
| C-058 | 191 | §3 V2b tabela E3 linha 9 | sem rótulo | anom | `but found .` caiu de 8.843 para 98 no E3 (MessageDigest 55, Signature 39, Mac 4); o resíduo é algoritmo fora da allow-list sob o `jca` congelado | CARREGADO | FINAL:128 (c-A37), FINAL:381 (§7.6 critério 2) |
| C-059 | 192 | §3 V2b tabela E3 linha 10 | sem rótulo | anom | Funil no E3: 696 → 188 → 184 → 69/54/45, com as mesmas definições | AUSENTE | — |
| C-060 | 193 | §3 V2b tabela E3 linha 11 | sem rótulo | anom | Linhas de terceiros no E3: 80,04 / 84,81 / 87,34 %; 72 de 112 apps sem código próprio; `Platform` sozinho é 30,4 % | AUSENTE | — |
| C-061 | 194 | §3 V2b tabela E3 linha 12 | sem rótulo | anom | Maior grupo idêntico no E3: 2 na chave de 11 colunas (excesso 0,05 %); 7 na de 10 sem `source`; 1.152 na de 5 (laço Ktor no dankchat) — a coluna `source` separa as linhas | AUSENTE | — |
| C-062 | 195 | §3 V2b tabela E3 linha 13 | sem rótulo | anom | `SecureRandomSpec` no E3: 2.882 linhas (14,7 %), mesmo perfil de sítios (nonce Ktor 1.152; `secureRandomBytes` 731); o estrato `next2` não foi tocado pelo gh100 | PARCIAL | FINAL:242 diz "SR share unquantified"; o número e o perfil E3 se perderam, só o mecanismo `next2` sobrevive (FINAL:74) |
| C-063 | 196 | §3 V2b tabela E3 linha 14 | sem rótulo | anom | A coluna `source` existe no E3 e 100 % das linhas trazem `File:line`, 0 `Unknown Source`; 85 de 164 sítios têm mais de uma linha distinta; L5c não tem efeito mensurável sobre frames reportados | CARREGADO | FINAL:118 (c-A21/A22), FINAL:489 (O-8, marcado "U here") |
| C-064 | 198-200 | §3 V2b fecho | sem rótulo | verif | Previsões do review que se sustentam no E3 (aparece `UnsatisfiedConstraint`; sumiu o valor vazio de TMF; sumiu o gêmeo 1:1 de TMF; persiste o estrato `next2` do SRD) e as que não (PKIX fechado; valor observado vazio já entregue — 98 resíduos) | CARREGADO | FINAL:128 (c-A37), FINAL:136 (c-B2) |
| C-065 | 206 | §3 V3 linha 1 | A7 | anom | Novo: em `JavaFSM.java:154-158` um estado de usuário chamado literalmente `fail` é silenciosamente sobrescrito por `:158` — não consegue disparar `@fail` | CARREGADO | FINAL:159 (c-C7), FINAL:64 (F1) |
| C-066 | 206 | §3 V3 linha 1 | sem rótulo | verif | O sink é acrescentado, auto-laçado, com `fail condition = state == countState`; tanto `ere:` quanto `fsm:` chegam nele; FSMMin apenas minimiza | CARREGADO | FINAL:64 (F1) |
| C-067 | 207 | §3 V3 linha 2 | A9 (parte) | c-plano | `@fail` dispara depois de **todo** evento enquanto no sink; só uma vez por violação porque os handlers fazem `__RESET`; `KeyPairGeneratorSpec` (`jca:109-112`) não tem `__RESET` e re-reporta a cada evento posterior; o ponto de entrada ignora o booleano do método de evento e despacha sobre flags possivelmente obsoletas | CARREGADO | FINAL:130 (c-A39), FINAL:161 (c-C9), FINAL:64 (F1), FINAL:259-262 (§5.2) |
| C-068 | 208 | §3 V3 linha 3 | sem rótulo | verif | `__RESET` chama `this.reset()`, que limpa estado, põe lastevent em −1 e zera flags; as variáveis de spec sobrevivem | CARREGADO | FINAL:66 (F3) |
| C-069 | 209 | §3 V3 linha 4 | A10 | c-plano + anom | O plano erra ("nenhum `UnsafeProtocol` é emitido"): `getInstance("TLS")` sob `jca` dá 1 `UnsafeProtocol` + 2 mudos + contaminação; e o `__RESET` do fan-out joga todo monitor SSLContext vivo de volta para `start` (perda de estado, não só sobrescrita de variável) | CARREGADO | FINAL:116 (c-A17), FINAL:162 (c-C10), FINAL:68 (F5) |
| C-070 | 210 | §3 V3 linha 5 | sem rótulo | c-plano | IDs de evento seguem a ordem de declaração; IDs de estado vêm do FSMMin, que funde `start`/`unsafeAlg` no CipherSpec (6 colunas para 7 estados nomeados) e `start`/`unsafeProtocol` no SSLContext do O101 | CARREGADO | FINAL:77 (F14), FINAL:125 (c-A34) |
| C-071 | 211 | §3 V3 linha 6 | sem rótulo | c-plano | No `@fail`: portáveis são `getState()`/`getLastEvent()` (`IMonitor.java:19,25`); `getState()` já é o sink; o estado pré-falha não é guardado em lugar nenhum (só um `oldstate` local no `handleEvent` atômico); argumentos do evento não são visíveis; o objeto vinculado só via campo copiado ou `Ref_<param>` (apenas na forma sincronizada) | CARREGADO | FINAL:112 (c-A3/A4), FINAL:66 (F3), FINAL:332-343 (§7.2) |
| C-072 | 212 | §3 V3 linha 7 | sem rótulo | prop | `static final String[]` no bloco de declarações é viável pelo caminho da gramática (`javamop.jj:1276,1611-1623`; `DumpVisitor.java:207,814-826`; `RVParser.jj:253-254` texto cru; precedente `examples/ERE/SafeFileWriter/SafeFileWriter.mop:12`); nenhum `.mop` do rvsec usa campo estático; ressalva: uma linha de declaração que case com `event <nome>(` derruba a regex de texto cru | PARCIAL | FINAL:126 (c-A35) e FINAL:65 (F2) carregam a viabilidade e o gate G-1; a ressalva da regex `event <nome>(` se perdeu |
| C-073 | 213 | §3 V3 linha 8 | A13 | anom + prop | `RVM_loc` nunca é atribuído; **novo:** `__DEFAULT_MESSAGE` já é palavra-chave do gerador e `HandlerMethod.java:39-47` é uma tabela de substituição de 4 linhas — o lugar natural para um `__EVENTNAME`/`__PREVSTATE` | CARREGADO | FINAL:124 (c-A33), FINAL:165 (c-C13), FINAL:77 (F14), FINAL:482 (O-1) |
| C-074 | 215 | §3 V3 linha 10 | A/C-37 | anom | Fim de traço: `terminateInternal` retorna vazio; qualquer `@nome` faz parse e um nome desconhecido dá NPE em `BaseMonitor.java:332-334`; `endProgram/endThread/endObject` existem no JavaMOP, não são usados pelo rvsec e estão ausentes do dexlib2 | CARREGADO | FINAL:181 (c-C37), FINAL:77 (F14), FINAL:488 (O-7) |
| C-075 | 216 | §3 V3 linha 11 | A14 | anom + prop | `--internalbehavior` (`Main.java:414`; `BaseMonitor.java:410-413,1065-1085`) mantém por monitor uma `List<String>` de nomes de evento, clonada com o monitor, ilimitada, desligada por padrão — mecanismo de prefixo de traço já pronto | CARREGADO | FINAL:165 (c-C14), FINAL:77 (F14), FINAL:483 (O-2) |
| C-076 | 217 | §3 V3 linha 12 | A/C-26 | anom | `f1 = doFinal()` e `f2 = doFinal(..)` disparam ambos numa só chamada (wrapper pós-merge `WFZ:147-152`; `PointcutMatcher.java:367-370`); com o autômato do `jca` isso dá um registro mudo mais um reset espúrio depois do `init`, e nada depois do `update` | CARREGADO | FINAL:174 (c-C26), FINAL:76 (F13) |
| C-077 | 218 | §3 V3 linha 13 | A12 | anom | `GCMParameterSpecSpec.mop:23,34` declara dois `c1` e `:48` usa `ere : c1 \| c2`; símbolos ERE indefinidos passam pela geração em silêncio porque `FSMPlugin.java:55-64` checa a saída do FSM, onde `c2` já não aparece | CARREGADO | FINAL:164 (c-C12), FINAL:77 (F14), FINAL:264-265 (§5.2) |
| C-078 | 220-225 | §3 V3 implicações | sem rótulo | prop | Implicações para a mensagem no `@fail`: portáveis são `getState()`, `getLastEvent()`, campos de spec e `this.getClass()`; compor **antes** do `__RESET`; "expected one of" exige o estado pré-falha, obtido ou por uma linha de escrituração por corpo de evento (~170 linhas no `jca_android`) ou por mudança pequena no gerador; tabelas de **evento** escritas à mão são estáveis, tabelas de **estado** não são | CARREGADO | FINAL:125 (c-A34), FINAL:332-343 (§7.2), FINAL:482 (O-1) |
| C-079 | 233 | §3 V4 linha 1 | sem rótulo | c-plano | `doFinal()` logo após `init` (D05) não é falso positivo: é estritez do CrySL (`Cipher.crysl:75-76,85`, `A30/Cipher.cryptsl:107-117`); review está certo | CARREGADO | FINAL:76 (F13, "CrySL strictness"), FINAL:282 |
| C-080 | 234 | §3 V4 linha 2 | sem rótulo | c-plano | Re-`init` **depois** de um final (`end` sem `i1/i2`) também é conforme, porque `Init+` precede o grupo dos finais | PARCIAL | FINAL:275 funde tudo em "s2/s3 sem linhas de `init`, re-`init` antes do final é FP"; a distinção "depois de um final é conforme" desapareceu |
| C-081 | 235 | §3 V4 linha 3 | A2 (parte) | c-review + anom | Re-`init` **antes** de qualquer update/final (`s2` sem `i1/i2`, `jca:176-187`; `jca_android:302-310`) é defeito de tradução, persiste no gh101; o "a spec é fiel" do review está errado para a ORDER como um todo | CARREGADO | FINAL:137 (c-B3), FINAL:155 (c-C2), FINAL:275 (§5.3) |
| C-082 | 236 | §3 V4 linha 4 | A2 (parte) | anom | Multi-`update` antes de `doFinal` (`s3` sem auto-laço, `jca:188-195`; `jca_android:311-317`) é falso positivo realizável no padrão de streaming mais comum | CARREGADO | FINAL:155 (c-C2), FINAL:275, FINAL:422 (C-4) |
| C-083 | 237 | §3 V4 linha 5 | sem rótulo | anom | Mistura wrap × doFinal e ausência de `updateAAD` dos dois alfabetos: falso negativo por tradução (`AADUpdate*`, `noCallTo[AADUpdate]`) | CARREGADO | FINAL:176 (c-C28..C30), FINAL:422 (C-4) |
| C-084 | 238 | §3 V4 linha 6 | sem rótulo | verif | `nextBytes` duas vezes (D03) é defeito de tradução real e persiste no gh101; ambos os documentos acertam | CARREGADO | FINAL:278 (§5.3), FINAL:76 (F13) |
| C-085 | 239 | §3 V4 linha 7 | sem rótulo | c-plano + c-review | A atribuição das 12.400 linhas fica INFERIDA (auditoria H-SRD-1 pendente de replay); o review está melhor apoiado que o plano, mas o rótulo correto é INFERIDO | CARREGADO | FINAL:140 (c-B12), FINAL:74 (F11) |
| C-086 | 240 | §3 V4 linha 8 | A5 | anom | `KeyPair` chaveado no construtor (D06): `KeyPair.crysl:19-20` o torna obrigatório, mas `A30/KeyPair.cryptsl:12-13` diz `co?, (pu*, pr*)*` — opcional; nenhum dos dois documentos cita o api30, decisivo para `jca_android` | CARREGADO | FINAL:158 (c-C5), FINAL:279 (§5.3), FINAL:292 (D-B) |
| C-087 | 241 | §3 V4 linha 9 | sem rótulo | verif | `MessageDigest.reset` (D04): não há `reset` em CR nem A30; defeito de tradução do `jca`, já fechado no `jca_android` | CARREGADO | FINAL:184 (x-C "MD reset") |
| C-088 | 242 | §3 V4 linha 10 | sem rótulo | verif | Assimetria TMF/KMF, `:62-63` e o `byte` de Signature (D07/D08) continuam abertos nos dois documentos e são defeitos de tradução | CARREGADO | FINAL:75 (F12), FINAL:498 (§10 "D07/D08 persist") |
| C-089 | 243 | §3 V4 linha 11 | A3 | anom | `SSLContext.createSSLEngine` está declarado `void` (`jca/SSLContextSpec.mop:64`; `jca_android:90`) quando o retorno real é `SSLEngine` — quarto pointcut que nunca casa, canal Engine morto nos dois conjuntos, ausente do registro do plano | CARREGADO | FINAL:156 (c-C3), FINAL:75 (F12), FINAL:276 (§5.3) |
| C-090 | 244 | §3 V4 linha 12 | sem rótulo | anom | SSL `end [engine -> end]` versus `Engine?` do CrySL: falso negativo por tradução | CARREGADO | FINAL:176 (c-C28..C30) |
| C-091 | 245 | §3 V4 linha 13 | sem rótulo | verif | PBE 1000 vs 10000 (D18/D19): as condições são fiéis (≥ 10000 em CR e A30); o defeito está no **texto da mensagem** | CARREGADO | FINAL:358-359 (§7.4, "D18–D20"), FINAL:501 (§10) |
| C-092 | 246 | §3 V4 linha 14 | A4 | anom | `PBEKeySpecSpec` exige `RANDOMIZED(password)` (`jca:37-40,55-59`; `jca_android:42-44,61`) onde `PBEKeySpec.crysl:28-29` só exige `randomized[salt]` — toda senha legítima é acusada | CARREGADO | FINAL:157 (c-C4), FINAL:277 (§5.3) |
| C-093 | 247 | §3 V4 linha 15 | sem rótulo | anom | Os construtores FORBIDDEN de `PBEKeySpec` (`jca:20-30`) são reportados como `InvalidSequenceOfMethodCalls`; não existe tipo `ForbiddenMethod` em `ErrorType` — nenhum dos dois documentos nomeia essa lacuna de categoria | CARREGADO | FINAL:175 (c-C27), FINAL:324-325 (§7.1) |
| C-094 | 248 | §3 V4 linha 16 | sem rótulo | verif | `CipherTransformationUtil` rejeita 8 `PBEWithHmacSHA*AndAES_*` (D15): desvio contra o CrySL original (que aceita), fiel contra o api30 (cujo catálogo não tem a família PBE) | CARREGADO | FINAL:281 (§5.3), FINAL:292 (D-B) |
| C-095 | 249 | §3 V4 linha 17 | sem rótulo | anom | `CCM` aceito (`:33,42`) é falso negativo (ausente de CR); rejeitar `AES/ECB` é **fiel** ao 1.5.2 embora o api30 o admita; padding vazio para GCM/CTR depende do `pad()` do CogniCrypt e fica ambíguo | PARCIAL | FINAL:283 carrega só a linha CCM; ECB (fidelidade ao 1.5.2 vs admissão no api30) e o ponto de padding GCM/CTR sumiram |
| C-096 | 250 | §3 V4 linha 18 | A6 | c-plano | `AndroidKeyStore` sinalizado (D17, severidade A) é **escolha de oráculo**: `jca/KeyStoreSpec.mop:23` é byte-fiel a `KeyStore.crysl:52`; só é desvio contra `A30:89`; o plano classifica errado e o review não corrige | CARREGADO | FINAL:158 (c-C6), FINAL:280 (§5.3) |
| C-097 | 251 | §3 V4 linha 19 | sem rótulo | c-plano | MD5/SHA-1 e `SSL`/`TLSv1` (D-1): fiéis ao 1.5.2, admitidos pelo api30; a auditoria §7 item 10 mede que 5.891/6.048 linhas históricas de `UnsafeAlgorithm` nomeiam algoritmos que o api30 cru não proíbe | PARCIAL | FINAL:281 e FINAL:292 carregam a escolha de oráculo; a medida 5.891/6.048 se perdeu |
| C-098 | 252 | §3 V4 linha 20 | sem rótulo | anom | RANDOMIZED marca o argumento (D12): em `SecureRandom.crysl:33,53` a marca é sobre o valor de retorno; o api30 não tem eventos `nextInt`; SRD G7 FAIL mostra marcas concedidas a partir de instâncias violadoras — achado da auditoria mais forte do que o de ambos os documentos | CARREGADO | FINAL:176 (c-C28..C30), FINAL:469 (C-5, "RANDOMIZED on return values") |
| C-099 | 253 | §3 V4 linha 21 | sem rótulo | c-plano | Pré-requisito D-4 confirmado com uma correção: DH **tem** produtor (`DHGenParameterSpecSpec.mop:36` escreve `PREPARED_DH`); não há `.mop` para os outros quatro; `Property` tem `PREPARED_DH` e não tem `PREPARED_EC/RSA/DSA` | CARREGADO | FINAL:133 (c-A42), FINAL:486 (O-5) |
| C-100 | 254 | §3 V4 linha 22 | sem rótulo | verif | Mapeamento categorias CogniCrypt × `ErrorType` verificado linha a linha: faltam `RequiredPredicate`, `IncompleteOperation`, `ForbiddenMethod`, `NeverTypeOf/HardCoded`; `ErrorType.java:3-10` tem 6 valores | CARREGADO | FINAL:175 (c-C27), FINAL:324-325 (§7.1) |
| C-101 | 256-258 | §3 V4 fecho | sem rótulo | verif | Todos os vereditos por especificação da auditoria são REPROVADA no escopo coberto; o "FP carregador" de quase todo G3 da auditoria é o L2 do plano, alcançado independentemente e executado | CARREGADO | FINAL:85-88 (§3), FINAL:73 (F10) |
| C-102 | 264 | §3 V5 linha 1 | sem rótulo | c-review | **Todos os 11** specs com `getInstance(String)` colidiam antes da correção (o "dez dos onze" do review é impreciso: SecureRandom tem 1 `(String)` + 2 `(String, ..)`, ou seja 3 wrappers numa chave, e o vencedor pré-correção era o órfão `g4`) | CARREGADO | FINAL:141 (c-B14), FINAL:74 (F11) |
| C-103 | 265 | §3 V5 linha 2 | sem rótulo | verif | Truncamento de advice fundido: 9 eventos / 8 emissores descartados (`census_pre_repair.json`), todos os nove na tabela de órfãos do plano; mecanismo `EmitContext.java:52 getMonitorCalls().get(0)` | CARREGADO | FINAL:73 (F10, "nine truncated events restored") |
| C-104 | 266 | §3 V5 linha 3 | sem rótulo | verif | Os números pré-gh100 (8.371 / 643 / 9.015) são consistentes com `gh56-smoke:8835-8843`, `:8877-8896`, `:16327-16345` e com o clone da raiz em `initEvent` | CARREGADO | FINAL:74 (F11) |
| C-105 | 267 | §3 V5 linha 4 | A21 | anom | As 12.400 linhas do SRD têm **três** mecanismos coincidentes: os dois hipotéticos põem o frame num sítio `nextBytes`; a chave `(String)` pré-correção pertencia ao órfão `g4`, deixando o monitor em `start`; e `next2Event` cria monitores, de modo que objetos nascidos fora do DEX acusam no primeiro `nextBytes`; o CSV não tem identidade de objeto para separá-los | CARREGADO | FINAL:170 (c-C21), FINAL:140 (c-B12), FINAL:74 (F11) |
| C-106 | 268 | §3 V5 linha 5 | sem rótulo | verif | Tipo de retorno casado exatamente salvo `*` (`PointcutMatcher.java:361-364`); `doFinal(..)` também casa `doFinal()` | CARREGADO | FINAL:75 (F12), FINAL:174 (c-C26) |
| C-107 | 269 | §3 V5 linha 6 | sem rótulo | c-plano | Rota de clone medida (n=1, `dexdump`, owncloud original × instrumentado): 136.982 métodos comuns, 4.859 (3,9 %) perdem todas as posições de linha, 0 ganham, e **0 dos 693 métodos que invocam `mop.MonitorWrappers`/`MultiSpec_1RuntimeMonitor`** perderam linhas; descritor 115 advices = 64 after-returning + 33 after + 18 before, 0 throwing, logo só o spill de cobertura clona | PARCIAL | FINAL:118 (c-A21), FINAL:489 (O-8); o detalhamento dos 115 advices não é reproduzido |
| C-108 | 270 | §3 V5 linha 7 | sem rótulo | verif | Escopo: 12 contra 16 prefixos; içamento por classe em `DexWeaver.java:359-374`; não há opção de escopo na CLI | AUSENTE | — |
| C-109 | 271 | §3 V5 linha 8 | A/C-36 | anom | O frame de runtime é `(classe, método, arquivo:linha)` sem o alvo chamado — ambíguo quando um método contém duas chamadas monitoradas (`getInstance` + `init`, o caso comum); só fica único com o nome do evento ou a linha no relatório | CARREGADO | FINAL:180 (c-C36), FINAL:320-322 (§7.1), FINAL:489 (O-8) |
| C-110 | 272 | §3 V5 linha 9 | sem rótulo | verif | `ViolationRecorder.java:37-39` cria um `new Exception()` por tentativa de report, avaliado como argumento de `addError`; `MonitorBuilder.java:86-101` não passa `-g`; D44 confirmado (50 `getLineOfCode`, 0 `record`) | CARREGADO | FINAL:69 (F6), FINAL:144 (c-B18, status U) |
| C-111 | 273 | §3 V5 linha 10 | A22 | anom | Itens de toolchain da auditoria ainda abertos em `modules`: primeiro disjunto (`WrapperEmitter.java:507-527`), índice só-declarado (`AndroidClassIndex.java:111-127`), **estreitamento de `args()` variádico ignorado** (`ArgsPC.java:49-56`; `PointcutMatcher.java:269-271`; expansão `:383-384`), tipos aninhados (`TypeResolver.toDescriptor`), seleção do `android.jar` | CARREGADO | FINAL:171 (c-C22), FINAL:487 (O-6), FINAL:230-232 (§5.1) |
| C-112 | 274 | §3 V5 linha 11 | A1 | anom | O resíduo do E3 em `TrustManagerFactorySpec` é explicado pelo wrapper mesclado que chama `g1Event`, `g2Event`, `g3Event` em sequência (PROVADO no DEX de `app.pachli_50.apk`): `g1: 0→2`, `g2: 2→3` (sink) porque `waitingInit` não tem linha `g2`; prevê 2 mudos por fluxo correto, 0 gêmeos, 0 `found .`; MEDIDO sobre as tabelas do OFZ, **em 11 de 23 specs do `jca`** fluxos corretos de `getInstance` de um argumento nunca alcançam `final`/`@match` | CARREGADO (com refutação parcial) | FINAL:136 (c-B2), FINAL:154 (c-C1), FINAL:219-246 (§5.1). O FINAL re-verifica e **estreita**: três mudos por fluxo (não dois) e apenas TMF/KMF/SecureRandom afetados, explicitamente "not affected: MessageDigest, Cipher, Mac, Signature, KPG, SSLContext, KeyGenerator, KeyStore" — o "11 de 23" é rejeitado |
| C-113 | 280 | §3 V6 linha 1 | sem rótulo | verif | Formato 1 usa discriminador por sufixo sem `else`, fabrica `error_type := spec` e reduz `source` ao arquivo (a linha é lida em `:391` e descartada) | CARREGADO | FINAL:70 (F7), FINAL:166 (c-C20) |
| C-114 | 281 | §3 V6 linha 2 | sem rótulo | verif | Formato 2 tem 7 campos, rejunta `parts[6:]` e descarta `parts[2]`; com menos de 6 partes a linha cai adiante | CARREGADO | FINAL:70 (F7) |
| C-115 | 282 | §3 V6 linha 3 | sem rótulo | verif | Formato 3 precisa de `dot_idx`, fabrica `source := "Unknown Source:1"` e descarta linhas `[helper]` (D32) | CARREGADO | FINAL:70 (F7) |
| C-116 | 283 | §3 V6 linha 4 | sem rótulo | c-plano + c-review | O caso `\n`: o plano é IMPRECISO e o review CONFIRMADO com uma precisão — continuação com ≥5 vírgulas vira registro Formato 2 fabricado (spec = primeiro token, `error_type` = sexto token, um tipo bogus entra no `unique_msg`); com prefixo `classe.metodo(` e `:::` vira Formato 3; senão só um aviso em `:371`, sem contador. Uma continuação `state=2:::event=g1` pura é **descartada**, não vira Formato 3 | PARCIAL | FINAL:70 (F7) e FINAL:166 (c-C15) carregam a fabricação; o descarte silencioso de uma continuação em forma `chave=valor` — diretamente relevante para a gramática `key=value` do §7.1 — não é registrado |
| C-117 | 284 | §3 V6 linha 5 | A/C-31 | verif | `:::` dentro da mensagem envenena o `unique_msg` (6 partes) e faz o gh103 (`read_errors_csv:252-256`) zerar `violation_type` e incrementar `unparsed`, mantendo a linha | CARREGADO | FINAL:177 (c-C31), FINAL:418 (C-1) |
| C-118 | 285 | §3 V6 linha 6 | sem rótulo | c-review | `unique_msg` é 5-way, não há dedupe do lado Python, e o arquivo é `rv-android-core/.../domain/coverage.py:563-576`, não `rv-coverage/.../coverage.py` como diz o review | CARREGADO | FINAL:120 (c-B6), FINAL:71 (F8) |
| C-119 | 286 | §3 V6 linha 7 | sem rótulo | verif | Cabeçalho de 11 colunas, INV-PLT-19 "MUST NOT be changed", e o teste exato `test_errors_csv_header_carries_source_after_method` passa hoje (PROVADO) | CARREGADO | FINAL:71 (F8), FINAL:349 (§7.3) |
| C-120 | 287 | §3 V6 linha 8 | sem rótulo | c-plano | Colunas novas quebram INV-PLT-19, o teste e o `read_errors_csv` do gh103 (`ValueError`); **e** o gh103 já extrai `violation_type = parts[3]` e lê `source` como `location`, o que torna a motivação de WS-6.2/6.3 obsoleta para a camada de análise | CARREGADO | FINAL:123 (c-A32), FINAL:71 (F8), FINAL:345-354 (§7.3) |
| C-121 | 288 | §3 V6 linha 9 | A/C-32 | verif | `clock_logcat_join` usa `split(",", 6)` tolerante; uma continuação `\n` inflaria as contagens por passo em um | CARREGADO | FINAL:177 (c-C32), FINAL:350 (§7.3) |
| C-122 | 289 | §3 V6 linha 10 | A17 | anom | Os consolidadores usam a regex `\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$`, congelada em INV-APV-55, mas `experimento-comp162/scripts/consolidate.py:46` está vivo e fora da lista; linhas de continuação e specs que não terminam em `Spec` (`RandomStringPassword`) são excluídas, de modo que `mop_total` do E3 e a contagem INV-CAN-04 do aperv-tool divergem por construção | CARREGADO | FINAL:168 (c-C17), FINAL:353 (§7.3), FINAL:444 (C-1 tarefa 5) |
| C-123 | 290 | §3 V6 linha 11 | sem rótulo | verif | `TraceComparator` usa `EXPECTING_INDEX=6` e é tolerante | CARREGADO | FINAL:350 (§7.3) |
| C-124 | 291 | §3 V6 linha 12 | A/C-33 | verif | `generic_new` está ausente da CLI e o caminho estático analisa silenciosamente `jca` quando o conjunto é `jca_android` | CARREGADO | FINAL:177 (c-C33), FINAL:445-446 (C-1 tarefas 6-7) |
| C-125 | 292 | §3 V6 linha 13 | sem rótulo | verif | Nenhum invariante menciona o literal `unknown` | AUSENTE | — |
| C-126 | 294-303 | §3 V6 tabela de quebra | sem rótulo | prop | Tabela de quebra por mudança proposta: (a) mensagem rica com vírgulas não quebra nada em banda, mas a regra "último campo posicional" é não documentada (entra no INV-ANA-08); (d) sentinela exige regenerar o golden do INV-ANA-46; (e) mensagem na identidade do dispositivo faz contagens subirem e vira o `ErrorDescriptionTest`; (f) id estruturado é limitado, e um 8º campo antes da mensagem só não quebra se for livre de vírgulas; **(g) mensagem JSON funciona posicionalmente (PROVADO)**; (h) tabela de códigos derruba a cardinalidade do `unique_msg` e deixa obsoleto o comentário do INV-CORE-41 | CARREGADO (com decisão contrária) | FINAL:347-354 (§7.3), FINAL:326-330 (§7.1). O item (g) é revertido no FINAL:199, que rejeita JSON por "braces/commas/quotes in a positional line", sem citar a prova posicional da fonte |
| C-127 | 309 | §3 V7 linha 1 | sem rótulo | verif | gh100 está aberto e não arquivado, com 55 [x] / 3 [ ] (7.4–7.6 verify/review/docs-sync); nada aberto toca mensagens | PARCIAL | FINAL:73 (F10) carrega o gh100 como trabalho anterior; a contagem 55/3 e o "nada aberto toca mensagens" se perderam |
| C-128 | 310 | §3 V7 linha 2 | A19 | anom | gh101 está aberto com 84 [x] / 0 [ ], o portão de congelamento passa hoje (PROVADO), e a reversão `e204e2a4` **não está registrada em lugar nenhum do gh101** — `data/gh101/README.md:255-300` ainda documenta o store de identidade como vivo; `divergence_record.csv` tem 106 linhas num vocabulário que não é o da auditoria | CARREGADO | FINAL:135 (c-B1/c-C19), FINAL:73 (F10), FINAL:430 (C-0 tarefa 3) |
| C-129 | 311 | §3 V7 linha 3 | A18 | anom | INV-INS-109..115 existem só no delta do gh101; `openspec/specs/instrumentation/spec.md` para em INV-INS-103; INV-INS-110 não tem teste em `tests/parity/` | CARREGADO | FINAL:169 (c-C18), FINAL:448 (C-V tarefa 2) |
| C-130 | 312 | §3 V7 linha 4 | sem rótulo | verif | Órfãos: 18 no `jca`, 0 no `jca_android` | PARCIAL | FINAL:361-362 (§7.4) diz que INV-INS-110 "already true in `jca_android`"; a contagem de 18 órfãos do `jca` não aparece |
| C-131 | 313 | §3 V7 linha 5 | sem rótulo | verif | A auditoria está fechada, NOT READY, 22/22 REPROVADA, com portões 2 PASS / 2 INC / 10 FAIL; `HANDOFF_PROXIMA_SESSAO.md` é um handoff obsoleto de meio de auditoria | PARCIAL | FINAL:85-86 (§3), FINAL:73 (F10); a partição dos portões (2/2/10) não é reproduzida |
| C-132 | 314 | §3 V7 linha 6 | sem rótulo | anom | Estudo 03 executado em 2026-08-13 (8 containers, `errors.csv` 13:57–15:14, `consolidado/per_rep.csv` com 1.455 linhas = 162×3×3 − 3, corpus de 162 APKs instrumentados); o registro do E3 tem itens abertos P1–P3, P5, P6, P10–P12 | PARCIAL | FINAL:132 (c-A41) e FINAL:427-432 (C-0) carregam a execução e a re-baseline; os itens abertos P1–P3/P5/P6/P10–P12 do registro de prontidão não são mencionados |
| C-133 | 315 | §3 V7 linha 7 | sem rótulo | verif | gh102 e gh103 estão abertos (28/28 e 48/49); `gh103/design.md:54` nomeia `errors.csv`/logcat como entradas e o contrato vive em `aperv-tool/analysis/violations.py` | CARREGADO | FINAL:71 (F8), FINAL:418 (C-1, co-agendamento com gh103) |
| C-134 | 317-326 | §3 V7 fecho | sem rótulo | anom | Achados da auditoria relevantes para mensagens citados por **nenhum** dos dois documentos: G9 FAIL EXEC-SET-25 (5 dos 14 registros de drive com `expecting=unknown`, acompanhando exatamente os FPs executados); §5 item 6 (o NPE do KPG aniquila registros — só 16 linhas históricas) e "13 specs sem emissão histórica nunca adjudicadas"; as famílias G9 "acusações deslocadas/falsas", "canais faltantes" e "mensagem 10×"; risco 6 do §6.1 (não-atribuição diagnóstica impede atribuição por cláusula); a cadeia de serialização do piloto com o risco de truncamento de ~4.068 bytes de payload no logcat; ALFA-PBE-05 (não há `ErrorType` de método proibido) | PARCIAL | FINAL:178 (c-C34) carrega quatro dos sete: 5/14 drive records, NPE do KPG, 13 specs sem emissão, limite de ~4.068 bytes. Perderam-se as famílias G9 e o risco 6 do §6.1 |
| C-135 | 330-331 | §3 V8 primeiro ponto | sem rótulo | prop | A re-baseline não é um passo futuro: é computável agora; os `errors.csv` de 11 colunas antigos sob `results/` são de brinquedo (`gh90_smoke`, 9 linhas) | CARREGADO | FINAL:132 (c-A41), FINAL:427 (C-0) |
| C-136 | 332-335 | §3 V8 coerência da fase A | sem rótulo | c-plano | `ErrorType.java:3-10` está no `rvsec-core`, compartilhado pelos dois conjuntos e pelos dois loggers, logo WS-3.1 tem raio C; e a regra do próprio gh101 para reparos no runtime compartilhado (`gh101/specs/instrumentation/spec.md:99`, "MUST apply identically to both sets … effect on the frozen set MUST be enumerated site by site") o vincularia | PARCIAL | FINAL:121 (c-A30) e FINAL:420/457 (C-2) carregam o raio e o byte-diff do `jca` congelado; a regra citada do gh101 (aplicar identicamente aos dois conjuntos, com efeito enumerado sítio a sítio) não é reproduzida |
| C-137 | 336-340 | §3 V8 corpo mínimo WS-1 | sem rótulo | prop | Corpo mínimo (ilustração): construtor de 4 argumentos, `getLastEvent()` indexado num array de nomes em ordem de declaração, variáveis de spec, classe do objeto, composto antes do `__RESET`; carrega Q1, parte de Q2 e Q5; não carrega estado pré-falha, continuações legais nem argumentos do evento; variáveis de spec podem estar obsoletas de uma sequência anterior; descartar o hash de identidade; a checagem de geração "contagem de eventos == comprimento do array" pertence ao INV-INS-115 | CARREGADO | FINAL:193 (c-D1.3), FINAL:332-343 (§7.2), FINAL:421 (C-3) |
| C-138 | 341-349 | §3 V8 opções WS-2 | sem rótulo | c-plano + prop | gh101 escolheu a opção A para 15 órfãos e B para `MessageDigestSpec.reset`, com resíduo registrado ("a acusação reaparece uma chamada depois"); o custo de geração é dirigido só pela contagem de eventos (17 eventos = 53 s / 3,3 GB; 18 = StackOverflow; CipherSpec re-orçado de 17 para 14); **alternativa só-spec que nenhum documento pesa:** a transição `default` por estado da gramática `fsm:`, não usada em nenhum conjunto, indisponível para specs `ere:` e que precisa ser pareada com uma checagem estilo INV-INS-110 | PARCIAL | FINAL:122 (c-A31), FINAL:160 (c-C8), FINAL:484 (O-3), FINAL:490 (O-9); os números de custo de geração (53 s / 3,3 GB / StackOverflow em 18) não são reproduzidos |
| C-139 | 350-354 | §3 V8 modelo de volume | sem rótulo | prop | Modelo de volume por sítio: (a) mensagem fora da identidade dá 1 registro e a ordem de chegada escolhe o texto; (b) mensagem dentro da identidade dá até o número de valores distintos; (c) id de evento estruturado dentro da identidade dá até o tamanho do alfabeto (≤ 17, na prática 1–3) — recomenda-se (c), que é o que o §9 (ii) da auditoria pede | CARREGADO | FINAL:204 (c-D2.6), FINAL:294 (D-D), FINAL:316-319 (§7.1) |
| C-140 | 355-358 | §3 V8 critérios de aceite | sem rótulo | c-plano | Critérios 1,2,3,4,8 verificáveis offline; 5 e 6 exigem `rv-experiment run` num micro-APK; 5 é alvo errado para as linhas de Cipher (é CrySL); 2 não está "já entregue" (98 linhas residuais); **7 é provável estaticamente no Android** — como o tipo de retorno é casado exatamente, um censo de weaving num micro-APK prova a correção do pointcut sem executar | PARCIAL | FINAL:128 (c-A37) e FINAL:378-391 (§7.6) carregam a reescrita de 2/5/6 e os 98 resíduos; a prova estática do critério 7 desapareceu — o FINAL só oferece o portão de dispositivo G-8 |
| C-141 | 359-367 | §3 V8 corte T0/T1 | sem rótulo | prop | O corte T0/T1 é correto em forma, mas sua premissa presume que o conjunto pós-E3 é um `jca_android` reparado; existe uma terceira opção (conjunto sucessor derivado do `jca` congelado, compatível com o INV-INS-109 como escrito mas colidindo com a disciplina de derivação do INV-INS-112/113 e criando um terceiro livro de conformidade); faltam ao T0 o script de re-baseline do E3, uma casa para o teste de conteúdo `.mop` (`rvsec-mop` não tem `src/test`) e a checagem array/alfabeto; T0.3 deve ser dividido e T0.4 empacotado com T0.3a | PARCIAL | FINAL:142 (c-B15), FINAL:291 (D-A), FINAL:419 (C-V), FINAL:372 (G-4); a colisão com INV-INS-112/113 e o "terceiro livro de conformidade" não são registrados |
| C-142 | 368-370 | §3 V8 proporcionalidade | sem rótulo | prop | Proporcionalidade estimada: T1.3 ≈ 21×3 + 21 linhas de array por conjunto; WS-1.5 são 4 linhas; WS-7 itens 1–5 ≈ 10 linhas em 7 arquivos; WS-2.4 é 1 linha; WS-3 ≈ 60 linhas mais co-design de autômato por spec (27 leituras de `condition()`) | AUSENTE | — |
| C-143 | 374-381 | §3 V9 auditoria do review | sem rótulo | verif | As treze afirmações exclusivas do review foram reabertas e **todas** confirmadas verbatim (entre elas `MessageDigestSpec.mop:57` comentado, `Property` 25, `generic_new` 39, `remove(Property)` depreciado ainda chamado, `ErrorCollector.java:11-22` não sincronizado, `HMACParameterSpec` ausente do `android-37/android.jar`, `@severity` dentro de javadoc) | CARREGADO | FINAL:179 (c-C35), FINAL:120 (c-A25..A29) |
| C-144 | 381-383 | §3 V9 lacuna | sem rótulo | c-review | O §8 do review omite muitos arquivos de que o corpo depende e **nunca abre** `MetaCrySL/generated/api30` (0 menções) — a única lacuna substantiva | CARREGADO | FINAL:138 (c-B4), FINAL:120 ("missing files in review §8") |
| C-145 | 385-390 | §3 V9 padrões de viés | sem rótulo | c-review | Padrões de viés do review: assimetria direcional (responde afirmação não medida com contra-afirmação não medida); números sem caminho de replicação; firmeza seletiva (hesitante no corpo, firme no §0); julgamento CrySL de oráculo único; criação de recomendação; e o "is_library offline" precisa do manifesto da campanha, não só do `errors.csv` | CARREGADO | FINAL:143 (c-B17), FINAL:427-432 (C-0) |
| C-146 | 391-393 | §3 V9 deixado em aberto | sem rótulo | c-review | Itens que o review deixou abertos sendo fecháveis: D44 (agora confirmado), as linhas de `TypestateError`/`RequiredPredicateError` (agora confirmadas), a proveniência de `Platform.kt` (ainda NÃO VERIFICADA); e o review nunca re-checou os números de `e3_decisiva_05`/`exp_00` do plano nem as contagens zero de L5f | CARREGADO | FINAL:144 (c-B18), FINAL:145 (c-B19), FINAL:506 (§10) |
| C-147 | 393-395 | §3 V9 tensão interna | sem rótulo | c-review | Tensão interna do review: T0.5 (identidade em `ErrorSummary`) é mudança de comportamento no dispositivo e portanto só pós-E3, o que a linha "não dividir o E3" do §5 do review não diz | CARREGADO | FINAL:139 (c-B10), FINAL:420 (C-2, "device-side → after Study 03's final runs") |
| C-148 | 397-399 | §3 V9 veredito geral | sem rótulo | c-review | Veredito geral sobre o review: confiável no mecanismo §1–§4; números do §0 agora confirmados por medição; relato de trabalho anterior certo exceto pelo registro da reversão e pelo timing do E3; vereditos CrySL incompletos (api30, `Init+`/`Update+`); corte do §6 é uma opção admissível entre outras | CARREGADO | FINAL:502-506 (§10 errata ao review) |
| C-149 | 426-428 | §4.1 item 5 | A5 (do §4.1) | c-plano | O grafo de predicados do `jca_android` está reconectado (11 write-only, 0 lidos-sem-escrita), mas `generatedCipher` está quebrado pela reversão | CARREGADO | FINAL:131 (c-A40), FINAL:73 (F10) |
| C-150 | 430-431 | §4.1 item 6 | sem rótulo | c-plano | L5b: `is_library` é derivável offline a partir do manifesto da campanha, sem WS-5.1/5.2 | CARREGADO | FINAL:118 (c-A22), FINAL:489 (O-8) |
| C-151 | 432-434 | §4.1 item 7 | sem rótulo | c-plano | O escape é buggy e a chamada comentada citaria a linha inteira; o coletor csv do JSE escapa e depois faz trim; `err.getExpecting().trim()` dá NPE em `null` | CARREGADO | FINAL:119 (c-A23/A24), FINAL:70 (F7), FINAL:442 (C-1 tarefa 3) |
| C-152 | 439-441 | §4.1 item 9 | sem rótulo | c-plano | No §4 do plano: "sete handlers leem variáveis de spec", não os campos; e a weak ref `Ref_<param>` pode estar nula no handler | CARREGADO (com refutação) | FINAL:163 (c-C11): "V− as stated (that path is dead)"; o FINAL substitui o perigo por "campos podem ser nulos" e acrescenta o bug de sombreamento em `jca_android/KeyPairSpec.mop:19-21` |
| C-153 | 442-447 | §4.1 item 10 | sem rótulo | prop | Revisão dos workstreams: WS-2.1–2.3 já feitos no `jca_android`, 2.5/2.6 removidos, acrescentar "verificar INV-INS-110" e a alternativa da transição `default`; WS-3.1 com raio C; WS-6.2/6.3 parcialmente sem objeto; WS-6.6 reescrito (corrigir, não re-habilitar); WS-6.1 vira id estruturado; acrescentar a regra de conteúdo da mensagem, o contador do parser, o workstream de suíte sintética e a re-baseline do E3 como passo 0 | CARREGADO | FINAL:122 (c-A31), FINAL:191 (c-D1.1), FINAL:419 (C-V), FINAL:416 (C-0) |
| C-154 | 448-450 | §4.1 item 11 | sem rótulo | c-plano | D-1 está decidido para o Estudo 03 (`jca`) e aberto para a campanha seguinte; D-2 já foi tomada (gh100 mantido); o custo de D-3 está corrigido; falta a decisão do pesquisador "jca_android reparado vs sucessor do jca" | CARREGADO | FINAL:127 (c-A36), FINAL:142 (c-B15), FINAL:291 (D-A) |
| C-155 | 452-457 | §4.1 item 13 | sem rótulo | c-plano | Reclassificação do registro D01–D50: D02 (9 nunca dispararam; os 18 fechados no `jca_android`), D05 ERRADO, D06 IMPRECISO, D11 latente (`g1` agrupado antes de `g4` num advice, aspecto OFZ `:459-465`), D17 oráculo, D34 18/11; e acrescentar ao registro contaminação por fan-out/clonagem, truncamento, colisão de wrapper, bug de escape, NPE de `expecting` nulo, `c1`/`c2` do `GCMParameterSpecSpec`, `@fail` do KPG sem `__RESET`, `createSSLEngine` `void`, `RANDOMIZED(password)`, `g1+g2 → sink`, `Init+`/`Update+` não traduzidos, `updateAAD` ausente, SSL `engine*` vs `Engine?` | CARREGADO | FINAL:129 (c-A38), FINAL:494-501 (§10) |
| C-156 | 458-459 | §4.1 item 14 | sem rótulo | c-plano | As quatro afirmações inferidas do §9 do plano devem ser substituídas por suas resoluções (V3 itens 7–8; V5 itens 3–4; WS-4 ainda não medido) | CARREGADO | FINAL:126 (c-A35), FINAL:492-493 (§3 não-objetivos, WS-4 fora) |
| C-157 | 513 | §5 anomalias A9 | A9 | anom | Na forma atômica a flag é um `volatile boolean` depois de um CAS, de modo que **duas threads podem despachar uma violação duas vezes** (`O101:7690-7712`) | CARREGADO (refutado) | FINAL:161 (c-C9, "V±"): o despacho duplo concorrente é **refutado** — o `ReentrantLock` global envolve lookup, evento e handlers (FINAL:259-263); as flags obsoletas são confirmadas |
| C-158 | 515 | §5 anomalias A11 | A11 | anom | `HandlerMethod.java:96-101` restaura os parâmetros visíveis ao handler a partir de `WeakReference.get()`, logo qualquer mensagem de `@fail` que desreferencie o objeto monitorado pode dar NPE; campos de spec são seguros | CARREGADO (refutado e substituído) | FINAL:163 (c-C11): caminho morto; o perigo real é campo nulo, mais o bug de sombreamento em `KeyPairSpec.mop:19-21` |
| C-159 | 519 | §5 anomalias A15 | A15 | anom | Qualquer texto com ≥6 vírgulas é aceito como violação pelo `logcat_parser.py:322-349` (PROVADO), inclusive a linha de cabeçalho do csv do JSE | CARREGADO | FINAL:166 (c-C15, status "U — ≥6-comma acceptance not re-opened"), FINAL:418 (C-1) |
| C-160 | 520 | §5 anomalias A16 | A16 | anom | `unique_msg` é derivado em quatro lugares (`result_processor.py:631,999,1038` + `log.py:113`), então qualquer mudança de identidade tem de tocar quatro sítios | CARREGADO | FINAL:167 (c-C16), FINAL:71 (F8), FINAL:443 (C-1 tarefa 4) |
| C-161 | 524 | §5 anomalias A20 | A20 | anom | `logcat_parser.py:391` faz o parse de `line_number` e o descarta em `:309-315`: o caminho genérico perde a linha mesmo quando a tem | CARREGADO | FINAL:166 (c-C20), FINAL:441 (C-1 tarefa 2, "Format 1 keeps the line number") |
| C-162 | 527 | §5 anomalias A23 | A23 | anom | `CoverageWeaver.java:194-196` conta `methodsSpillFailed` e não conta os spills bem-sucedidos, tornando o impacto de L5c invisível no `WeaveReport` | CARREGADO | FINAL:172 (c-C23, status U), FINAL:489 (O-8) |
| C-163 | 528 | §5 anomalias A24 | A24 | anom | A ordem `escape(...).trim()` em `rvsec-logger-csv/.../ErrorCollector.java:42` faz os dois coletores discordarem em espaço em branco no fim mesmo depois de corrigido o escape | CARREGADO | FINAL:173 (c-C24, "U (trivial)"), FINAL:442 (C-1 tarefa 3) |
| C-164 | 539-548 | §6 Rung 0 | Rung 0 | prop | Rung 0, executável agora e sem mudança de código: comitar o script de re-baseline do E3 ao lado de `experimento-comp162/scripts/` com portão de reprodução byte-a-byte; ler os números já conhecidos; e **escalar A1 ao pesquisador** com um teste discriminante em micro-APK estilo G10 (`getInstance("PKIX"); init(ks); getTrustManagers()`), já que só o pesquisador pode decidir se o braço `jca` do E3 é medido com ou sem a correção de aridade | CARREGADO | FINAL:190 (c-D1.0), FINAL:416/427-432 (C-0), FINAL:293 (D-C), FINAL:376 (G-8) |
| C-165 | 550-560 | §6 Rung 1 | Rung 1 | prop | Rung 1 (higiene de toolchain): contar linhas de continuação em vez de fabricar; sentinela para os Formatos 1/3 com golden regenerado; preservar o `line_number`; checagem de sanidade do nome da spec no Formato 2; regra de conteúdo (sem `\n`, sem `:::`, mensagem como último campo) documentada em INV-ANA-08 e imposta por teste sobre corpos `.mop` (casa: `tests/parity/`); corrigir `escapeSpecialCharacters` e o NPE sem re-habilitar a chamada de linha inteira; efeito nas contagens: nenhum | CARREGADO | FINAL:191 (c-D1.1), FINAL:418 (C-1), FINAL:440-446 |
| C-166 | 562-572 | §6 Rung 2 | Rung 2 | prop | Rung 2 (decisão de identidade): acrescentar um id estruturado — o nome do evento ofensor ou o id da cláusula CrySL — à identidade de `ErrorSummary`, nunca o texto livre nem um hash de objeto; reescrever `ErrorDescriptionTest.java:179-220`; tocar as quatro derivações de `unique_msg`; portão com byte-diff do monitor do `jca` congelado e harness JVM disparando dois eventos num sítio; mudança do lado do dispositivo, só em builds pós-E3 | CARREGADO | FINAL:192 (c-D1.2), FINAL:204 (c-D2.6), FINAL:420/454-458 (C-2), FINAL:294 (D-D) |
| C-167 | 574-581 | §6 Rung 3 | Rung 3 | prop | Rung 3 (só texto da mensagem, no conjunto nomeado pelo pesquisador): construtor de 4 argumentos nos 21 `@fail`; mensagem = nome do evento vindo de array em ordem de declaração + variáveis de spec + classe do objeto, composta antes do `__RESET`; os 4 sítios mudos não-`@fail` reportam seus parâmetros; sem hash, `\n`, `:::` ou nomes de estado; portões INV-INS-115, comprimento do array == `getNumberOfEvents()`, micro-APK por modo de falha, zero `unknown` | CARREGADO | FINAL:193 (c-D1.3), FINAL:421/460-462 (C-3), FINAL:369 (G-1) |
| C-168 | 583-592 | §6 Rung 4 | Rung 4 | prop | Rung 4 (autômatos e pointcuts) com portões formais obrigatórios: (i) INV-INS-110 verificado sobre as tabelas **geradas**; (ii) inclusão de linguagem traduzindo a ORDER do CrySL num DFA e checando aceitação/rejeição até um limite, com os traços separadores mínimos da auditoria virando contraexemplos JVM executáveis; (iii) mutação de spec que os portões precisam pegar; (iv) classe de proveniência e entrada no registro de divergência para cada edição, fundidas com o vocabulário do gh101 | CARREGADO | FINAL:194 (c-D1.4), FINAL:365-376 (§7.5 G-2..G-5), FINAL:422 (C-4) |
| C-169 | 594-600 | §6 Rung 5 | Rung 5 | prop | Rung 5 (predicados, após D-4 e a decisão sobre o store de identidade reaberta por `e204e2a4`): mover `condition()` para o corpo só junto com a edição do autômato da spec; criar um tipo de erro `RequiredPredicate`; disciplina RANDOMIZED; os quatro produtores faltantes ou redução explícita de escopo; portões de paridade de inventário e checagem de produto "autômato × predicados" | CARREGADO | FINAL:195 (c-D1.5), FINAL:423/468-470 (C-5), FINAL:375 (G-7) |
| C-170 | 602-609 | §6 Rung 6 | Rung 6 | prop | Rung 6 (gerador/runtime, só se o rung 3 mostrar necessidade): palavras-chave `__EVENTNAME`/`__PREVSTATE` ou `RVM_prevstate` + `RVM_eventNames`; prefixo de traço limitado estilo `--internalbehavior`; preservação de debug items em `cloneInstructions` mais contador de spill; constante de pacote do app pelo canal do `ThisJoinPointEmitter`; manifesto de weaving `(classe, método, chamado, linha)` unido offline; portões por byte-diff e censo `dexdump` como regressão de L5c | CARREGADO | FINAL:196 (c-D1.6), FINAL:482-489 (O-1/O-2/O-8) |
| C-171 | 611-612 | §6 Rung 7 | Rung 7 | prop | Rung 7 é READY conforme `fase0/pre_registro.md §7` (23/23 APROVADA, todos os portões PASS, nada OMITIDA/INCORRETA/INCONCLUSIVA, nenhum contraexemplo aberto, evidência reproduzível) — não é um critério novo | CARREGADO | FINAL:197 (c-D1.7), FINAL:391 (§7.6 item 8) |
| C-172 | 614-623 | §6 ideias formais | sem rótulo | prop | Ideias de validação formal avaliadas: equivalência/inclusão de linguagem é viável (as tabelas geradas já são um DFA e as ORDER são regulares); a checagem do INV-INS-110 é trivial sobre tabelas; traços separadores como contraexemplos JVM já são o método da auditoria; checagem limitada de autômato × predicados é viável para 25 constantes; mutação de spec é barata e é o único modo de saber se os portões discriminam; propriedades de mensagem (nomear evento e classe de estado, nenhum par de modos compartilhando mensagem, injetividade por spec) são checáveis estaticamente; CogniCrypt como oráculo externo sobre os mesmos micro-APKs valida categorias e contagens, não mensagens, porque os oráculos e as granularidades diferem | CARREGADO | FINAL:198 (c-D1.8), FINAL:365-376 (§7.5, G-1..G-8) |
| C-173 | 629-633 | §7 brainstorming ideia 1 | ideia 1 | prop | Mensagem estruturada `key=value` com um campo `message` opaco e `event` de primeira classe; parser trata `message` como opaco e consumidores fazem split em `=`; sem mudança de cabeçalho se o id viajar dentro de `message`; forma recomendada para o rung 3 | CARREGADO | FINAL:199 (c-D2.1), FINAL:307-330 (§7.1) |
| C-174 | 634-637 | §7 brainstorming ideia 2 | ideia 2 | prop | Tabela de códigos de erro por spec/cláusula CrySL (`CIP-ORDER-03`) com o texto humano no consumidor; risco: a tabela precisa ser gerada da mesma fonte que o autômato ou deriva | CARREGADO | FINAL:200 (c-D2.2), FINAL:316-318 (§7.1, `codes.csv`) |
| C-175 | 638-642 | §7 brainstorming ideia 3 | ideia 3 | prop | Gerador emite nomes de evento e estado (`__EVENTNAME`, `__PREVSTATE`); risco: nomes de estado são ids minimizados, então emitir nomes de evento e o id do estado pré-falha, nunca nomes de estado da spec | CARREGADO | FINAL:201 (c-D2.3), FINAL:482 (O-1) |
| C-176 | 643-645 | §7 brainstorming ideia 4 | ideia 4 | prop | Prefixo de traço por monitor em buffer circular limitado (últimos N ids de evento), usado como modo de campanha de calibração e não como padrão | CARREGADO | FINAL:202 (c-D2.4), FINAL:483 (O-2) |
| C-177 | 646-649 | §7 brainstorming ideia 5 | ideia 5 | prop | Manifesto estático de sítios de weaving unido offline; a chave `(classe, método)` é ambígua sem o nome do evento ou a linha, então parear com a ideia 1 | CARREGADO | FINAL:203 (c-D2.5), FINAL:489 (O-8) |
| C-178 | 650-651 | §7 brainstorming ideia 6 | ideia 6 | prop | Id estruturado (evento/cláusula) na identidade de dedupe, não texto nem hash; limitado pelo alfabeto | CARREGADO | FINAL:204 (c-D2.6), FINAL:420 (C-2) |
| C-179 | 652-654 | §7 brainstorming ideia 7 | ideia 7 | prop | Limitação de taxa / agregação por sítio com contagem de suprimidos; risco: muda a semântica de `mop_total` e precisa da decisão D-6 | CARREGADO | FINAL:205 (c-D2.7), FINAL:295 (D-E), FINAL:485 (O-4) |
| C-180 | 655-659 | §7 brainstorming ideia 8 | ideia 8 | prop | Categorias do CogniCrypt como `ErrorType` com texto de remediação do CrySL; a lacuna de vocabulário é real, provada pelos construtores FORBIDDEN do PBEKeySpec reportados como `InvalidSequenceOfMethodCalls` | CARREGADO | FINAL:206 (c-D2.8), FINAL:324-325 (§7.1) |
| C-181 | 660-663 | §7 brainstorming ideia 9 | ideia 9 | prop | Gerar os `.mop` (autômatos e mensagens) a partir do CrySL via MetaCrySL; risco: os defeitos do próprio oráculo se propagam (o api30 tem `next(numB)` protegido e nenhum `nextInt`) e a memória do projeto diz para não mexer no gerador MetaCrySL ainda | CARREGADO | FINAL:207 (c-D2.9), FINAL:490 (O-9); os defeitos concretos do api30 citados não são reproduzidos |
| C-182 | 664-665 | §7 brainstorming ideia 10 | ideia 10 | prop | Modo diagnóstico via `--internalbehavior` para campanhas de calibração, barato de testar nos micro-APKs do E3 | CARREGADO | FINAL:208 (c-D2.10), FINAL:483 (O-2) |
| C-183 | 666-668 | §7 brainstorming ideia 11 | ideia 11 | prop | Transições `default` do `fsm:` em vez de auto-laços enumerados, só com alvo `unsafe` explícito e checagem estilo INV-INS-110, nunca em specs `ere:` | CARREGADO | FINAL:209 (c-D2.11), FINAL:484 (O-3) |
| C-184 | 669-671 | §7 brainstorming ideia 12 | ideia 12 | prop | Redução de alfabeto: todo reparo de órfão por remoção ou por dobrar a checagem no corpo do evento legítimo reduz o custo de geração; risco de expressividade | CARREGADO | FINAL:210 (c-D2.12), FINAL:490 (O-9) |
| C-185 | 672-675 | §7 brainstorming ideia 13 | ideia 13 | prop | Impor a aridade de `args()` nos dois caminhos de weaving (A1): custo pequeno, mas **inverte a semântica do Estudo 03** — decisão do pesquisador; remove o FP de `g2` em 11 specs de uma vez, o que é mais "valor de mensagem" do que qualquer edição `.mop` da lista | CARREGADO | FINAL:211 (c-D2.13/c-D4.1), FINAL:293 (D-C), FINAL:417 (C-1a); o alcance "11 specs" é reduzido a três no FINAL:238-240 |
| C-186 | 681-684 | §8 riscos | sem rótulo | verif | Risco de validade: esta validação foi produzida pela mesma classe de agente que o plano e o review; a mitigação foram subagentes com disciplina de reabrir-e-citar e checagens cruzadas entre eles; concordância não é prova, as citações é que são | AUSENTE | — |
| C-187 | 685-688 | §8 NOT_VERIFIED | sem rótulo | verif | A consequência de A1 em runtime no E3 é INFERIDA: o wrapper (DEX) é PROVADO e as tabelas (OFZ) MEDIDAS, mas que o runtime faça exatamente `g1: 0→2, g2: 2→3` no dispositivo não foi reproduzido; os números do E3 batem com a predição, o que é forte mas circunstancial, e o micro-APK do rung 0 é o teste discriminante | PARCIAL | FINAL:219-246 (§5.1) marca o achado como V+ e cita o DEX; a ressalva epistêmica ("runtime não replicado, evidência circunstancial") não é registrada — o FINAL só mantém o micro-APK como portão G-8 |
| C-188 | 689-690 | §8 NOT_VERIFIED | sem rótulo | verif | A medição de L5c é n=1 (um APK, `dexdump`), somada à estatística de 100 % de linhas do E3, que condiciona nos frames que chegaram a ser reportados | CARREGADO | FINAL:118 (c-A21, "n=1 census"), FINAL:489 (O-8) |
| C-189 | 691 | §8 NOT_VERIFIED | sem rótulo | verif | A atribuição das 12.400 linhas do SRD continua INFERIDA (três mecanismos coincidentes; o CSV não tem identidade de objeto) | CARREGADO | FINAL:140 (c-B12), FINAL:74 (F11) |
| C-190 | 692-693 | §8 NOT_VERIFIED | sem rótulo | verif | Os julgamentos sobre api30 repousam no texto da regra e na leitura documentada do gh101; o `pad()` do CogniCrypt sobre transformações de 2 partes não foi checado | PARCIAL | FINAL:76 (F13) e FINAL:292 (D-B) usam o api30 como oráculo decidido; a ressalva sobre `pad()` não aparece |
| C-191 | 694-695 | §8 NOT_VERIFIED | sem rótulo | verif | `static final String[]` no bloco de declarações é viável pela gramática mas NÃO VERIFICADO num oráculo do rvsec, porque exigiria gerar um monitor (deliberadamente não executado) | CARREGADO | FINAL:126 (c-A35, "R (grammar) / U (oracle)"), FINAL:369 (G-1) |
| C-192 | 698-702 | §8 NOT_VERIFIED | sem rótulo | verif | Continuam NÃO VERIFICADOS: a proveniência da linha em `Platform.kt`, os números de linha de `DexWriter.java` (jar externo), o caminho de seleção do `android.jar` e os números in-tree do plano vindos de `e3_decisiva_05`/`exp_00` | PARCIAL | FINAL:145 (c-B19) carrega só `Platform.kt`; `android.jar` sobrevive como item de O-6 (FINAL:487); `DexWriter` e `e3_decisiva_05`/`exp_00` não aparecem |
| C-193 | 703 | §8 NOT_VERIFIED | sem rótulo | verif | A ordem de registro dos wrappers pré-correção é INFERIDA da ordem no artefato | CARREGADO | FINAL:74 (F11, atribuição mantida INFERRED) |

## Itens AUSENTES, em detalhe

Vinte e dois itens. Para cada um: texto da fonte (condensado, mas com os números literais), por que
importa, e as buscas feitas para confirmar a ausência no FINAL.

**C-007 (fonte:44-46) — o placar de auditoria das citações do review.**
"every one of the 52 decision-carrying `file:line` citations we re-opened for it is CONFIRMED or off
by one line — and its re-measurements, which it left untraceable, all reproduce (V2)".
Importa porque é a base de confiança do FINAL no review: o FINAL marca dezenas de linhas do §4 como
`R` ("já verificado no review") sem registrar em nenhum lugar *quanto* do review foi auditado nem por
quem. Buscas: `grep -F "52"` (0 ocorrências); `grep -i -E "13 review|bias"` — `bias` aparece 3 vezes,
sempre em outro contexto (FINAL:143 sobre viés do review, FINAL:292 "HMC oracle bias", FINAL:298).

**C-021 e C-022 (fonte:128-129) — os placares de citação do plano e do review.**
"**Plan** (45 rows): CONFIRMED 39 · IMPRECISE 3 · WRONG 2 · UNVERIFIED 1. **Review** (52 rows):
CONFIRMED 49 · IMPRECISE 2 · WRONG 0 · UNVERIFIED 1."
Importam pela mesma razão: são a única quantificação de quanto de cada documento sobreviveu à
verificação independente. Buscas: `grep -F "45"`, `grep -F "52"`, `grep -i "IMPRECISE"`,
`grep -i "UNVERIFIED"` — nenhuma ocorrência; o FINAL usa o vocabulário próprio `V+/V−/V±/R/U`.

**C-019 (fonte:115-118) — o prompt de validação aponta o caminho errado de `JavaFSM.java`.**
"its path for `JavaFSM.java` (`.../java/rvj/logicpluginshells/fsm/`) is wrong — the file is at
`rv-monitor/rv-monitor/src/main/java/com/runtimeverification/rvmonitor/logicpluginshells/fsm/JavaFSM.java`".
Importa porque `docs/20260815_javamop_mensagens_validacao_prompt.md` continua no repositório e é a
linhagem declarada do FINAL (FINAL:18); qualquer nova rodada de validação herda o caminho errado.
Buscas: `grep -i "validacao_prompt"` (só a linha de linhagem, FINAL:18); `grep -i "logicpluginshells"`
(0).

**C-031 (fonte:143) e parte de C-192 (fonte:700) — `DexWriter.java:1156-1159` vs `:1155-1158`.**
Divergência de citação entre plano e review deixada NÃO VERIFICADA porque o jar é externo.
Importa como dívida de verificação declarada: fica sem dono se não for anotada. Buscas:
`grep -F "DexWriter"` (0); `grep -i "external jar"` (0).

**C-036 (fonte:158) — a definição de shadow muda a leitura por especificação.**
"under co-location MessageDigest is 99 % shadow (10,035/10,135) and KeyStore 29 % — the definition
changes the per-spec reading materially".
Importa porque o FINAL adota "pairing" como definição canônica em D-F (FINAL:296) sem registrar que a
escolha vira uma spec de 99 % para outra fatia; é exatamente o tipo de sensibilidade que a decisão
D-F deveria documentar. Buscas: `grep -F "10,035"` (0); `grep -i -E "shadow|per-spec"` — as 5
ocorrências de "shadow" no FINAL tratam só da dicotomia pairing/co-location global.

**C-037 (fonte:159) — sítios de contagem idêntica em TMF: 1.733/1.748 e 4.587/4.602.**
Confirmação da métrica de gêmeos 1:1 pré-gh100 sobre a qual o F11 do FINAL se apoia. Importa porque
o FINAL afirma "wrapper collision explains the TMF 1:1 twins" sem nenhum número reproduzível por trás.
Buscas: `grep -F "1,733"`, `grep -F "1,748"`, `grep -i -E "twin"` — as ocorrências de "twin" são
FINAL:74 e FINAL:140, ambas sem contagem.

**C-043 (fonte:165) — 11.761 é o excesso, e as linhas em grupos idênticos são 20.323 (20,95 %).**
"11,761 is the *excess* (N − distinct); rows belonging to a fully identical group are 20,323 (20.95 %)".
Importa porque é uma correção de *leitura* de um número que o plano publica como se fosse contagem de
linhas — o dobro do valor real de duplicação declarada. Buscas: `grep -F "11,761"` (0);
`grep -i -E "excess|amplification"` (0).

**C-045 (fonte:167) — o grupo de "1.542 linhas" e os "24 timestamps" vêm de outro diretório.**
"in *this* CSV the largest (apk,rep,tool,unique_msg) group is 388; 1,542 and '24 timestamps at
Platform.kt:83' are other result dirs — the plan mixes sources without saying so".
Importa porque é uma acusação de mistura de fontes no plano, e o plano continua sendo "o registro de
causa raiz" (FINAL:8-9): um número sem proveniência sobrevive lá. Buscas: `grep -F "1,542"` (0);
`grep -F "24 timestamp"` (0); `grep -F "exp_00"` e `grep -F "e3_decisiva"` (0).

**C-046 (fonte:168) — o censo de mensagens degeneradas.**
"`but found .` 8,843/5; missing space 2,005; ellipsis 109; braced 9/14,959; unbraced 7/11,292;
case-only 4; SHA-1/SHA1/SHA 2,340 … identical (unbraced 9/11,299 if the two `invalid key size`
messages are counted)".
Importa porque é a evidência quantitativa do problema que o documento inteiro existe para resolver —
a superfície de mensagens degeneradas — e é a linha de base contra a qual as propriedades G-6
("nenhum par de modos compartilha mensagem") seriam medidas. Buscas: `grep -F "8,843"`,
`grep -F "2,005"`, `grep -F "2,340"`, `grep -i -E "degenerate|missing space|braced|case-only"` — todas
0.

**C-050 (fonte:173-176) — a fatia `unknown` é plana entre ferramentas e o volume é concentrado.**
"`unknown` share is flat across tools (71.2–74.0 %) and timeouts (72.5–73.1 %) — a property of the
specs/pipeline, not of the driver; volume is concentrated (top-5 apks 32 % of rows; SSLContextSpec +
TrustManagerFactorySpec = 45.7 % of the CSV); every `unique_msg` splits into exactly 5 parts".
Importa por dois motivos: (i) é a refutação medida da hipótese de que o problema de mensagens dependa
da ferramenta de exploração, o que blinda a comparação APE × APE-RV; (ii) a concentração em duas
specs diz onde o C-3/C-4 dá retorno. Buscas: `grep -F "71.2"`, `grep -F "45.7"`, `grep -F "top-5"`
(0); `grep -i -E "per tool|per-tool|across tools|driver"` (0).

**C-052 (fonte:184) — a distribuição de tipos de erro no E3.**
"InvSeq **77.78** · UnsafeProto 7.46 · **UnsatCons 6.90 (1,357)** · UnsafeAlg 6.50 · InvKST 1.35 ·
InvKS 2 rows — the 9 restored events now emit".
Importa porque é a evidência direta de que os 9 eventos restaurados pelo gh100 passaram a emitir (a
categoria `UnsatisfiedConstraint` sai de 0 para 1.357 linhas) — a validação de resultado do gh100.
Buscas: `grep -F "1,357"`, `grep -F "77.78"` (0); `grep -i "UnsatisfiedConstraint"` — só FINAL:115,
que cita 419 linhas `unknown`, um subconjunto de outra medida.

**C-053 (fonte:185) — mensagens distintas caíram de 19 para 16.**
Importa porque o §1 do FINAL (FINAL:44) ainda enuncia o problema com "only 19 distinct messages
exist" sem dizer que no dado pós-reparo esse número **caiu** para 16, isto é, o vocabulário ficou mais
pobre depois do reparo. Buscas: `grep -F "distinct messages"` (0 — o FINAL escreve "19 distinct
messages" só na forma corrida do §1); `grep -F "16 "` — as 9 ocorrências de "16" são de outros
contextos (`≈ 16 %` em FINAL:241, números de linha).

**C-055 (fonte:188) — shadow no E3 e o peso das linhas mudas órfãs.**
"22.21 / 28.08 %; orphan mute rows still 55.6 % of the CSV".
Importa porque é a medida de que, mesmo depois do gh100 e do congelamento, mais da metade do CSV é
registro mudo órfão — o dimensionamento do problema no dado que o FINAL escolhe como linha de base.
Buscas: `grep -F "22.21"`, `grep -F "55.6"` (0); `grep -i "orphan"` — 4 ocorrências, todas sobre
eventos órfãos em specs, nenhuma sobre linhas do CSV.

**C-056 (fonte:189) — três novas famílias de gêmeos 1:1 no E3.**
"**SecretKeySpec 820/820, IvParameterSpec 419/419, PBEKeySpec 118/118** — restored orphans reaching
the DEX and sinking (plan L2 mechanism 1, live)".
Importa porque é o efeito colateral medido do reparo do gh100: eventos restaurados agora chegam ao
DEX e afundam no sink, criando gêmeos onde antes não havia. O FINAL registra o desaparecimento dos
gêmeos antigos de TMF (F11) e não registra o aparecimento dos novos. Buscas: `grep -F "820"` (0);
`grep -F "SecretKeySpec"` (0); `grep -i -E "twin|restor"` — "twin" só em FINAL:74/140 (TMF,
pré-gh100); "restored" só em FINAL:73 (os nove eventos do gh100, sem consequência medida). A única
sobrevivência parcial é o número 419 em FINAL:115, ali usado como contagem de linhas `unknown` do
`IvParameterSpec`, não como família de gêmeos.

**C-059 (fonte:192) — o funil no E3: 696 → 188 → 184 → 69/54/45.**
Importa porque o funil é a métrica que o plano usa para dizer "28 achados"; o FINAL retira o número
antigo (F9) mas não põe o valor pós-reparo no lugar. Buscas: `grep -F "696"`, `grep -F "188"` (0);
`grep -i "funnel"` — só FINAL:114, "funnel 24–59 by definition", referente ao dataset velho.

**C-060 (fonte:193) — linhas de terceiros no E3: 80,04 / 84,81 / 87,34 %, 72 de 112 apps sem código próprio.**
Importa porque é o insumo do classificador que a decisão D-F (FINAL:296) manda registrar "antes de
qualquer número ser publicado" — e o número pós-reparo não está no documento. Buscas:
`grep -F "80.04"`, `grep -F "87.34"` (0); `grep -i -E "third-party|vendor"` — FINAL:114 e FINAL:296,
ambos sobre as definições, sem valores do E3.

**C-061 (fonte:194) — maior grupo idêntico no E3 e o papel da coluna `source`.**
"11-col 2 (excess 0.05 %); 10-col w/o `source` 7; 5-col 1,152 (dankchat Ktor loop); `source` separates
lines".
Importa porque a opção O-4 (agregação/rate limit, FINAL:485) tem como gatilho declarado "C-0 mostra
que o volume dirigido por reinício domina" — e esta é justamente a medida que responde a isso: com
`source` na chave, a duplicação exata praticamente some (0,05 %). Buscas: `grep -F "1,152"` (0);
`grep -i "identical group"` (0); `grep -F "excess"` (0).

**C-108 (fonte:270) — escopo de weaving: 12 contra 16 prefixos, sem opção de CLI.**
"Scope: 12 vs 16 prefixes; per-class hoisting `DexWeaver.java:359-374`; no CLI scope option".
Importa porque a divergência entre a lista de prefixos do weaver e a do resto do pipeline afeta quais
classes de biblioteca chegam a ser instrumentadas — e portanto a própria contagem de "linhas de
terceiros" que a decisão D-F quer congelar. Buscas: `grep -i "prefix"` — 3 ocorrências, todas sobre
`trace-prefix` (O-2) ou sobre o classificador de terceiros (D-F), nenhuma sobre escopo de weaving;
`grep -i -E "scope|hoist"` — "scope" aparece só em "explicit scope reduction" (FINAL:486) e em
"artifact-scoped" fora deste contexto.

**C-125 (fonte:292) — nenhum invariante menciona o literal `unknown`.**
"No invariant mentions the literal `unknown` — CONFIRMED (grep)".
Importa porque o critério de aceite nº 1 do FINAL (FINAL:380) é "zero linhas com `message = unknown`":
esse critério não tem nenhum invariante SDD que o sustente hoje, e o achado é exatamente a
justificativa para criar um. Buscas: `grep -F "no invariant"` (0); `grep -i "literal"` — 2
ocorrências (FINAL:44 e FINAL:46), ambas descrevendo o problema, nenhuma dizendo que nenhum
invariante o cobre.

**C-142 (fonte:368-370) — a proporcionalidade em linhas de código.**
"T1.3 ≈ 21×3 + 21 array lines per set; WS-1.5 4 lines; WS-7 items 1–5 ≈ 10 lines in 7 files; WS-2.4 1
line; WS-3 ≈ 60 lines + automaton co-design per spec (27 `condition()` reads)".
Importa porque é a única estimativa de esforço concreta produzida por qualquer dos documentos; o §8
do FINAL atribui raios (S/C/M/I/P) mas nenhum tamanho, e as mudanças C-3/C-4 são propostas como
issues sem ordem de grandeza. Buscas: `grep -E "lines"` — todas as ocorrências são contagens de
linhas dos documentos de linhagem ou textos de tarefa; `grep -F "21×"` e `grep -F "60 lines"` (0).

**C-186 (fonte:681-684) — o risco "mesma classe de agente".**
"This review was produced by the same class of agent as the plan and the review; the mitigation was
subagents with re-open-and-quote discipline and cross-checks between them … Agreement is not proof;
the quotes are."
Importa porque o FINAL consolida quatro validações externas produzidas todas por LLMs e trata
concordância entre elas como reforço (FINAL:60, "re-verified by ≥2 external validations"); a fonte
adverte explicitamente contra esse raciocínio. Buscas: `grep -F "same class"` (0); `grep -i -E "agent|LLM"`
— "LLM" só em FINAL:18 ("brief given to four external LLMs"), sem ressalva metodológica.

## Itens PARCIAIS, em detalhe

Vinte e três itens. O que se perdeu entre a fonte e o FINAL.

**C-038 (fonte:160) — granularidade de evento.** A fonte confirma 46.330 / 20.507 / 32.232 e
acrescenta que `time` é inteiro em segundos, de 0 a 294, monótono dentro da execução, com 17.174
linhas em `time=0`. O FINAL (FINAL:72, F9) preserva apenas "`time` is seconds". Perderam-se as três
contagens de granularidade — que são o que distingue "evento" de "linha" nas comparações — e o fato
de que quase 18 % das linhas caem no instante 0.

**C-047 (fonte:169) — os 8.371 valores observados vazios.** A fonte decompõe por classe (Platform
7.174; TlsUtil 584; okhttp3.internal.Util 324; Ktor 219; `AdvancedX509TrustManager` de pacote próprio
27+24; Conscrypt 19) e conclui 96,5 % okhttp3, corrigindo o "okhttp" do plano. O FINAL (F11) mantém
só o total 8.371 e a atribuição à colisão de wrapper. Perdeu-se que **não** é 100 % okhttp — há
linhas de pacote próprio no meio, o que impede tratar o fenômeno como puramente de biblioteca.

**C-049 (fonte:171) — perfil de sítios das 12.400 linhas do SecureRandomSpec.** A fonte lista os
sítios com contagem e conclui que "o perfil da auditoria é exato". O FINAL (F11) diz apenas "site
profile at `nextBytes`". Perdeu-se a quantificação que sustenta o veredito, e com ela a possibilidade
de o leitor julgar por que a atribuição fica INFERIDA.

**C-051 (fonte:183) — composição do E3.** Sobrevivem as 19.664 linhas (FINAL:46, FINAL:132).
Perderam-se: 112 de 162 apks com pelo menos um erro, a repartição por ferramenta (`ape` 7.133;
`aperv:mop_off_llm_off` 6.023; `aperv:mop_on_llm_off` 6.508) e o fato de que só o timeout 300 foi
usado — informação necessária para saber contra o que a próxima campanha será comparada.

**C-062 (fonte:195) — SecureRandomSpec no E3.** A fonte mede 2.882 linhas (14,7 % do CSV) com o mesmo
perfil de sítios e conclui que o estrato `next2` não foi tocado pelo gh100. O FINAL preserva o
mecanismo `next2` (F11) mas escreve explicitamente "SR share unquantified" (FINAL:242) — ou seja,
declara não quantificada uma fatia que a fonte já havia quantificado.

**C-072 (fonte:212) — `static final String[]` no bloco de declarações.** A viabilidade pela gramática
e o portão de regeneração (G-1) foram carregados. Perdeu-se a ressalva operacional: uma linha de
declaração que case com `event <nome>(` derruba a regex de texto cru do `RVParser.jj:253-254`. Como
o desenho §7.2 do FINAL põe `EVENT_NAMES` exatamente nesse bloco, a ressalva é a armadilha concreta
de implementação do C-3.

**C-080 (fonte:234) — re-`init` depois de um final.** A fonte separa dois casos: re-`init` *depois*
de um final é conforme (porque `Init+` precede o grupo dos finais), enquanto re-`init` *antes* de
qualquer update/final é defeito de tradução. O FINAL (§5.3 linha 1) funde os dois em "s2/s3 no
re-`init`" e classifica o conjunto como defeito. Perdeu-se a fronteira — que é justamente o que o
reparo C-4 precisa saber para não abrir um falso negativo ao acrescentar linhas de `init`.

**C-095 (fonte:249) — CCM, ECB e padding.** O FINAL carrega a linha CCM ("absent from both oracles →
`CipherTransformationUtil:33` accepts it → deviation"). Perderam-se: (i) que rejeitar `AES/ECB` é
**fiel** ao 1.5.2 embora o api30 o admita — isto é, ECB é escolha de oráculo e não defeito; e (ii)
que o padding vazio para GCM/CTR depende do comportamento de `pad()` do CogniCrypt e portanto fica
ambíguo. Ambos entram no escopo da decisão D-B sem estarem listados nela.

**C-097 (fonte:251) — a medida do deslocamento de oráculo.** A escolha de oráculo para MD5/SHA-1 e
SSL/TLSv1 foi carregada (§5.3, D-B). Perdeu-se a quantificação da auditoria §7 item 10: "5.891/6.048
linhas históricas de `UnsafeAlgorithm` nomeiam algoritmos que o oráculo api30 cru não proíbe" — ou
seja, 97 % daquela categoria de achado desapareceria sob o api30. É o número que torna a decisão D-B
consequente em vez de estilística.

**C-107 (fonte:269) — o censo de clonagem.** A medição principal (3,9 % dos métodos, 0 de 693 tecidos)
foi carregada. Perdeu-se a decomposição do descritor que explica *por que* o efeito é nulo nos
métodos tecidos: 115 advices = 64 after-returning + 33 after + 18 before, 0 throwing/if/staticinit,
logo só o spill de cobertura clona instruções.

**C-116 (fonte:283) — o descarte silencioso de continuações em forma `chave=valor`.** A fabricação de
registro com ≥5 vírgulas foi carregada (F7, c-C15). Perdeu-se: "Bare `state=2:::event=g1` is
**dropped**, not Format 3". Importa diretamente para o desenho §7.1: se um envelope `key=value`
alguma vez for quebrado em duas linhas de logcat, o segundo pedaço some sem contador — precisamente
o que a gramática v1 precisa prever.

**C-127 (fonte:309) — estado do gh100.** F10 carrega o gh100 como trabalho anterior. Perderam-se o
"55 [x] / 3 [ ]" e a observação de que as três tarefas abertas (7.4–7.6 verify/review/docs-sync) não
tocam mensagens — isto é, que nada em gh100 bloqueia o trabalho proposto.

**C-130 (fonte:312) — contagem de órfãos.** O FINAL diz que INV-INS-110 "já vale no `jca_android`"
(§7.4). Perdeu-se o número do outro lado: o `jca` congelado tem **18** eventos órfãos, medidos por
script próprio da fonte. É a dimensão do débito que o conjunto sucessor (D-A opção ii) herdaria.

**C-131 (fonte:313) — placar de portões da auditoria.** "NOT READY, 22/22 REPROVADA" foi carregado.
Perdeu-se "gates 2 PASS / 2 INC / 10 FAIL" e a observação de que `HANDOFF_PROXIMA_SESSAO.md` é um
handoff obsoleto de meio de auditoria — armadilha para quem retomar o trabalho pela auditoria.

**C-132 (fonte:314) — registro de execução do E3.** A execução em 2026-08-13 e a re-baseline foram
carregadas (c-A41, C-0). Perderam-se os detalhes de reprodutibilidade (8 containers, janela 13:57–15:14,
`per_rep.csv` com 1.455 = 162×3×3 − 3, corpus de 162 APKs) e, sobretudo, os **itens abertos P1–P3,
P5, P6, P10–P12** do `registro_execucao_prontidao_e3.md:610-640`, que são condições declaradas de
validade da própria campanha usada como linha de base.

**C-134 (fonte:317-326) — achados da auditoria citados por nenhum documento.** O FINAL (c-C34) carrega
quatro dos sete: 5/14 registros de drive com `expecting=unknown`, o NPE do KPG que aniquila registros,
as 13 specs sem emissão histórica e o limite de ~4.068 bytes do logcat. Perderam-se as famílias G9
("acusações deslocadas/falsas", "canais faltantes", "mensagem 10×") e o risco 6 do §6.1 da auditoria
("não-atribuição diagnóstica … impede atribuição por cláusula") — este último é literalmente o
problema que o documento inteiro se propõe a resolver, com um registro de risco já existente.

**C-136 (fonte:332-335) — a regra do gh101 para runtime compartilhado.** O raio C de WS-3.1 e o
byte-diff do `jca` congelado foram carregados (C-2). Perdeu-se a citação da regra vinculante:
`gh101/specs/instrumentation/spec.md:99` — "MUST apply identically to both sets … effect on the
frozen set MUST be enumerated site by site". Sem ela, a exigência de enumeração sítio a sítio no C-2
aparece como preferência de desenho e não como obrigação herdada.

**C-138 (fonte:341-349) — custo de geração.** A alternativa `default` do `fsm:` e a redução de
alfabeto foram carregadas (O-3, O-9). Perderam-se os números que dão limite duro ao desenho: 17
eventos custam 53 s e 3,3 GB, 18 eventos estouram em StackOverflow, e o CipherSpec teve de ser
re-orçado de 17 para 14 eventos. Qualquer reparo do C-4 que acrescente eventos esbarra nesse teto e
o FINAL não o menciona.

**C-140 (fonte:355-358) — critério 7 provável estaticamente.** A reescrita dos critérios 2/5/6 foi
carregada. Perdeu-se que o critério 7 (pointcuts que nunca casam) é **provável estaticamente no
Android**, porque o tipo de retorno é casado exatamente: um censo de weaving num micro-APK prova a
correção sem executar. O FINAL só oferece o portão de dispositivo G-8 (FINAL:388), o que torna a
verificação mais cara do que precisa ser.

**C-141 (fonte:359-367) — a terceira opção de conjunto-alvo.** A opção (ii) "sucessor derivado do
`jca`" foi carregada em D-A. Perderam-se a compatibilidade e o conflito precisos que a fonte apura:
compatível com o INV-INS-109 **como está escrito** ("freezes the `jca` specification set … at this
change's base commit"), mas colidindo com a disciplina de derivação do INV-INS-112/113 e criando um
**terceiro livro de conformidade**. É o custo processual da opção que o FINAL recomenda por padrão.

**C-187 (fonte:685-688) — a consequência de A1 em runtime é INFERIDA.** O FINAL classifica o achado
como `V+` e cita o DEX desmontado. Perdeu-se a estratificação da evidência que a própria fonte impôs:
o wrapper é PROVADO, as tabelas são MEDIDAS, mas a execução `g1: 0→2, g2: 2→3` no dispositivo nunca
foi reproduzida — "forte, mas circunstancial". Como este é o achado que sustenta a mudança C-1a e a
decisão D-C (agir no meio da campanha), a diferença entre PROVADO e INFERIDO é material.

**C-190 (fonte:692-693) — ressalva sobre o `pad()` do CogniCrypt.** O api30 foi adotado como oráculo
decidido por família de cláusula (D-B). Perdeu-se a ressalva de que os julgamentos sobre api30
repousam no texto da regra e na leitura documentada do gh101, e que o comportamento de `pad()` do
CogniCrypt sobre transformações de duas partes não foi checado — a lacuna que afeta exatamente a
linha de padding GCM/CTR.

**C-192 (fonte:698-702) — a lista de NÃO VERIFICADOS.** Sobrevive `Platform.kt` (c-B19) e, de lado, o
`android.jar` como item de O-6. Perderam-se `DexWriter.java` (números de linha, jar externo) e os
números in-tree do plano vindos de `e3_decisiva_05`/`exp_00` — este último importa porque o plano
segue sendo o registro de causa raiz e esses números continuam lá sem verificação.
