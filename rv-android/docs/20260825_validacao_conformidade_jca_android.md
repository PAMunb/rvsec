# Validação rigorosa de conformidade — `jca_android` × CrySL (pós gh104/gh105)

**Data**: 2026-08-25 · **Estado auditado**: rvsec `HEAD = 14dd8093` (grupo 9.B da gh105 aplicado) · **Método**: seis auditorias independentes em paralelo — quatro por família de specs (cláusula a cláusula contra os dois oráculos), uma de integridade mecânica (contagens, gates, CLI de conformidade gh106, hash do oráculo, monitor gerado) e uma metodológica (validade científica, ameaças, go/no-go) — consolidadas com resolução de conflitos entre relatórios. Nenhuma análise de outro modelo foi consultada.

**Oráculos** (dupla ancoragem D-15, respeitada em toda a análise): cláusulas de **valor** contra as 49 regras CrySL validadas por especialistas (`RVSec-replication-package/tools/rules/`, sha256 `d7bcc019…` — **recomputado nesta auditoria e confere**); **ORDER/alfabeto/predicados** contra `MetaCrySL/generated/api30/`.

---

## 1. Veredicto executivo

**As specs `jca_android` estão aderentes aos oráculos declarados. Nota geral do conjunto: ≈ 9,2/10 nas specs; ≈ 7,5/10 na higiene dos registros; ≈ 9,0/10 no agregado.**

- **O teste ácido da re-ancoragem D-15 passa em todas as 24 specs**: MD5, SHA-1, HmacMD5, MD5withRSA, SHA1withRSA, AES/ECB, DES, DESede, RC4/ARC4, Blowfish e ChaCha20 são **acusados**; TLS, AndroidKeyStore, X509 e SHA256WITHRSA ficam em silêncio pelos mecanismos registrados (platform-value, alias, case-fold). Verificado em três instrumentos independentes: o texto das specs, o monitor gerado de 25/08 (nenhum MD5/SHA-1/ECB em lista admitida) e a CLI de conformidade da gh106 (M4: **zero polaridades invertidas** nas 21 specs pareadas).
- **A mecânica de predicados da gh105 é uniforme e correta**: 38 leituras todas em corpo de evento (zero em `condition()`), três valores (VIOLATED ≠ NOT_OBSERVED com códigos distintos), `validateAbsent` com a semântica invertida certa (ausência satisfaz), escrita só no ponto de aceitação (staging), zero `ExecutionContext`, o único `negate` do conjunto traduz o único NEGATES real (`PBEKeySpec.cP`). O grafo fecha: 32 escritas + 38 leituras, todo read com produtor e todo write com leitor ou disposição registrada.
- **Nenhuma divergência de valor sem registro foi encontrada.** Os departures observados estão todos dentro do conjunto fechado admissível (platform-value citado, oracle-wart, spelling-variant, deferred-constant, divergência registrada).
- **Seis defeitos comportamentais residuais foram encontrados sem registro** (§4) — um deles com potencial de falso positivo de classe nova (splitter do `CipherSpec`); os demais contaminam categoria (ORDER espúrio junto do ALG correto) ou são falsos negativos herdados de baixa severidade.
- **A higiene dos registros é o eixo fraco**: ~20 claims desmentidos ou envelhecidos (§5), nenhum dos quais muda o que é acusado, mas vários dos quais fariam uma auditoria externa tropeçar — inclusive dois vermelhos de instrumento (`G-2a` sem allowlist para 4 eventos das tasks 9.3/9.9; `G-PRED` superseded ainda somado no `ok` global do `gh104_gates.py`).
- **Go/no-go do experimento: GO condicionado — bloqueadores operacionais, não científicos** (§8).

---

## 2. Notas por spec

Rubrica: D1 alfabeto de eventos (20%) · D2 ORDER/autômato (20%) · D3 valores vs expert (25%) · D4 predicados (25%) · D5 adaptação Android registrada (10%). Nota 0–10 ponderada.

