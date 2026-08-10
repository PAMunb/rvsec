# JUIZ — Síntese da rodada-piloto (CipherSpec, GCMParameterSpecSpec)

Juiz (LLM-as-a-Judge) · 2026-08-08. Papel: síntese de evidência — **não** oráculo formal,
**não** decisão por maioria. Contraexemplo reproduzível não é descartável por consenso;
alegação só de leitura não fecha claim de toolchain; `INCONCLUSIVE` nunca vira aprovação.
Pesos e denominadores do score: pré-publicados em `fase0/pre_registro.md` §6 — usados sem
alteração. Insumos: os 12 arquivos `alfa_*`/`beta_*`/`gama_*` de `pilot/` e os brutos em
scratch (`{alfa,beta,gama}/`). Claims citados pelos IDs originais; resolução claim a claim
em `juiz_claims_resolvidos.csv` (72 claims: 34 Alfa, 20 Beta, 18 Gama).

## 0. O que o juiz executou (evidência própria, não delegada)

Fatos medidos por mim nesta sessão (comandos reproduzíveis; scratch dos agentes intocado):

1. **Identidade das gerações independentes**: as tabelas de transição do
   `CipherSpecRuntimeMonitor.java` gerado por Beta (`beta/gen_cipher/out/`, linhas 405-418)
   e por Gama (`gama/gen_cipher/`, linhas 405-418) são **idênticas linha a linha**; idem o
   GCM (`Prop_1_transition_c1[] = {1,2,2}`, linha 93 em ambos). Duas rotas de geração
   independentes produziram o mesmo artefato — a base do teste discriminante é estável.
2. **Teste discriminante linguagem (executado)**: caminhada programática dos contraexemplos
   de Alfa sobre as tabelas **do artefato** de Beta (parse direto do `.java` gerado, não da
   transcrição em `beta_autometa_efetivo_cipher.md`). Resultado integral na §2.1 — os cinco
   contraexemplos confirmados.
3. **Cascata pós-`__RESET`** (ALFA-CIP-22): no artefato, `u1[0]=f1[0]=f2[0]=wkb1[0]=5` —
   todo u/f a partir do estado 0 é fail. Confirmado.
4. **`g3` → `init` espúrio** (ALFA-CIP-06/GAMA-CIP-02): `g3[0]=0`, `init2[0]=5`; e no corpo
   gerado (`Prop_1_event_init2`) a ordem é corpo → `handleEvent` → flags/handler. Confirmado.
5. **Citações estruturais conferidas no fonte** (regra do projeto: verificar o código antes
   de afirmar mecanismo): `ExecutionContext.validate(Property, Object)` é binário
   propriedade+objeto, sem casa para o algoritmo (rvsec-core `ExecutionContext.java:118-120`);
   `ErrorDescription` de 3 args delega com `"unknown"` (`ErrorDescription.java:34-36`);
   `GCMParameterSpecSpec.mop` tem dois `event c1` (linhas 23 e 34) e `ere : c1 | c2` (48);
   o prólogo de condition faz `return false` **antes** de `handleEvent` (artefato gerado,
   `Prop_1_event_init2`); o wrapper estático descarta o retorno booleano do evento e testa
   as flags em seguida (artefato, gen_cipher `:917-924`); a config da estática defaulta
   `mop_dir` para o literal `.../resources/jca` e sonda `android_jar` em
   `["33","29","28","27","26"]` — sem `"30"` (`rv_static_analysis/config.py:199-206` e
   `:186-194`); `get_static_analysis_config()` constrói `RVStaticAnalysisConfig` sem passar
   `mop_dir`/`targets_file` (`rv_experiment/config.py:941-950`); o monitor e o aspecto
   gerados do GCM importam `java.util.*` na linha 8 (resolve ALFA-GCM-08).

Distinção mantida ao longo do documento: **fato medido** (execução/artefato desta rodada),
**observado em artefato** (leitura de código/artefato citada), **inferido** (dedução sem
execução), **histórico** (errors.csv pré-GH100/GH101 — só gera hipóteses).

## 1. Matriz de conflitos/convergências

Cada rota listada tem evidência primária própria (verifiquei uma a uma); convergência
independente aumenta confiança, mas a resolução cita sempre a evidência primária decisiva.

