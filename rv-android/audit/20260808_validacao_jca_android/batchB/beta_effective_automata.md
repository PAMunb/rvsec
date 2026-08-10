# Autômatos efetivos — Batch B (extraídos dos artefatos gerados)

Agente Beta, 2026-08-09. Fonte: os `*RuntimeMonitor.java` do insumo comum da rodada
(`batchB/generation_manifest.md`), hashes conferidos antes do uso (20/20 idênticos) e
**re-gerados de forma independente** neste parecer (20/20 byte-idênticos — `beta_report.md`
§1). Formato do batch A (`batchA/beta_effective_automata.md`): codificação de estados,
tabelas por evento, escopo do monitor, tudo citado por arquivo:linha do artefato. Todas as
tabelas conferidas idênticas no `MultiSpec_1RuntimeMonitor.java` do `-merge` de produção
(23 specs; `beta_report.md` §4).

Convenções: categorias calculadas após cada `handleEvent`; `condition(false)` = `return
false` **antes** de `handleEvent` (supressão sem transição); corpo do evento executa
**antes** da transição (escritas de Property são independentes do estado — provado
executável, SKY-d2/KPR-a2 em `beta_betadriveB_run1.out`).

## CipherInputStreamSpec — alfabeto {c1, r1, r2, cl1} — **monitor GLOBAL**

Arquivo: `gen_CipherInputStreamSpec/out/CipherInputStreamSpecRuntimeMonitor.java`
(sha256 `aa6e492e…`). Tabelas `:125-128`; eventos `:169` (c1), `:182` (r1), `:192` (r2),
`:202` (cl1); handler fail `:212` (+ `reset()` `:220`); **sem** categoria match.
Estados: 0 = início, 3 = pós-c1, 1 = lendo, 2 = pós-close (aceitante estrutural, sem
handler), 4 = fail.

| evento | 0 | 1 | 2 | 3 | 4 | fonte |
|---|---|---|---|---|---|---|
| c1 (ctor 2-arg; corpo lê REQUIRES generatedCipher) | 3 | 4 | 4 | 4 | 4 | `:125` |
| r1 (read() ∥ read(byte[])) | 4 | 1 | 4 | 1 | 4 | `:126` |
| r2 (read(byte[],int,int); liga args, **sem** condition) | 4 | 1 | 4 | 1 | 4 | `:127` |
| cl1 (close()) | 4 | 2 | 4 | 4 | 4 | `:128` |

**Escopo do monitor**: a spec não declara parâmetro (`CipherInputStreamSpec()`,
`.mop:11`); a árvore de indexação é UM monitor estático por processo
(`CipherInputStreamSpec__Map`, `:275`; FindOrCreateEntry devolve sempre o mesmo,
`:298-308`; idem no merge, `MultiSpec_1RuntimeMonitor.java:9446`). A linguagem
`c1 (r1|r2)+ cl1` vale portanto para a CONCATENAÇÃO de todos os streams do processo: a
2ª construção legal dispara `InvalidSequenceOfMethodCalls` e o resto do 2º ciclo de vida
falha em cascata (3 FPs por stream legal — PROVADO, CIS-b/b2/b3). `close` sem `read`
é corretamente acusado (cl1 de 3→4; CIS-d). fail é canal VIVO aqui (difere do batch A).

## CipherOutputStreamSpec — alfabeto {c1, w1, w2, fl, cl} — **monitor GLOBAL**

Arquivo: `gen_CipherOutputStreamSpec/out/CipherOutputStreamSpecRuntimeMonitor.java`
(sha256 `65df35f2…`). Tabelas `:145-149`; handler fail `:243`; sem match. Estados: 0 =
início, 2 = pós-c1, 1 = escrevendo, 3 = pós-close, 4 = fail. Monitor global (`:309`;
merge `:9448`).