| Spec | D1 | D2 | D3 | D4 | D5 | **Final** | Observação dominante |
|---|---|---|---|---|---|---|---|
| PBEParameterSpecSpec | 10 | 10 | 10 | 9,5 | 9,5 | **9,8** | nenhum defeito; c2 ganhou o acusador que nunca teve |
| SecretKeySpec (propagador) | 9,5 | 9,5 | n/a | 10 | 10 | **9,8** | desconflação randomized/preparedKeyMaterial exemplar |
| KeyPairGeneratorSpec | 10 | 9,5 | 9,5 | 9,5 | 10 | **9,7** | mensagem de envelope cita oráculo errado (api30) |
| SecretKeySpecSpec | 10 | 9 | 10 | 9,5 | 10 | **9,7** | caso-bandeira do D-15 corretamente executado |
| IvChainJunction | 10 | 9 | 10 | 10 | 9 | **9,7** | cadeia IV/GCM/randomized/!macced fechada ponta a ponta |
| KeyGeneratorSpec | 10 | 9 | 10 | 9 | 10 | **9,6** | citação de linha errada em 3 registros (crysl:52, não :60) |
| KeyPairSpec | 10 | 9,5 | 10 | 8,5 | 10 | **9,5** | privada-como-pública corrigido; justificativa de escrita em corpo desatualizada |
| SignatureSpec | 9,5 | 9 | 9,5 | 9,5 | 9 | **9,4** | verified-on-boolean corrigido; resíduo g2 registrado só em comentário |
| SSLContextSpec | 9,5 | 8,5 | 10 | 9,5 | 9 | **9,4** | getDefault agora acusa (FORB-00); repetição de engine aberta (7.1) |
| IvParameterSpec | 10 | 10 | 9 | 9 | 9 | **9,4** | gêmeos órfãos fundidos; "dois relatórios viram um" medido |
| PBEKeySpecSpec | 9,5 | 9,5 | 9,5 | 9,5 | 7 | **9,3** | único negate do conjunto, semântica certa; bloco :80-91 contradiz o código |
| CipherInputStreamSpec | 9 | 10 | 9 | 9 | 10 | **9,3** | parametrização 9.15; ere idêntico ao ORDER |
| GCMParameterSpecSpec | 10 | 9 | 9 | 9 | 9 | **9,2** | seed tinha zero relatórios possíveis; import List/Arrays faltante |
| MessageDigestSpec | 9 | 8,5 | 10 | 9 | 9 | **9,2** | reset deletado, g4 revivido; resíduo overload 2-args sem registro |
| SecureRandomSpec | 9,5 | 9 | 9,5 | 9 | 9 | **9,2** | hub do randomized com dois pontos de aceitação corretos |
| HMACParameterSpecSpec | 10 | 9 | 10 | 8,5 | 8 | **9,2** | fiel 1:1 à regra; inerte em Android (classe inexistente na api30) — declarado |
| DHGenParameterSpecSpec | 10 | 8,5 | 8,5 | 9,5 | 10 | **9,2** | constraint realizada como filtro: violação é silêncio, não acusação |
| RandomStringPassword (propagador) | 9 | 9 | n/a | 9,5 | 9 | **9,0** | ponte falsa deletada com medição; hoje sem função — permanência em aberto |
| TrustManagerFactorySpec | 9,5 | 8 | 10 | 9 | 7 | **9,0** | gtm1 ressuscitado (3 defeitos); registro prometido no comentário não existe |
| CipherOutputStreamSpec | 8 | 9 | 9 | 9 | 10 | **8,9** | `fl` fora do alfabeto da regra no grupo obrigatório (flush-only passa) |
| KeyStoreSpec | 9 | 8 | 9 | 9,5 | 8,5 | **8,9** | 4 platform-values citados; tipo rejeitado + load sem getKey = só ORDER |
| KeyManagerFactorySpec | 9 | 7,5 | 10 | 9 | 7,5 | **8,8** | espelho NÃO reparado da co-emissão ORDER+ALG (TMF/SSLContext foram) |
| MacSpec | 9 | 8 | 8,5 | 9 | 9 | **8,7** | sink do prefixo g3* (só-inseguro vira ORDER perpétuo); 2 variantes sem cobertura da regra de normalização |
| CipherSpec | 9 | 8 | 9 | 8 | 10 | **8,65** | splitter cru de generatedKey (B1); mistura de ramos em `end` |

**Médias**: simples **9,27** · ponderada por peso no corpus (Cipher, MessageDigest, Signature, Mac, SecureRandom, KeyGenerator, KeyStore, SSLContext, TMF, SecretKeySpecSpec ×2) **≈ 9,2**.

Por família: chaves **9,6** · Cipher/IV **9,2** · store/TLS/PBE **9,2** · digest/assinatura/MAC/random **9,1**.

---

## 3. Aderência CrySL → MOP: o que está coberto