| # | Fenômeno / Claims | Alfa | Beta | Gama | Evidência conflitante | Teste discriminante | Resolução | Incerteza residual |
|---|---|---|---|---|---|---|---|---|
| 1 | Linguagem ORDER Cipher: re-init, multi-update, mistura wrap×doFinal — ALFA-CIP-01/02/03 × BETA-CIP-09 | FAIL vs CrySL (modelo da **sintaxe** `.mop`) | PASS "fiel ao `.mop`" (autômato **efetivo**) | — (usa o efetivo p/ diagnóstico) | Conflito **aparente**: comparações com referências distintas (CrySL×MOP vs MOP×artefato) | **Executado** (§2.1): walk dos 5 contraexemplos de Alfa sobre as tabelas do artefato | FAIL — as duas medições compõem: artefato fiel ao `.mop` E `.mop` diverge do CrySL ⇒ artefato diverge do CrySL. INCORRETA ×3, crítica | Precedência do ORDER (fenômeno 2); dimensão 7 (weaving/execução) fora do piloto |
| 2 | Precedência do ORDER no oráculo — ALFA-CIP-04 | INCONCLUSIVE (gramática MetaCrySL inverte a do CrySL oficial; leitura B degenerada) | — | — | — | Sanity check de Alfa (leitura B exclui uso normal) — não substitui verificação do Xtext upstream | INCONCLUSIVE (ambiguidade do oráculo, não da spec) | Xtext oficial não conferido; decisão única necessária antes da rodada das 23 |
| 3 | GCM `c1` duplicado + `c2` órfão — ALFA-GCM-01/02, BETA-GCM-02, GAMA-GCM-01 | INCONCLUSIVE (hipótese H-GCM) | PASS(linguagem)/FAIL(texto): artefato com 1 tabela, 2 carriers, c2 morto | FAIL (fail-open do gerador; geração própria limpa) | Nenhum — três rotas convergem no fato; divergem no rótulo | Identidade das 2 gerações independentes conferida pelo juiz (§0.1) | H-GCM **confirmada** ⇒ ALFA-GCM-01/02 viram PASS; linguagem = DIVERGÊNCIA_EQUIVALENTE_COMPROVADA; aceitação silenciosa de símbolo indefinido = defeito de toolchain (GAMA-GCM-01 FAIL, latente) | Equivalência vale pela estrutura desta spec (disjunção 1-de-2); não generaliza a specs maiores |
| 4 | GCM `@fail` morto — BETA-GCM-04, GAMA-GCM-02 | (nota em ALFA-GCM §1.2) | FAIL: alcançabilidade no artefato (2º c1 no mesmo monitor impossível) | FAIL: mesma prova + corroboração histórica (0 linhas em 97.018) | Nenhum | Prova estrutural já é discriminante; histórico é só corroboração (zero ≠ conformidade) | FAIL — `@fail` é código morto; spec sem canal próprio de acusação | Nenhuma relevante (prova estrutural) |
| 5 | GCM supressão de CONSTRAINT/REQUIRES (família D-S9) — ALFA-GCM-03/04, GAMA-GCM-03, BETA-GCM-04 §4 | INCORRETA, crítica (FN terminal realizável) | "limitação herdada do desenho, a registrar" | INCORRETA, crítica | **Conflito real de classificação**: limitação × defeito | Critério §4 do pré-registro (FN demonstrável em trace realizável = crítica) + contraprova de inevitabilidade: os 4 REQUIRES do próprio CipherSpec lidos **no corpo** provam que a alternativa existe | FAIL — INCORRETA (mecânica), valores fiéis; crítica. Classificação de Beta ajustada com justificativa: não é LIMITAÇÃO_INEVITÁVEL porque a alternativa é demonstrada na mesma base de código | Nenhuma sobre o mecanismo; impacto de conjunto depende de auditoria das 23 |
| 6 | Resíduo D-S9 no Cipher (`generatedKey` em `condition`) — ALFA-CIP-08, GAMA-CIP-03, Beta §2 | FAIL crítica (FN terminal + acusação deslocada) | (constata a mecânica no artefato, sem rotular) | FAIL major (evento e sítio errados; misuse key aponta método errado) | Nenhum — três rotas: texto+registro gh101 / artefato / cadeia diagnóstica | `return false` antes de `handleEvent` verificado pelo juiz no artefato (§0.5) | FAIL — INCORRETA, deliberada e registrada (`divergence_record.csv`), mas registrado ≠ aprovado no gate; crítica (FN terminal realizável) | Frequência real do FN terminal exige execução (G10, fora do piloto) |
| 7 | `generatedKey` 2ª casa (concordância chave-algoritmo) — ALFA-CIP-07 | FAIL crítica (store unário; escrita sem algoritmo) | — | (tabela sinergia nota o validate, sem a 2ª casa) | Rota única | Verificação do juiz: `validate` sem casa de algoritmo (§0.5); ausência em `predicate_omissions.csv` relatada por Alfa e não contestada | FAIL — OMITIDA **sem registro**; crítica (chave AES aceita em cipher DESede) | Nenhuma sobre o mecanismo |
| 8 | `@fail` espúrio junto a erro específico (`g3`→`init`) — ALFA-CIP-06, GAMA-CIP-02 (+H2 histórico) | FAIL (semântica **assumida** do handler) | (artefato dá a ordem corpo→handleEvent→handler) | FAIL **PROVADO** no artefato | Nenhum | Confirmado pelo juiz na tabela e no corpo gerado (§0.4); H2 (TMF 4.599 pares) fica como hipótese histórica, não prova | FAIL — INCORRETA (diagnóstico), major; a pendência executável de Alfa está sanada pelo artefato | Nenhuma estrutural |
| 9 | Cascata pós-`__RESET` — ALFA-CIP-22 | FAIL (assumido da sintaxe) | (tabela efetiva publicada) | (dedupe pode mascarar — GAMA-CIP-04) | Rota única + interação com dedupe | Confirmado pelo juiz: todo u/f em estado 0 → 5 (§0.3); dedupe in-JVM mascara só repetições no **mesmo** `__LOC` | FAIL — INCORRETA (diagnóstico/ruído), major | Magnitude do ruído em execução real (G10) |
| 10 | Handler re-executa sobre evento suprimido (flags obsoletas) — BETA-CIP-06, GAMA-CIP-08 | — | FAIL (gen_cipher `:917-924`) | FAIL (gen_gcm `:38-44`) | Nenhum — duas rotas, dois artefatos | Padrão verificado pelo juiz no gen_cipher (§0.5) | FAIL — defeito de mecanismo do **gerador** (rv-monitor), benigno nas 2 specs do piloto; major como padrão set-wide | Não exercitado em runtime; sem cenário concreto não-idempotente no piloto |
| 11 | Diagnóstico inatribuível — GAMA-CIP-01 (`unknown`), GAMA-CIP-04 (colisão dedupe), GAMA-CIP-05 (sem campo de conjunto), GAMA-CIP-06 + ALFA-CIP-23 (mensagem engana/elide) | CIP-23 FAIL | (BETA-CIP-07: `__LOC` presente, PASS com ameaça A2) | FAIL ×4 PROVADO | Nenhum — Beta mede presença do `__LOC`, Gama mede suficiência da atribuição: complementares | `unknown` verificado pelo juiz no construtor (§0.5); 70.760/97.018 é corroboração histórica | FAIL nos 5; BETA-CIP-07 PASS (a expansão existe — a insuficiência é dos campos, não da expansão) | `__LOC` sob DEX (A2/GAMA-SET-04) fora do piloto |
| 12 | Captura de pointcuts — BETA-CIP-04/05, BETA-GCM-03, ALFA-CIP-05, ALFA-GCM-05 | PASS com ressalvas de borda (classe adversarial; 3º arg null) | PASS **MEDIDO** (matcher de produção; 28/28 e 2+2; DISJOINT; vizinhos livres; insensível ao G10) | — | Nenhum — Alfa inferiu das assinaturas, Beta mediu com o matcher real | Triangulação do próprio Beta (harness stock × ctor; android-30 × 37.0) | PASS — G5 no escopo do piloto; ressalvas de Alfa registradas como ameaças (não realizadas em API real) | Weave real não exercitado (G6); `after returning` + ctor da GCM inferido da API p/ ALFA-GCM-05 |
| 13 | Gerabilidade/orçamento — BETA-CIP-01/02/03, BETA-GCM-01, BETA-SET-01/02, ALFA-CIP-24 | PASS sintático (14 eventos) | PASS **MEDIDO** (14≤17; coenable saturado 229.362; 6,66 s/1,04 GB; conjunto 28,09 s/1,71 GB; determinismo por hash) | PASS implícito (gerações limpas) | Nenhum | — | PASS — G2 no escopo do piloto | Teto 17 é alegação gh101 sem output bruto commitado (fase 0) |
| 14 | CONSTRAINTS do Cipher — ALFA-CIP-14 (literais), 14a (componente ausente), 14b (folding), 15 (encmode), 16 (comprimentos), 17 (c2 noCallTo), 18 (c3 callTo) | 14 PASS; 14a/15/16/17/18 FAIL; 14b FAIL | — | (sinergia diz "OMITIDA registrada" p/ c2/c3) | Conflito menor Alfa×Gama sobre "registrada": Alfa não achou em `data/gh101`; Gama cita comentário do spec/tarefa 4.11 | Resolução documental: comentário no spec ≠ registro formal de omissão (critério §4: OMITIDA sem registro é major) | 14 PASS; 14a FAIL (INCORRETA vs oráculo cru); 15/16 FAIL OMITIDA minor; 17 FAIL OMITIDA crítica (sem registro algum); 18 FAIL OMITIDA major (comentário existe, registro formal não); **14b rebaixado a INCONCLUSIVE** (ver §2.3) | 14a: semântica de `part()` sobre componente ausente no CogniCrypt não verificada (a convenção `''` vem dos literais do próprio oráculo); 14b: equivalência JCA case-insensitive não testada |
| 15 | Estática usa `jca` e nunca `android-30` — GAMA-SET-01/03 | — | — | FAIL PROVADO | Rota única; contradiz a ressalva "sem fallback silencioso" da fase 0 (que valia só p/ monitores) | Verificado pelo juiz no fonte: literal `jca` e lista de probe sem `"30"` (§0.5) | FAIL ×2 — defeito de toolchain (major/minor); mina G12 e qualquer braço `jca_android` com métricas estáticas | Magnitude prática (sobreposição classe/método entre conjuntos) não quantificada |
| 16 | Identidade e dedupe multi-camada — GAMA-SET-02, GAMA-SET-06 | — | — | FAIL (join (classe,método); 3 chaves inconsistentes; linha morre antes do CSV) | Rota única, evidência direta de código | — | FAIL ×2 — major (reprodutibilidade/diagnóstico de conjunto) | — |
| 17 | Pendências Android — BETA-CIP-08 (`after` ajc×dexlib2), GAMA-SET-04 (`__LOC` DEX), GAMA-SET-05 (truncamento), BETA-SET-03 (nível DEX gh100) | — | INCONCLUSIVE / PASS(código) | INCONCLUSIVE ×2 | Nenhum | Exigem weave+dispositivo (G6/G10 — fora do piloto) | INCONCLUSIVE (3); BETA-SET-03 PASS **no escopo código**, com pendência DEX explícita | Todas abertas para a fase de execução |
| 18 | Histórico errors.csv — GAMA-SET-07 (H1–H7) | — | — | INCONCLUSIVE (gerador de hipóteses; unidades declaradas) | Nenhum | — | INCONCLUSIVE — fora do denominador; H4 (rótulo vazio em Signature/MD/Mac) é resíduo **não explicado** pela narrativa do Grupo 8: hipótese nova obrigatória na rodada das 23 | Dados pré-reparo; zero nunca é conformidade |
| 19 | ENSURES extra-oráculo — ALFA-CIP-20 (generatedCipher), ALFA-CIP-21 (WRAPPED_KEY) | 20 FAIL / 21 PASS | (artefato confirma `setProperty(GENERATED_CIPHER, c)` no ramo condicionado) | (sinergia: "âncora dupla") | Nenhum | Escrita confirmada pelo juiz no corpo gerado do init2 (§0.5) — inclusive a incoerência: a marca é gravada mesmo quando `reportUnsafeTransformation` acusa | 20 FAIL — INCORRETA minor (extra-oráculo registrado com âncora 1.5.2; incoerência interna g3); 21 PASS (efeito morto registrado) | Escolha de âncora é decisão de pesquisa — candidata a redução formal de escopo |
| 20 | Tese D-S10 (freeze byte-a-byte) — ALFA-GCM-07 + hashes de Beta | PASS (registro) | (`.rvm` byte-idêntico nos 3 modos) | (cmp confirmado) | Nenhum | — | PASS — freeze é byte-a-byte, não comportamental: os defeitos do GCM são herdados e não alcançados pela gh101 | — |