| evento | 0 | 1 | 2 | 3 | 4 | fonte |
|---|---|---|---|---|---|---|
| c1 | 2 | 4 | 4 | 4 | 4 | `:145` |
| w1 (write(int) ∥ write(byte[])) | 4 | 1 | 1 | 4 | 4 | `:146` |
| w2 (write(byte[],int,int)) | 4 | 1 | 1 | 4 | 4 | `:147` |
| fl (flush()) | 4 | 1 | 1 | 4 | 4 | `:148` |
| cl (close()) | 4 | 3 | 4 | 4 | 4 | `:149` |

`fl` está DENTRO do laço `(w1|w2|fl)+`: `c1 fl cl` é aceito sem erro (PROVADO, COS-c),
enquanto o ORDER CrySL (`Constructs, Writes+, c`) exige ≥1 write — `flush` nem é evento
da regra. Mesma cascata global de FPs do CIS (COS-b/b2/b3).

## KeyPairSpec — alfabeto {c1, gpu, gpr} — **c1 não liga o parâmetro da spec**

Arquivo: `gen_KeyPairSpec/out/KeyPairSpecRuntimeMonitor.java` (sha256 `aa4c0f90…`).
Tabelas `:142-144`; fail `:231`, match `:239` (`setObjectAsInAcceptingState(keyPair)` —
campo NUNCA atribuído, ver abaixo); backend sincronizado (`:127`). Estados: 0 = início,
1 = match (pós-c1, laço gets), 2 = fail.

| evento | 0 | 1 | 2 | fonte |
|---|---|---|---|---|
| c1 (ctor; liga publicKey/privateKey/kp — NENHUM é o parâmetro `keyPair`) | 1 | 2 | 2 | `:142` |
| gpu (getPublic, target keyPair) | 2 | 1 | 2 | `:143` |
| gpr (getPrivate, target keyPair) | 2 | 1 | 2 | `:144` |

**Escopo/semântica paramétrica**: árvore mista — `Tuple2<Set, Monitor>` para o slot de
binding vazio (`KeyPairSpec__Map`, `:306`) + `MapOfMonitor` por objeto (`:307`). c1 vai
para o slot vazio e é despachado ao **CONJUNTO INTEIRO** de monitores vivos
(`stateTransitionedSet.event_c1`, `:352`; corpo executa por monitor, `Set.event_c1`
`:31-53`); gpu/gpr criam o monitor do objeto **clonando o estado do leaf vazio**
(`:387-419`). Consequências provadas (`beta_betadriveB_run1.out`):
- `gpu` como 1º evento (rota `KeyPairGenerator.generateKeyPair()` — a rota JCA padrão):
  0→2 → `InvalidSequenceOfMethodCalls` espúrio (KPR-a). O CrySL tem `co?` (ctor
  OPCIONAL); o ERE `c1 (gpu|gpr)*` o torna obrigatório.
- 2ª construção legal: TODOS os monitores vivos vão a 2 e resetam (o monitor de kp1 foi
  arrastado de 1→0 por c1 de kp2 — KPR-c2); a cascata continua no gpu de kp2 (KPR-d).
- `@match` marca **null**: o gerador materializa o parâmetro não-ligado como local
  `KeyPair keyPair = null` (`:179`) que SOMBREIA o campo homônimo (`:138`); o
  `keyPair = kp` do corpo (`:190`) escreve no local; o campo fica null para sempre
  (KPR-b2: `isInAcceptingState(kp1)==false`, `isInAcceptingState(null)==true`).

## SecretKeySpec (spec) / SecretKey (alvo) — alfabeto {e1, d}