**Tudo que está em CrySL está coberto por MOP? Não — por desenho, e todo o descoberto está registrado.** O denominador real do instrumento é:

- **Valores**: 38 de 80 cláusulas ativas (22 IGUAL + 14 NAO-DERIVADO + 2 MOP-MAIS-PERMISSIVO, que são spelling-variants do próprio congelado); **42 deferred-constants**, todas com linha citando o texto expert. O que fica de fora, por grupo: (i) toda a família de proteção de senha (`notHardCoded` ×3, `neverTypeOf` ×5) — parte **impossível em RV dinâmico** (exige análise de origem de dado); (ii) as janelas de buffer (`length ≥ off+len` etc., ~17 cláusulas); (iii) os acoplamentos `alg⇒mode`/`alg∧mode⇒pad` e keysizes do `Cipher`; (iv) o keysize AES do `KeyGenerator`. A decisão "no new accusation classes" é deliberada (classe nova = taxa de FP não medida no corpus) e preserva a comparabilidade com o `jca` publicado.
- **Predicados**: das 36 cláusulas do ledger, **21 fiadas** (produtor + consumidor + acusador + par de traces), **14 registradas** com medição (2 vacuous — #23, #30; 2 unreachable-composition — #17, #21, ambas verificadas nesta auditoria e sustentadas; 10 com ponta sem spec no conjunto), **1 unclosable** (`preparedEC` — nenhuma regra o garante).
- **ORDER**: fiel módulo 9 divergências mantidas de propósito e registradas no `gate_allowlist.csv`; G-ORDER verde (14 passed, 8 allow-listed, 2 skipped por declaração — junção e propagador, que não têm regra).

O construto honesto para o artigo é: **"as cláusulas que o `jca` publicado já checava, com os valores expert corretos, mais a fiação de predicados"** — não "as 49 regras expert".

---

## 4. Defeitos comportamentais residuais (sem registro) — B1–B6

Ordenados por severidade. Nenhum foi reparado nesta análise (escopo: apenas analisar).

- **B1 — `CipherSpec.mop:167`: splitter de `generatedKey` cru.** `alg(c.getAlgorithm())` chama a `CipherTransformationUtil.alg` congelada (case-sensitive, sem alias), enquanto os produtores gravam o algoritmo canônico e os demais usos do mesmo evento foram normalizados na 9.10. `Cipher.getInstance("aes/GCM/NoPadding")` (JCA resolve case-insensitively) forma `("aes")` vs `("AES")` → `validate` responde **VIOLATED** → `CIPHER-CONSTR-00` falso, que o envelope descreve como evidência positiva de misuse. O comentário da IvChainJunction (:144-151) chama a leitura crua de "segunda exposição do defeito" — esta terceira ficou. **Único achado com potencial de falso positivo de classe nova.**
- **B2 — família "guarda positiva no overload de 2 args" (co-emissão ORDER+ALG).** `KeyManagerFactorySpec` (g1/g2 + rota `g3→unsafeAlg` que rejeita o `init`), `TrustManagerFactorySpec.g2`, `MessageDigestSpec.g2/g3`, `SignatureSpec.g2`, `SecureRandomSpec.g2`: algoritmo inseguro pedido pelo overload com provider fica não observado e o evento seguinte emite o ALG correto **mais** um ORDER espúrio — exatamente o defeito que 3.2/3.6/9.17 removeram de TMF.g1 e SSLContext. Espelhos declarados respondem diferente ao mesmo misuse; contamina a categoria `InvalidSequenceOfMethodCalls` nos dois lados do pareamento.
- **B3 — `KeyStoreSpec`: constraint governa transição.** Tipo rejeitado (`g2`) faz o `load` cair em `@fail`; a acusação de tipo vive só em `gk1` — tipo inseguro carregado mas nunca lido = só `KEYSTORE-ORDER-00`, nunca `KSTYPE-00`.
- **B4 — falsos negativos herdados de ORDER.** `CipherSpec` :402-412: o estado `end` mistura os ramos `w+` e finals (aceita `wrap` após `doFinal` e vice-versa — mais permissivo que os dois oráculos). `CipherOutputStreamSpec`: caminho flush-only alcança `close` sem nenhum `write` (este está registrado, mas não reparado).
- **B5 — escritas de predicado em corpo executam mesmo em transição que falha** (`gtm1`/`gkm1`): sobre-aproximação do predicado em traces já não-conformes; baixa severidade (o trace já carrega ORDER).
- **B6 — `GCMParameterSpecSpec` usa `List`/`Arrays` sem importá-los** — compila por acidente do dedupe de imports do monitor mesclado; é a mesma classe de fragilidade que quebrou a 11.9 duas vezes. Fere a regra set-wide de disciplina de imports.

Recomendação (sem implementar): B1 merece adjudicação antes do experimento — ou linha de `divergence_record.csv` assumindo o FP possível, ou reparo pontual em change própria. B2–B6 podem virar linhas de registro/backlog; nenhum bloqueia a execução (B2 afeta as duas populações do pareamento igualmente).

---

## 5. Registros desmentidos ou envelhecidos — R1–R7

Nenhum muda o que é acusado; todos violam P4 ou atrasam a auditoria cruzada.

- **R1 — `data/jca_android/README.md` parado em 112 sites.** A realidade é **115/115** (bijeção verde no message gate): 112 → 114 (+`SECRETKEYSPEC-ALG-00/01`, 24/08) → 115 (+`SSLCONTEXT-FORB-00`, 9.9, 25/08). O mesmo README ainda declara vivos os "five purely predicate-guarded accusers" (todos fundidos/deletados pela gh105) e descreve `RandomStringPassword` como propagador com leitor (hoje não escreve nada e ninguém o consome).
- **R2 — `predicate_graph.csv` uma geração atrás** (23/08): três rows afirmam que `order_alphabet_map.csv` não mapeia arquivos que o mapa (completado pela 7.1 em 25/08) mapeia.
- **R3 — `constraint_table.csv` ancora `mop_line` no seed congelado** — correto para o G-CONF (que roda no seed), mas ambíguo para o leitor; no caso GCM (`crysl:19/:20 → mop:34 IGUAL`) descreve testes que o sucessor **deletou** (task 8.1), contradizendo o `conformance_record` do mesmo diretório; e as rows 92-93 do conformance ("no .mop of the frozen jca ever tested it") são factualmente falsas para os bounds do GCM (o seed os testava em `condition()`).
- **R4 — `divergence_record.csv`**: quatro rows do hunk de import da `ConscryptAliasTable` (91, 134, 210, 288) carregam reason copiado do KeyGeneratorSpec; rows 95/96 (KMF) ainda descrevem a lista pré-D-15 (`{PKIX}`, SunX509 narrowed); a row que `TrustManagerFactorySpec.mop:74-78` promete ("resíduo registrado no divergence_record") **não existe**.
- **R5 — comentários estale em 6+ specs**: "este arquivo é um dos treze ausentes do order_alphabet_map" (MacSpec :329-332, GCM, SecretKeySpec — o mapa já os mapeia); `PBEKeySpecSpec.mop:80-91` afirma que o read de `randomized[password]` "is kept unchanged" — contradito pelo próprio arquivo (:116-135) e pelo `codes.csv`; IvChainJunction :311 fala em "both symbols" para um alfabeto de sete; `KeyPairSpec` justifica escrita em corpo por um autômato que a 9.11 mudou; `PBEParameterSpecSpec` :12 intitula-se "GCMParameterSpec"; `KeyPairGeneratorSpec.mop:151` atribui a lista de keysizes ao oráculo errado ("api30" — a lista aplicada é a expert, com 3072); `conformance_record.csv:74` diz que o `__RESET` foi revertido (foi reimplementado na 9.2); citação `KeyGenerator.cryptsl:60` deveria ser `:52` em três registros.
- **R6 — gates com vermelho de instrumento**: `G-2a` reprova 4 eventos (`PBEKeySpecSpec.f1/f2`, `SSLContextSpec.getDefault`, `SecureRandomSpec.g4`) que são a mesma classe dos 8 já allow-listed mas não ganharam linha no `gate_allowlist.csv` quando as 9.3/9.9 aterrissaram; `G-PRED` (superseded para o sucessor) ainda soma no `ok` global do `gh104_gates.py` — **o CLI sai exit 1 sobre `jca_android` para sempre**, enquanto todos os gates gh105 e o pytest de parity (102 passed) estão verdes.
- **R7 — lacuna de cobertura**: a suíte de parity não asserta G-2a para `jca_android`, então o verde do pytest e o vermelho do CLI coexistem sem que nenhum teste o denuncie. Além disso, `gate_allowlist.csv` (lado `jca`) mantém a row G-FORB do `getDefault` dizendo que o sucessor "carrega a omissão idêntica até a 9.9 aterrissar" — a 9.9 aterrissou.

---

## 6. O que mudou, e por quê (categorias de alteração)

- **Por re-ancoragem de valores (D-15)**: listas restauradas ao expert (SecretKeySpecSpec é o caso-bandeira — a api30 não declara cláusula e a expert declara; SunX509 de volta em TMF/KMF; EC/DiffieHellman de volta no KPG; 3072 de volta no RSA); os 65 flags da alias table recomputados; `Api30CipherTransformationUtil` sem nenhum chamador (confirmado por grep).
- **Por Android (todas registradas)**: 5 platform-values fechados (`TLS`; `AndroidKeyStore/AndroidCAStore/BKS/BouncyCastle`) com citação primária; `SSL` deliberadamente acusado; normalização única via `ConscryptAliasTable` (175 = 175 registros do `OpenSSLProvider.java`, igualdade Java×CSV verificada linha a linha, zero mismatch); construtores `protected` no android-30 sem pointcut (CipherStreams); `HMACParameterSpec` inerte (classe fora da api30) — mantida com registro; `destroy()` de SecretKey sem caminho observável.
- **Por fiação de predicados (gh105)**: 27 leituras movidas de `condition()` para corpos; 17 órfãos absorvidos/fundidos; `IvChainJunction` criada para os argumentos que `CipherSpec` não pode ligar (teto de 17 eventos); store novo três-valorado, chave por identidade, API bound-first (motivada pelo `KeyManager[]` — verificada em uso); 8 `remove()` de `@fail` extintos, o nono virou o `negate` do PBEKeySpec; NOBS com códigos próprios (30 de 115).
- **Reparos pontuais (F4), todos confirmados contra o seed**: KeyPair privada-como-pública; Signature `sign()` com retorno errado (nunca teceu) e verified-on-boolean; TMF `gtm1` morto por três defeitos e propriedade errada (`GENERATED_KEY_MANAGERS`!); SSLContext `engine` com retorno `void`; GCM com dois eventos de mesmo nome e `ere` referindo evento inexistente (zero relatórios possíveis no seed); SecureRandom `next2` ausente do estado `end` (12.400 FPs no corpus congelado); MessageDigest `reset` acusador falso; parametrização dos CipherStreams e do KeyStore (monitor único de processo no seed).

---

## 7. Paralelo histórico — melhorou ou piorou?

| Eixo | (a) `jca` Java publicado | (b) `jca_android_bug_predicate` (arquivado) | (c) `jca_android` atual |
|---|---|---|---|
| Valores | expert corretos, mas 11 idiomas de comparação em 3 famílias (a mesma string era misuse numa spec e não noutra) | **invertidos** — MD5/SHA-1/ECB admitidos via âncora de provider; reprovado 22/22 | expert + normalização única auditável; aceitação bilateral medida (replay D-15) |
| Predicados | escritos e nunca lidos (17 órfãos, teto 56,1% do ISoMC); leituras em `condition()` fabricando ORDER falso; `remove()` em `@fail` sem semântica CrySL | herdou tudo e fiou sem instrumento | 21/36 fiados com par de traces; três valores; grafo fechado e gateado |
| Autômatos | acusadores fora do `ere` (all-fail rows, relatórios dobrados); specs mortas (Signature.sign, TMF.gtm1, GCM inteiro) | idem | órfãos absorvidos; specs mortas ressuscitadas; 112→115 sítios vivos = codes.csv bijetivo |
| Legibilidade | 72,93% `unknown`, envelopes autocontraditórios ("but found .") | idem | envelope v=1, código por sítio, ancoragem gateada |
| Custo novo | — | — | 42 deferências declaradas; semântica NOBS sem análogo anterior; 4 populações com 3 semânticas de `UnsafeAlgorithm` (comparações têm de nomear o oráculo); envelope de validade estreitado explicitamente a API 30/Conscrypt |

**Conclusão: melhorou em todos os eixos que importam.** O que se perdeu foi simplicidade de comparação entre campanhas — custo declarado e instrumentado, não escondido. O único estado inequivocamente pior é o intermediário (b), arquivado e não selecionável.

---

## 8. Ameaças à validade e go/no-go

| Ameaça | Sev. | Estado |
|---|---|---|
| Denominador real ≠ "49 regras expert" (42/80 deferidas; senha/buffers/acoplamentos fora) | Alta p/ a claim; nula p/ FP | registrada linha a linha; **declarar no artigo** |
| B1 (splitter cru do CipherSpec) — FP possível de classe nova | Média-alta | **sem registro — adjudicar antes do experimento** |
| Medição 8.4 da gh105 feita com harness pré-conserto 11.11 (subcontagem de deltas), sem re-execução registrada | Média | re-rodar (custa segundos) ou registrar ressalva |
| Gates leem texto/artefato possivelmente velho (3 ocorrências históricas) | Média | mitigado por INV-INS-124/code-anchor; falta checagem de frescor artefato-vs-`.mop` |
| Oráculo expert 2017–2022 sobre Android (CCM wart; upstream dropou CBC/PCBC; BC fora do oráculo; Conscrypt android11-release) | Média | pinado com justificativa; **declarar envelope: API 30/Conscrypt** |
| B2 (co-emissão ORDER+ALG nos overloads 2-args) contaminando a categoria ORDER | Média | simétrico nos dois lados do pareamento; registrar |
| 4 populações × 3 semânticas de `UnsafeAlgorithm` | Média | regra de leitura existe (README/CONTEXTO); risco é de escrita |
| Junção nunca disparou dinamicamente em device; memória em escala | Média | prova estrutural existe; P6 é a observação |
| Vermelhos de instrumento (G-2a/G-PRED no CLI) desalinhados do pytest verde | Baixa-média | R6/R7 — atualizar allowlist e escopo do G-PRED |
| Ruído dexlib2 (double-fire) inflando ISoMC | Baixa | medido, pareado nos dois lados |

**GO condicionado.** Não há bloqueador científico. Condições operacionais antes de subir a campanha `experimento-gh104`:
1. **Rebuild do reator + reinstalação** — P1 reenvelheceu: `KeyPairSpec.mop` de 25/08 16:20 é mais novo que `rvsec-core.jar` (15:51) e `instr-cli.jar` (24/08).
2. **Imagem Docker `0.9.3-gh104`** (push + rebuild — B3/P5).
3. **Decisão do F3** (colisão de nome dos dois `gh104_gates.py`).
4. **As 4 linhas G-2a no `gate_allowlist.csv`** e a decisão sobre o escopo do G-PRED no CLI (hoje o CLI reprova o conjunto por construção).
5. **Adjudicar B1** (registro ou reparo em change própria).
6. Recomendado: re-rodar a 8.4 sob o harness pós-11.11; tratar o **P6 como go/no-go decisivo** — é também o primeiro contato do conjunto pós-9.B com um dispositivo.

---

## Apêndice: verificações mecânicas (25/08)

Contagens: 24 `.mop` + `codes.csv` ✓ · 115 sites, todos 4-arg, 0 comentados, bijeção 115=115 com ancoragem verde ✓ · `ExecutionContext` 0, `validate(` 38, `setProperty(` 0, `.remove(` 0 ✓ · seed `jca/` byte-idêntico a `7e7acb69` ✓ · `jca_android_bug_predicate/` = 23 arquivos idênticos ao pré-rename `a3e6a165` ✓ · alias table 175=175 Java×CSV, 67 yes/108 no ✓ · constraint_table 80 linhas, 42/22/14/2 ✓ · sha256 do oráculo expert recomputado = `d7bcc019…` ✓.

Gates: G-LINT 🟢 · G-MSG (+code-anchor) 🟢 · G-ORDER 🟢 (14/0/8/2) · G-SIG/G-FORB/G-BIND 🟢 (141/6/136 checados, 0 falhas) · G-PARAM 🟢 (24/24) · grafo de predicados 🟢 (70 sites, 0 failing) · pytest parity do escopo 🟢 (102 passed) · `gh104_gates.py` CLI 🔴 **só** por G-2a (4, R6) e G-PRED (23, por construção — superseded).

CLI gh106 (oráculo mecânico independente, upstream `CrySL-Rules@f2f4d3b`): 24 lifted, 22 pareadas, M0 recusa os 2 propagadores (por design), M2 11 EQUIVALENT / 3 MOP_MORE_PERMISSIVE / 4 MOP_MORE_RESTRICTIVE / 3 INCOMPARABLE (contra upstream, não contradiz G-ORDER que responde à api30), **M4: 0 polaridades invertidas**.

Fora do escopo do conjunto (registrado de passagem): 4 testes de parity vermelhos por ambiente/artefato lateral — baseline do gator mais velho que o jar, tokens `reachesMop` em `modules/aperv-tool/`, `ANDROID_SDK_HOME` ausente (2 testes).