## 2. Resoluções detalhadas (o que mudou e por quê)

### 2.1 Teste discriminante de linguagem — executado e integral

Caminhada dos contraexemplos de Alfa sobre as tabelas do artefato gerado
(`beta/gen_cipher/out/CipherSpecRuntimeMonitor.java:405-418`; estados 0=start∪unsafeAlg,
3=s1, 1=s2, 2=s3, 4=end/match1, 5=fail; representante por classe de fusão — as tabelas de
`init2/3/4`, `u1/u3/u5` e `f2/f5/f7` são idênticas dentro de cada classe):

| Trace | Caminhada no artefato | Resultado | Confirma |
|---|---|---|---|
| `G I I` | 0→3→1; `init2[1]=5` | **@fail** no 3º evento; CrySL aceita `Inits+` (G I I W ∈ L) | ALFA-CIP-01: **FP** |
| `G I U U` | 0→3→1→2; `u1[2]=5` | **@fail** no 4º evento; CrySL aceita `updates+` | ALFA-CIP-02: **FP** |
| `G I W Fw` | 0→3→1→4; `f2[4]=4` | termina em 4, **aceitante**; fora de L(CrySL) (ramos `w+` × DOFINALS exclusivos) | ALFA-CIP-03: **FN** |
| `G I Fw W` | 0→3→1→4; `wkb1[4]=4` | idem — aceitante fora de L(CrySL) | ALFA-CIP-03: **FN** |
| `G I W U` | 0→3→1→4; `u1[4]=2` | termina em 2, não-aceitante e **sem @fail** onde CrySL viola | ALFA-CIP-03: **FN de veredito** |
| pós-fail | `__RESET`→0; `u1[0]=f1[0]=f2[0]=wkb1[0]=5` | cada u/f seguinte re-acusa | ALFA-CIP-22 |
| `g3` depois `init` | `g3[0]=0`; `init2[0]=5`; corpo executa antes de `handleEvent` | acusação dupla na mesma chamada | ALFA-CIP-06 / GAMA-CIP-02 |

