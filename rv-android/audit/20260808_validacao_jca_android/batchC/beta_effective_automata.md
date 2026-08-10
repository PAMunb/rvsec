# Autômatos efetivos — Batch C (extraídos dos artefatos gerados)

Agente Beta, 2026-08-09. Fonte: os `*RuntimeMonitor.java` do insumo comum da rodada
(`batchC/generation_manifest.md`), hashes conferidos antes do uso (20/20 idênticos ao
manifesto) e **re-gerados de forma independente** neste parecer com o pipeline de produção
(`-d out -merge --emit-descriptor`) — 20/20 byte-idênticos (`beta_report.md` §1). Formato
dos batches A/B: codificação de estados, tabela por evento, escopo do monitor, tudo citado
por arquivo:linha do artefato. As cinco tabelas conferidas idênticas no
`MultiSpec_1RuntimeMonitor.java` do `-merge` de produção das 23 specs (indexações em
`:9470/:9474/:9485/:9508/:9528`; compila limpo contra o runtime de produção — javac exit 0,
57 classes).

Convenções (batch B, revalidadas aqui): categorias calculadas após cada transição;
`condition(false)` = `return false` **antes** do `handleEvent` (supressão sem transição —
ex. KGN `:320`, KMF `:242`); corpo do evento executa **antes** da transição (escritas de
Property independem do estado — KST `Prop_1_event_load` `:325-337` grava
GENERATED_KEY_STORE antes de transitar; provado no drive KST-c).

## KeyGeneratorSpec — alfabeto {g1,g2,g3,i1..i5,gk1} — por objeto `k`

Arquivo: `gen_KeyGeneratorSpec/out/KeyGeneratorSpecRuntimeMonitor.java` (sha256
`de9e5205…`). Tabelas `:267-275`; fail = estado 5, match = estado 1 (`:329-330`).
Estados: 0 = início, 4 = laço g1+ , 3 = laço g2+, 2 = pós-init, 1 = aceitante (pós-gk1),
5 = fail. Indexação POR OBJETO (`KeyGeneratorSpec_k_Map`, MapOfMonitor, `:596`).

| evento | 0 | 1 | 2 | 3 | 4 | 5 | fonte |
|---|---|---|---|---|---|---|---|
| g1 (getInstance(String), cond safe) | 4 | 5 | 5 | 5 | 4 | 5 | `:267` |
| g2 (getInstance(String,Object+), cond safe) | 3 | 5 | 5 | 3 | 5 | 5 | `:268` |
| g3 (getInstance(String), cond `!safe.contains(currentAlgorithmInstance)`) | 0 | 5 | 5 | 5 | 5 | 5 | `:269` |
| i1..i5 (init overloads, before) | 5 | 5 | 5 | 2 | 2 | 5 | `:270-274` |
| gk1 (generateKey, after ret) | 5 | 5 | 1 | 1 | 1 | 5 | `:275` |

Notas de escopo/dispatch:
- **g1 e g3 compartilham o mesmo pointcut**; o advice fundido chama `g1Event` **antes** de
  `g3Event` (`KeyGeneratorSpecMonitorAspect.aj:66-72`). A condição de g3 lê o CAMPO
  `currentAlgorithmInstance` (não o argumento): para monitor fresco (`""`), g3 dispara sse
  g1 foi suprimido (alg unsafe) — comportamento efetivo equivale a `!safe.contains(alg)`,
  mas SOMENTE por causa da ordem g1→g3 no advice e do monitor fresco por getInstance.
- Trace unsafe (g3, i*, gk1): i* de 0 → 5 (fail) e, pós-`__RESET`, gk1 de 0 → 5 (fail de
  novo) — **2 InvalidSequence espúrios + 1 UnsafeAlgorithm** (PROVADO, KGN-b,
  `beta_drive_run1.out`). O ere não tem caminho unsafe→init (as fsm de KMF/TMF/SSL têm o
  estado unsafeAlg; aqui não).
- CONSTRAINT `alg=AES => keySize in {128,192,256}`: nenhum código no artefato; i1 corpo
  vazio (`.mop:76-78`); PROVADO invisível (KGN-d — o provider do JDK lança
  InvalidParameterException antes de qualquer verificação da spec).

## KeyManagerFactorySpec — alfabeto {g1,g2,g3,i1,i2,gkm1} — por objeto `k`