Arquivo: `gen_SecretKeySpec/out/SecretKeySpecRuntimeMonitor.java` (sha256 `69791c1a…`).
Tabelas `:85-86`; match calculado `nextstate == 1 || nextstate == 0` (`:138`, `:149`) —
estados 0 E 1 aceitantes: `epsilon` do ERE realizado corretamente (linguagem `e1* (d|ε)`
= `ge*, d?`; sonda p6 discriminante em `beta_probes_summary.txt`). handler match vazio
(`:154-158`); **não existe categoria/handler fail**. Estado 2 = morto SILENCIOSO.
Indexação POR OBJETO `secretKey` (`MapOfMonitor`, `:225`; merge `:9512`).

| evento | 0 | 1 | 2 | fonte |
|---|---|---|---|---|
| e1 (getEncoded; condition validate(GENERATED_KEY) — EXTRA-oráculo, a regra não tem REQUIRES) | 0 | 2 | 2 | `:85` |
| d (destroy; corpo remove GENERATED_KEY) | 1 | 2 | 2 | `:86` |

Violações de ORDER (`ge` após `d`; 2º `d`) levam ao estado 2 sem NENHUM erro (PROVADO,
SKY-d/e). Corpo antes da transição: no estado morto, e1 com condition verdadeira ainda
escreve RANDOMIZED (SKY-d2). **Captura**: no caminho dexlib2 de produção a spec inteira é
INERTE — 0 wrappers, eventos jamais emitidos (`beta_weave_all.out`, seção SecretKeySpec;
`beta_report.md` §3.3).

## PBEKeySpecSpec — alfabeto {f1, f2, c1, err1, err2, err3, c2}

Arquivo: `gen_PBEKeySpecSpec/out/PBEKeySpecSpecRuntimeMonitor.java` (sha256 `30795a79…`).
Tabelas `:206-212`; fail `:359`, match `:367` (`setObjectAsInAcceptingState(spec)` — campo
corretamente atribuído em c1, sem sombreamento). Estados: 0 = início, 1 = pós-c1,
2 = match (pós-c2), 3 = fail. Indexação POR OBJETO `s` (`:491`; todos os eventos ligam
`s` — f1/f2/c1/err* por `returning`, c2 por `target`).

| evento | 0 | 1 | 2 | 3 | fonte |
|---|---|---|---|---|---|
| f1 (ctor 1-arg FORBIDDEN; corpo emite ISMC) | 0 | 3 | 3 | 3 | `:206` |
| f2 (ctor 3-arg FORBIDDEN; idem) | 0 | 3 | 3 | 3 | `:207` |
| c1 (ctor 4-arg; iter≥10000 ∧ RAND(pw) ∧ RAND(salt)) | 1 | 3 | 3 | 3 | `:208` |
| err1 (ctor 4-arg; iter<10000) | 0 | 3 | 3 | 3 | `:209` |
| err2 (ctor 4-arg; ¬RAND(pw) — **EXTRA-oráculo**: a regra só REQUIRES randomized[salt]) | 0 | 3 | 3 | 3 | `:210` |
| err3 (ctor 4-arg; ¬RAND(salt)) | 0 | 3 | 3 | 3 | `:211` |
| c2 (clearPassword; corpo remove SPECCED_KEY) | 3 | 2 | 3 | 3 | `:212` |

Advice do ctor 4-arg = 4 monitorCalls em sequência (c1, err1, err2, err3 — aspecto
`:48-58`; descriptor 1:1). Os guards de err se SOBREPÕEM (uma construção pode disparar
err1+err2+err3 — PROVADO, PBK-c). Cobertura total do ctor 4-arg: ¬(c1) = err1∨err2∨err3.
`c2` de 0→3: clearPassword de um objeto cujo ctor foi não-conforme (ou FORBIDDEN) soma um
`InvalidSequenceOfMethodCalls` de sequência à acusação específica (PBK-c2/d2) — sob a
leitura FORBIDDEN⇒c1 do CrySL, `f1, cP` seria ORDER-legal. Flags obsoletas do advice
fundido: benignas aqui (nenhum estado de categoria é alcançável entre monitorCalls do
mesmo advice — estado 1 não liga categoria; @match só em c2, advice separado).