**Fechamento dos claims de linguagem do Cipher**: FAIL (INCORRETA), agora com evidência de
artefato, não só de sintaxe — a condicionalidade declarada por Alfa está sanada. O aparente
conflito com BETA-CIP-09 (PASS) se dissolve: Beta provou fidelidade artefato↔`.mop`; Alfa
provou divergência `.mop`↔CrySL; a composição (verificada acima) prova divergência
artefato↔CrySL. GCM: o produto de Alfa (sem separador até comprimento 12, sob H-GCM) mais a
confirmação de H-GCM no artefato fecham ALFA-GCM-02 como PASS firme.

Ressalva de escopo mantida: tudo módulo α e módulo a leitura (A) da precedência
(ALFA-CIP-04 segue INCONCLUSIVE — é ambiguidade do oráculo; sob a leitura B degenerada nada
disso muda de sinal, pois B exclui até o uso normal).

### 2.2 Claims que mudaram de posição na resolução do juiz

| Claim | De → Para | Justificativa |
|---|---|---|
| ALFA-GCM-01 | INCONCLUSIVE → **PASS** (DIVERGÊNCIA_EQUIVALENTE_COMPROVADA) | H-GCM confirmada por dois artefatos independentes (Beta e Gama, tabelas idênticas — §0.1): homônimos viram carriers do mesmo símbolo, `c2` morto, linguagem = intenção |
| ALFA-GCM-02 | PASS condicional → **PASS firme** | mesma razão |
| ALFA-GCM-08 | INCONCLUSIVE → **PASS** | `java.util.*` injetado na linha 8 do monitor e do aspecto gerados — verificado pelo juiz (§0.5); dependência acidental do preâmbulo registrada (nota de Beta) |
| ALFA-CIP-06, ALFA-CIP-22 | FAIL (semântica assumida) → **FAIL provado** | ameaça de validade sanada pelo artefato (§2.1); posição não muda, o grau de evidência sim |
| ALFA-CIP-14b | FAIL → **INCONCLUSIVE** | a divergência textual (folding aceita strings que o oráculo cru rejeita) é fato; mas o **impacto** depende da resolução case-insensitive do JCA, não testada. Sem o teste, nem DIVERGÊNCIA_EQUIVALENTE (não provada) nem INCORRETA (FN não demonstrado em comportamento). Fica fora do denominador e impede score completo |
| GAMA-CIP-07 | FAIL (INFERIDO) → **INCONCLUSIVE** | o escape comentado é fato (`ErrorCollector.java:39-51`), mas o dano exige string do app com `\n` que **sobreviva ao JCA**: nos eventos do Cipher (`after returning`) `getInstance` rejeita transformação malformada antes do evento. Dano não demonstrado em trace realizável no piloto; teste de harness pendente para specs que serializam outras strings |
| BETA-GCM-04 (classificação) | "limitação a registrar" → **defeito INCORRETA** no fenômeno agregado (com ALFA-GCM-03/04, GAMA-GCM-03) | critério pré-registrado §4: FN demonstrável em trace realizável é crítica e bloqueia APROVADA; e não é LIMITAÇÃO_INEVITÁVEL porque os 4 REQUIRES lidos no corpo do próprio CipherSpec provam a alternativa. O recorte de Beta (sem FN de conjunto **se** o objeto chega ao init GCM) permanece válido como atenuante de impacto, não de classificação |