Arquivo: `gen_KeyManagerFactorySpec/out/KeyManagerFactorySpecRuntimeMonitor.java`
(sha256 `dca6fb37…`). Tabelas `:192-197`; fail = 3, match1 = 2 (`:251-252`).
Estados: 0 = início **e** unsafeAlg (minimização fundiu os dois — CoenableProbe:
states_after_min = 3), 1 = waitingInit, 2 = final (match1), 3 = fail. Por objeto
(`KeyManagerFactorySpec_k_Map`, `:464`).

| evento | 0 | 1 | 2 | 3 | fonte |
|---|---|---|---|---|---|
| g1 (getInstance(String), cond PKIX) | 1 | 3 | 1 | 3 | `:192` |
| g2 (getInstance(String,..) && args(alg,*), cond PKIX) | 1 | 3 | 1 | 3 | `:193` |
| g3 (getInstance(String), cond !PKIX) | 0 | 3 | 3 | 3 | `:194` |
| i1 (init(KeyStore,char[]), before) | 3 | 2 | 3 | 3 | `:195` |
| i2 (init(ManagerFactoryParameters), before) | 3 | 2 | 3 | 3 | `:196` |
| gkm1 (getKeyManagers, after ret) | 3 | 3 | 0 | 3 | `:197` |

Notas: i1/i2 de 0 (= unsafeAlg) → 3: o trace unsafe (g3, i1, gkm1) rende **2
InvalidSequence espúrios + 1 UnsafeAlgorithm** (PROVADO, KMF-b) — o estado unsafeAlg
evita o fail imediato no getInstance, mas o init seguinte falha (família resíduo,
D-S10). gkm1 → 0 permite novo ciclo g1… (reuso além do ciclo único do ORDER CrySL).
No caminho dexlib2 de produção o site 1-arg dispara g1, g3 **e g2** (ver
`beta_report.md` §4): g1 (0→1) seguido de g2 (1→3) = fail imediato em TODO
getInstance("PKIX") legal (PROVADO, DX-1).

## TrustManagerFactorySpec — alfabeto {g1,g2,g3,i1,i2,gtm1} — por objeto `mf`

Arquivo: `gen_TrustManagerFactorySpec/out/TrustManagerFactorySpecRuntimeMonitor.java`
(sha256 `a99d7d54…`). Tabelas `:193-198`; fail = 3, match1 = 2 (`:252-253`). MESMA tabela
de KMF (gtm1 no lugar de gkm1). Por objeto (`TrustManagerFactorySpec_mf_Map`, `:465`).

**Reparo gh101 verificado no artefato**: gtm1 liga `target(mf)` e retorna
`TrustManager[]` (aspecto `:92-97`; assinatura real conferida por javap dos bytes
extraídos da android-30), escreve GENERATED_TRUST_MANAGERS; g3 tem linha viva
{0,3,3,3} (`:195`), não all-fail; indexação por objeto. Isolamento do remove de dois
argumentos PROVADO: o @fail de tmf2 retira a marca do próprio array e preserva a de
tmf1 (TMF-b2/b3/b4, `beta_drive_run1.out`). A sonda pF1 reconstrói o defeito pré-gh101
(g3 fora da fsm → all-fail silencioso) no toolchain congelado
(`beta_probes_summary.txt`).

Nota de observabilidade: gtm1-antes-de-init é INVISÍVEL na prática — a plataforma lança
IllegalStateException antes do retorno e o advice é after-returning (PROVADO, TMF-b);
o canal fail vivo foi exercitado pela rota re-init-após-gtm (TMF-b2).

## SSLContextSpec — alfabeto {g1,g2,unsafe_protocol,init,engine} — por objeto `ctx`

Arquivo: `gen_SSLContextSpec/out/SSLContextSpecRuntimeMonitor.java` (sha256
`ea212b12…`). Tabelas `:170-174`; fail = 3, match1 = 1 (`:228-229`). Estados: 0 = início
**e** unsafeProtocol (fundidos na minimização), 2 = s1, 1 = end (match1), 3 = fail.
Por objeto (`SSLContextSpec_ctx_Map`, `:420`).

| evento | 0 | 1 | 2 | 3 | fonte |
|---|---|---|---|---|---|
| g1 (getInstance(String), cond protocolo safe, case-fold) | 2 | 3 | 3 | 3 | `:170` |
| g2 (getInstance(String,String)) | 2 | 3 | 3 | 3 | `:171` |
| unsafe_protocol (mesmo pointcut de g1, cond !safe) | 0 | 3 | 3 | 3 | `:172` |
| init (init(KM[],TM[],SR), after) | 3 | 3 | 1 | 3 | `:173` |
| engine (createSSLEngine — **pointcut morto**) | 3 | 1 | 3 | 3 | `:174` |