Nenhum contraexemplo foi descartado; nenhuma resolução usou contagem de agentes.

### 2.3 Rotas únicas — como foram fechadas sem convergência

ALFA-CIP-07 (2ª casa do `generatedKey`), GAMA-SET-01/03 (estática), GAMA-SET-02/06
(identidade/dedupe), ALFA-CIP-23 e GAMA-CIP-05/06: todas fechadas por **verificação direta
do juiz no fonte** (§0.5) — não por confiança no relator. ALFA-CIP-14a fica FAIL com
incerteza residual declarada: a leitura de `''` como membro explícito de conjunto vem dos
literais do próprio oráculo (RSA e ChaCha20 listam `''`; AES não), que é a melhor evidência
disponível sob o oráculo cru pré-registrado; a semântica de `part()` do CogniCrypt real
segue não verificada e a rodada das 23 deve padronizar esse teste.

## 3. Classificação consolidada das divergências resolvidas

- **DIVERGÊNCIA_EQUIVALENTE_COMPROVADA**: fusões D-S11 (ALFA-CIP-05, com ameaças de borda
  registradas); GCM c1/c2 no plano da linguagem (ALFA-GCM-01/02, BETA-GCM-02); condições
  extras do ctor 4-args (ALFA-GCM-05, equivalência via API documentada — INFERIDO);
  projeção do ENSURES `encrypted` (ALFA-CIP-19, projeção registrada, FN latente da 2ª casa).
- **LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA**: `preparedAlg` (ALFA-CIP-12, D-S14 — produtor sem
  spec no conjunto); `WRAPPED_KEY` efeito morto (ALFA-CIP-21). Ambas bloqueiam alegação de
  aderência total, como manda o modelo semântico §7.
- **OMITIDA**: 2ª casa de `generatedKey` (ALFA-CIP-07 — **sem registro**, crítica);
  c2 `noCallTo(IWOIV)` (ALFA-CIP-17, crítica, sem registro); c3 `callTo(iv)` (ALFA-CIP-18,
  major, só comentário); c4 encmode (ALFA-CIP-15, minor); c5–c8 comprimentos (ALFA-CIP-16,
  minor); offsets/lens sem constraint (seção OBJECTS).
- **INCORRETA**: linguagem do Cipher ×3 (ALFA-CIP-01/02/03, críticas); supressão por
  condition — Cipher `generatedKey` (ALFA-CIP-08) e GCM tLen/randomized (ALFA-GCM-03/04,
  GAMA-GCM-03), críticas; componente ausente (ALFA-CIP-14a, major); diagnóstico: `unknown`
  (GAMA-CIP-01), espúrio (ALFA-CIP-06/GAMA-CIP-02), cascata (ALFA-CIP-22), deslocamento
  (GAMA-CIP-03), dedupe (GAMA-CIP-04), sem campo de conjunto (GAMA-CIP-05), mensagens
  (ALFA-CIP-23/GAMA-CIP-06), `@fail` morto do GCM (GAMA-GCM-02/BETA-GCM-04);
  `generatedCipher` extra-oráculo (ALFA-CIP-20, minor); defeitos de toolchain: flags
  obsoletas (BETA-CIP-06/GAMA-CIP-08), fail-open de símbolo (GAMA-GCM-01), exit 0 com erro
  (BETA-SET-04), estática `jca`/sem api30 (GAMA-SET-01/03), identidade/dedupe
  (GAMA-SET-02/06).
- **INCONCLUSIVA** (7 — fora do denominador, impedem score completo): ALFA-CIP-04
  (precedência do oráculo), ALFA-CIP-14b (folding×JCA), BETA-CIP-08 (`after` ajc×dexlib2),
  GAMA-CIP-07 (newline), GAMA-SET-04 (`__LOC` DEX), GAMA-SET-05 (truncamento), GAMA-SET-07
  (histórico — gerador de hipóteses).

## 4. Score descritivo (pesos pré-registrados; denominadores explícitos)

Denominador por dimensão = claims **resolvidos pelo juiz** (PASS+FAIL) na dimensão;
INCONCLUSIVE fora do denominador. Sem média entre agentes. Atribuição de cada claim a uma
dimensão está no CSV.

| Dimensão | Peso | Resolvidos | PASS | FAIL | INCONCLUSIVE (fora) | Subscore |
|---|---|---|---|---|---|---|
| Linguagem formal | 20 | 7 | 4 | 3 | 1 (ALFA-CIP-04) | 20×4/7 = **11,4** |
| Captura de eventos | 20 | 5 | 5 | 0 | 0 | **20,0** |
| Bindings/cláusulas | 15 | 9 | 3 | 6 | 1 (ALFA-CIP-14b) | 15×3/9 = **5,0** |
| Predicados/composição | 15 | 13 | 8 | 5 | 0 | 15×8/13 = **9,2** |
| Toolchain Android | 15 | 15 | 9 | 6 | 1 (BETA-CIP-08) | 15×9/15 = **9,0** |
| Diagnóstico | 10 | 12 | 1 | 11 | 2 (GAMA-CIP-07, GAMA-SET-04) | 10×1/12 = **0,8** |
| Reprodutibilidade | 5 | 4 | 2 | 2 | 2 (GAMA-SET-05, GAMA-SET-07) | 5×2/4 = **2,5** |
| **Total** | 100 | **65** | 32 | 33 | **7** | **≈ 58,0** |

**Rótulos obrigatórios**: score **descritivo e INCOMPLETO** (7 INCONCLUSIVE fora do
denominador) ≠ probabilidade de correção ≠ veredito; não arredondado; **não abre gate**.
Duas leituras de contexto: (i) o denominador conta claims, e fenômenos convergentes geram
claims em mais de um agente (ex.: a supressão do GCM aparece em 3 claims) — o score pondera
evidência, não fenômenos; (ii) captura 20/20 e diagnóstico 0,8/10 no mesmo conjunto ilustram
por que média/compensação entre dimensões é proibida.

## 5. Vereditos-piloto por spec

Gates no escopo do piloto: G2 (gerabilidade), G3 (linguagem), G4 (cláusulas/bindings),
G5 (pointcuts), G7 (predicados/composição), G9 (diagnóstico). **Fora do escopo (não
executados)**: G6 (weaving/artefatos ponta a ponta em device), G8 (testes
diferenciais/mutação), G10 (execução Android/observacional), e o fechamento de G11/G12/G13
(a rodada só os alimenta).

### CipherSpec — **REPROVADA** (no escopo do piloto)

| Gate | Resultado | Fundamento |
|---|---|---|
| G2 | PASS | geração limpa medida; 14≤17; coenable saturado 229.362; 6,66 s/1,04 GB (BETA-CIP-01/02/03) |
| G3 | **FAIL** | 3 contraexemplos confirmados no artefato (§2.1): re-init FP, multi-update FP, mistura wrap×doFinal FN — INCORRETA, críticos |
| G4 | **FAIL** | c2/c3/c4/c5–c8 OMITIDAs (c2 sem registro algum, crítica); componente ausente INCORRETA (14a); literais fiéis (14) não compensam |
| G5 | PASS | partição exata 28/28 no android-30 real, DISJOINT, vizinhos livres, insensível ao G10 (BETA-CIP-04) |
| G7 | **FAIL** | 2ª casa de `generatedKey` OMITIDA sem registro (crítica); supressão D-S9 INCORRETA (crítica); preparedAlg/WRAPPED_KEY limitações registradas; randomized/preparedIV/preparedGCM/macced fiéis |
| G9 | **FAIL** | todo `@fail` = `unknown`; espúrio junto a erro específico; cascata pós-reset; acusação deslocada; dedupe colide cláusulas; sem campo de conjunto |

### GCMParameterSpecSpec — **REPROVADA** (no escopo do piloto)

| Gate | Resultado | Fundamento |
|---|---|---|
| G2 | PASS | geração limpa e trivial (0,41+0,91 s, ~87 MB) |
| G3 | PASS | dupla inclusão confirmada (produto de Alfa + H-GCM confirmada no artefato); a colisão c1/c2 é DIVERGÊNCIA_EQUIVALENTE_COMPROVADA **desta spec** (o fail-open do gerador fica registrado em G-toolchain) |
| G4 | **FAIL** | tLen: valores fiéis, mecânica INCORRETA (supressão em vez de report) — crítica |
| G5 | PASS | 2/2 construtores, DISJOINT, vizinhos livres, dois harnesses (BETA-GCM-03) |
| G7 | **FAIL** | `randomized[src]` suprimido (INCORRETA, crítica); ENSURES `preparedGCM` fiel |
| G9 | **FAIL** | `@fail` inalcançável (código morto); spec sem canal próprio; causa-raiz indistinguível no leitor deslocado |

Nota sobre Alfa ter dito "INCONCLUSIVA" para o GCM: a condição (i) de Alfa (H-GCM) foi
resolvida — restam defeitos **demonstrados** críticos, logo REPROVADA, não INCONCLUSIVA.
Ambos os vereditos valem **no escopo coberto**; G6/G8/G10 podem apenas adicionar defeitos,
não remover os demonstrados.

## 6. Validação do protocolo pelo piloto

**O piloto validou o protocolo no essencial**: o esquema de claims único funcionou; a
separação de papéis produziu convergência independente real (3 rotas na supressão do GCM,
2 gerações idênticas de artefato); o pré-registro §3/§4 decidiu os dois conflitos de
classificação sem arbitrariedade; o modelo semântico §5 (distinções de não-ocorrência) foi
usado corretamente pelos três. Custo: razoável (geração de 23 specs em 28 s comprova
viabilidade da rodada completa).

Ajustes recomendados para a rodada das 23 — **sem mudar gates**:

1. **Autômato efetivo como insumo comum de rodada** (maior ganho): Alfa gastou os claims de
   linguagem condicionais à extração que Beta fez de qualquer forma. Padronizar: Beta extrai
   e publica as tabelas efetivas por spec ANTES do parecer de Alfa (ou Alfa recebe o
   artefato); o walk contraexemplo-sobre-artefato vira teste padrão do juiz (script único).