Notas:
- **engine é evento morto nas duas metades**: o pointcut declara retorno `void`
  (`.mop:90`, aspecto `:59`) e `createSSLEngine()` retorna `SSLEngine` na android-30
  (javap dos bytes extraídos) — ajc: 0 join points (site cse0/cse2 NONE,
  `beta_capture_matrix.txt`); dexlib2: 0 wrappers (UNTOUCHED, `beta_weave_all.out`).
  A linha `:174` é inalcançável por captura; GENERATE_SSL_ENGINE nunca é escrito
  (PROVADO, SSL-b/DX-6b). A violação CrySL engine-antes-de-init também é invisível
  (SSL-b2 — e a plataforma lança ISE antes, de qualquer forma).
- getInstance(String, Provider) — CrySL `g2: getInstance(protocol, _)` — NÃO é capturado
  por nenhum evento (ajc NONE; dexlib2 UNTOUCHED): criação legal sem monitor.
- unsafe_protocol + init: init de 0 → 3 = **1 InvalidSequence espúrio + UnsafeProtocol**
  (PROVADO, SSL-c). g1 aceita minúsculas via `toUpperCase()` (SSL-d) — leitura
  case-insensitive do constraint (dado para o teste D-piloto-2a).

## KeyStoreSpec — alfabeto {g1,g2,load,store,ge1,se1,gk1} — **monitor GLOBAL**

Arquivo: `gen_KeyStoreSpec/out/KeyStoreSpecRuntimeMonitor.java` (sha256 `45befd0b…`).
Tabelas `:242-248`; fail = 5, match = 1 (`:299-300`). Estados: 0 = início, 4 = pós-g1,
1 = loaded (base do laço, aceitante), 3 = pós-ge1, 2 = pós-se1, 5 = fail.

| evento | 0 | 1 | 2 | 3 | 4 | 5 | fonte |
|---|---|---|---|---|---|---|---|
| g1 (getInstance(String), cond tipo safe) | 4 | 4 | 5 | 5 | 5 | 5 | `:242` |
| g2 (mesmo pointcut, cond !safe) | 0 | 0 | 5 | 5 | 5 | 5 | `:243` |
| load (load(..), before) | 5 | 5 | 5 | 5 | 1 | 5 | `:244` |
| store (store(..), before) | 5 | 5 | 1 | 5 | 5 | 5 | `:245` |
| ge1 (getEntry, before) | 5 | 3 | 5 | 5 | 5 | 5 | `:246` |
| se1 (setEntry, before) | 5 | 2 | 5 | 5 | 5 | 5 | `:247` |
| gk1 (getKey, after ret) | 5 | 1 | 5 | 1 | 5 | 5 | `:248` |

**Escopo do monitor — a forma KPR/CIS na spec inteira**: a spec declara `KeyStoreSpec(KeyStore ks)`
(`.mop:21`) mas TODOS os eventos ligam a variável `k`, nunca `ks` — nenhum evento liga o
parâmetro da spec. A árvore de indexação é `Tuple2<Set,Monitor>` com dispatch incondicional
`matchedEntry = KeyStoreSpec__Map` (`:498`, `:521-556`; merge `:9485`); qualquer evento cria
o monitor único (`:585-599`); `AbstractSynchronizedMonitor`, único da rodada (`:221`). A
linguagem acima vale para a CONCATENAÇÃO de todos os KeyStore do processo. Consequências
PROVADAS (`beta_drive_run1.out`):
- dois KeyStore legais intercalados → **4 InvalidSequenceOfMethodCalls espúrios** (KST-b:
  g1,g1 → 5; cascata em load/load/getKey);
- `getInstance(tipo, Provider)` — CrySL `g2: getInstance(keyStoreAlg, _)` — não tem
  pointcut: criação invisível; o load seguinte transita no monitor global e o corpo grava
  GENERATED_KEY_STORE **no campo `keyStore` = último g1**, não no receptor: medido
  mark(ksE)=true (nunca deu load) / mark(ksF)=false (deu load) — FP+FN de identidade
  (KST-c), com FP encadeado em KMF.init (KST-d);
- no caminho dexlib2, ge1/se1 são silenciosamente NÃO tecidos (tipos aninhados
  `KeyStore$Entry`/`$ProtectionParameter` viram `KeyStore/Entry` no TypeResolver —
  `beta_report.md` §4), então a rota legal `sE, Stores` vira fail espúrio (DX-5c).
- g2 de 1 → 0: um getInstance de tipo unsafe REBAIXA o monitor global do estado loaded —
  contaminação entre objetos adicional (não exercitada em drive; tabela `:243`).