2. **Resolver a precedência do ORDER uma vez** contra o Xtext oficial do CrySL e registrar
   a leitura adotada — hoje cada spec com `,`/`|` aninhados carrega a mesma INCONCLUSIVE
   (ALFA-CIP-04) sem necessidade.
3. **Padronizar dois testes hoje ausentes**: (a) folding×JCA (resolução case-insensitive de
   `getInstance` — fecha ALFA-CIP-14b e homólogos); (b) semântica de `part()` sobre
   componente ausente (fecha o resíduo de 14a). Ambos são executáveis em harness JVM sem
   emulador.
4. **Completar o harness de captura para construtores**: `api_members.py:94-97` pula ctors
   por construção; Beta escreveu `PointcutBudgetCtor.java` à mão. Incorporar a variante ao
   harness padrão (muitas das 23 specs são de classes `*Spec` cujo único evento é ctor).
5. **Fontes que faltaram aos agentes**: `data/gh101/predicate_omissions.csv` não cobre a
   2ª casa de `generatedKey` nem c2/c3 do Cipher — a rodada deve tratar "procurei registro e
   não achei" como passo obrigatório com localização exata pesquisada; e o board deve saber
   que a ressalva "sem fallback silencioso" da fase 0 era falsa para o caminho estático
   (GAMA-SET-01) — corrigir a leitura do manifesto na rodada.
6. **Higiene do denominador**: claims do mesmo fenômeno em agentes distintos devem citar um
   ID de fenômeno comum (ex.: `FEN-GCM-SUPRESSAO`) para o juiz reportar score por claim E
   contagem por fenômeno, evitando leitura inflada da convergência.

**Desvios a registrar** (proponho o texto; não escrevo em `fase0/desvios.md`):

> **D-piloto-1 (proposto)**: "A rodada das 23 adota como leitura normativa do ORDER a
> precedência do CrySL oficial (vírgula mais externa), após verificação única contra a
> gramática Xtext upstream; a gramática do MetaCrySL (`ConcreteSyntax.rsc:59-70`) fica
> registrada como divergente. Data, responsável, e evidência da verificação anexas."

> **D-piloto-2 (proposto)**: "Acrescentam-se dois testes padronizados por spec (folding×JCA
> e `part()` sobre componente ausente), executáveis em harness JVM. Não alteram critérios de
> decisão nem gates; convertem INCONCLUSIVEs recorrentes em resoluções."

> **D-piloto-3 (proposto)**: "O parecer de linguagem passa a ser emitido sobre o autômato
> efetivo extraído do artefato gerado (dimensão 1 do modelo semântico), com a sintaxe `.mop`
> usada apenas como hipótese inicial. Não muda o critério — explicita a fonte de evidência
> que o modelo semântico §6.1 já exigia."

## 7. Arquivos

- Este documento: `pilot/juiz_sintese.md`.
- Resolução claim a claim: `pilot/juiz_claims_resolvidos.csv` (72 claims).
- Brutos consultados: `pilot/alfa_*`, `pilot/beta_*`, `pilot/gama_*`; scratch
  `{alfa,beta,gama}/` (artefatos gerados, saídas de harness, scripts).

## 8. Decisão final pós-refutação

2026-08-09. Emitida após resposta a cada uma das 13 objeções do revisor independente
(`pilot/juiz_respostas_refutacao.md`), como exige o protocolo §15. As seções 1–6 acima
são a primeira síntese (rev. 1) e permanecem como registro; onde os números divergirem,
**esta seção prevalece** — a base é a rev. 2 de `juiz_claims_resolvidos.csv`.

### 8.1 Vereditos finais por spec

Inalterados pela refutação — nenhuma objeção alcançou os vereditos, por conclusão do
próprio revisor (`refutacao_parecer.md:252-257`), que re-executou os FAILs estruturantes.

- **CipherSpec — REPROVADA** no escopo coberto. Gates: G2 PASS, G3 FAIL, G4 FAIL,
  G5 PASS, G7 FAIL, G9 FAIL (fundamentos na §5).
- **GCMParameterSpecSpec — REPROVADA** no escopo coberto. Gates: G2 PASS, G3 PASS,
  G4 FAIL, G5 PASS, G7 FAIL, G9 FAIL (fundamentos na §5).

Escopo dos vereditos: G6 (weaving ponta a ponta), G8 (diferenciais/mutação) e G10
(execução Android) não foram executados no piloto e só podem **adicionar** defeitos,
nunca remover os demonstrados. `INCONCLUSIVE` não vira aprovação: os 8 claims
inconclusivos ficam abertos como pendências nomeadas no CSV.

### 8.2 Score descritivo re-somado (CSV rev. 2)

Re-soma mecânica com os pesos pré-registrados (`fase0/pre_registro.md` §6), reproduzível
por `python3 pilot/juiz_rescore.py`:

| Dimensão | Peso | Resolvidos | PASS | FAIL | INCONCLUSIVE (fora) | Subscore |
|---|---|---|---|---|---|---|
| Linguagem formal | 20 | 7 | 4 | 3 | 1 | 11,43 |
| Captura de eventos | 20 | 5 | 5 | 0 | 0 | 20,00 |
| Bindings/cláusulas | 15 | 9 | 2 | 7 | 1 | 3,33 |
| Predicados/composição | 15 | 13 | 8 | 5 | 0 | 9,23 |
| Toolchain Android | 15 | 14 | 8 | 6 | 2 | 8,57 |
| Diagnóstico | 10 | 12 | 1 | 11 | 2 | 0,83 |
| Reprodutibilidade | 5 | 4 | 2 | 2 | 2 | 2,50 |
| **Total** | 100 | **64** | 30 | 34 | **8** | **55,90** |

Rótulos obrigatórios: score **descritivo e INCOMPLETO** (8 INCONCLUSIVE fora do
denominador) ≠ probabilidade de correção ≠ veredito; não arredondado; **não abre gate**.

Duas ressalvas da refutação, declaradas com o número (REF-06, aceita parcialmente):

1. A atribuição claim→dimensão não foi pré-registrada e não é re-feita ex post —
   trocar a regra depois de ver o resultado seria o vício que o pré-registro proíbe.
   A regra vira o desvio **D-piloto-4** (`fase0/desvios.md`), a fixar antes da rodada
   das 23.
2. 12 claims `*-SET-*` são do conjunto/pipeline, não das 2 specs, e 8 deles estão no
   denominador de um score apresentado como "do piloto". Sensibilidade **medida** (não
   estimada): excluindo os 12, o total seria **59,83** (+3,93) — acima do "±≈2" estimado
   na resposta REF-06, e é o número medido que fica valendo. Nenhuma das duas leituras
   abre gate.

Higiene registrada em 2026-08-09: três linhas do CSV rev. 2 tinham vírgula não escapada
dentro do campo `classificacao` (ALFA-CIP-18, GAMA-CIP-07, GAMA-SET-02) e foram
re-serializadas com aspas, sem mudança de conteúdo — necessário para a re-soma mecânica.

### 8.3 Mudanças da rev. 1 para a rev. 2 (tabela completa — REF-09)

| Claim | Mudança | Objeção | Efeito no score |
|---|---|---|---|
| ALFA-GCM-05 | PASS → INCONCLUSIVE (rótulo rev. 1 era autocontraditório; determinação exige harness não executado) | REF-02 | bindings: sai do denominador |
| BETA-SET-03 | PASS → INCONCLUSIVE (leitura não fecha claim de toolchain; metade DEX não verificada) | REF-03 | toolchain: sai do denominador |
| ALFA-CIP-14b | INCONCLUSIVE → FAIL (mesma regra de 14a sob o oráculo cru) | REF-04 | bindings: entra como FAIL |
| ALFA-CIP-15, ALFA-CIP-16 | severidade minor → major (sem registro deliberado; mitigação por API é inferida) | REF-05 | nenhum (severidade não pontua) |
| ALFA-CIP-17, ALFA-CIP-18 | evidência/classificação corrigidas: registro deliberado existe (`tasks.md:117`); FAIL e severidades mantidos — registrado ≠ aprovado | REF-01 | nenhum |
| GAMA-CIP-07 | resolução mantida INCONCLUSIVE; fundamento trocado pelo critério pré-registrado (argumento não executado rebaixado a hipótese) | REF-07 | nenhum |
| BETA-CIP-10 | PASS mantido; qualificador restaurado: ameaça A1 registrada e não adjudicada (FP condicional, pendência G10) | REF-08 | nenhum |
| BETA-CIP-04, BETA-GCM-03, BETA-SET-05 | PASS mantidos; pendência registrada: `android-36` do container não triangulado | REF-12 | nenhum |
| ALFA-GCM-01/02, BETA-GCM-02 | resoluções mantidas; retórica corrigida — identidade beta/gama é determinismo do gerador, não replicação independente | REF-11 | nenhum |
| (coluna `classificacao`) | normalizada aos seis estados da matriz normativa (`modelo_semantico.md:92-95`), com a convenção para claims de medição de toolchain | REF-13 | nenhum |

Efeito líquido no total: 58,0 (rev. 1) → **55,90** (rev. 2).

### 8.4 Lacunas e retificações declaradas

- **Dimensão 5 do modelo semântico** (equivalência paramétrica/ciclo de vida) **não
  produziu claims próprios no piloto** — lacuna estrutural que a primeira síntese não
  declarou (REF-08). A frase da §6 "o piloto validou o protocolo no essencial" fica
  retificada: o piloto validou o protocolo **nos aspectos que exercitou**; a dimensão 5
  e os gates G6/G8/G10 não foram exercitados. Claims da dimensão 5 são obrigatórios na
  rodada das 23.
- A ressalva da fase 0 "sem fallback silencioso" era **falsa para o caminho estático**
  (GAMA-SET-01: literal `jca` e probe sem API 30) — a leitura do manifesto deve ser
  corrigida na rodada.
- Mesa de captura validada contra `android-30` e `android-37.0` do host; o
  `android-36` do container Docker segue não triangulado (REF-12) — teste adotado
  para a rodada das 23.

### 8.5 Desvios do pré-registro

D-piloto-1 a D-piloto-4 formalizados em `fase0/desvios.md` (texto integral lá), a fixar
**antes** da abertura da rodada das 23. Os ajustes de processo 1–6 da §6 permanecem
recomendações de execução; nenhum altera critério de decisão ou gate.

**Decisão final**: piloto encerrado com **CipherSpec REPROVADA** e
**GCMParameterSpecSpec REPROVADA** no escopo coberto; protocolo validado nos aspectos
exercitados e segue para a rodada das 23 com os desvios D-piloto-1..4 e os ajustes da §6.
