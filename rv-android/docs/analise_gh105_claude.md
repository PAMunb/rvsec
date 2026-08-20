# Verificação rigorosa da change `gh105-predicate-wiring`

**Data**: 2026-08-20 · **Modelo**: claude (Opus 5, 1M context) ·
**HEAD verificado**: `bd61abea` em ambas as árvores (`rvsec` e `rv-android` — mesmo repositório,
`git rev-parse --show-toplevel` idêntico), o ponto de medição esperado. Nada se moveu.

**Ferramentas**: nove workstreams paralelos (subagentes), um por dimensão D1–D8 com D2 dividido em
D2a (semântica do oráculo + razão das 35 cláusulas) e D2b (spot-checks fim-a-fim + `ORDER`), mais
uma linha de medição própria do orquestrador usada para conferir os subagentes em vez de aceitá-los.
O MCP `sequential-thinking` não foi usado; a decomposição em nove workstreams independentes cumpriu
o mesmo papel. Toda escrita fora deste arquivo foi para um diretório de scratch próprio.

**Método**: todo número foi **re-derivado da fonte** com parsers escritos para esta verificação,
nunca copiado do plano. Onde dois workstreams divergiram, o orquestrador arbitrou medindo de novo
(dois casos, ambos registrados abaixo). Onde um subagente afirmou algo de alto impacto, o
orquestrador leu o arquivo citado antes de aceitar (onze verificações diretas).

**O que não pôde ser executado, e por quê**
- **Nenhum emulador** foi iniciado, parado ou tocado, em nenhum contexto (regra permanente).
- **Nenhum weave real** (`ajc`/dexlib2): não há jar do AspectJ na árvore. Consequência concreta:
  a contradição do delta entre `spec.md:157` ("`Object` … including autoboxed primitives") e
  `spec.md:399` ("`Object+` rejects primitives") fica **NÃO VERIFICÁVEL AQUI** — um único `ajc`
  contra `SecureRandom.setSeed(long)` a resolve.
- **`equals` de `OpenSSLRSAPublicKey`/`BCRSAPublicKey`** (R4): exige dispositivo. NÃO VERIFICÁVEL AQUI.
- **O reator não foi buildado** (não era necessário: os binários `target/release` de javamop e
  rv-monitor existiam e foram usados). O gerador foi executado apenas em scratch, para a matriz de
  colapso de parâmetros e para o idioma do splitter.
- Os números do gerador (17 eventos sob `-Xmx1g` ≈ 53 s; 18 ⇒ `StackOverflowError` em
  `EnableSet.parseSets`) foram **lidos da evidência de `audit/.../agentC/`**, não re-medidos.

---

## 1. Veredito executivo

**BLOQUEADOR de fato físico: `CipherSpec.mop` já tem exatamente 17 eventos — o teto do gerador.**
A task 5.4 manda reconstruir o bloco `REQUIRES` do `Cipher` a partir das seis cláusulas da regra, e
as cláusulas 7/9/10 exigem `param`/`params` ligados, que o `i2` fundido
(`call(public void Cipher.init(int, Key,..))`) não liga. Pela regra de fusão do **próprio** delta
(`spec.md:385-403`), separar por perfil de ligação custa ≥1 evento no melhor caso e ~6 na leitura
literal: n ≥ 18 ⇒ `StackOverflowError` em `EnableSet.parseSets`, sem monitor, **com exit 0**.
Nenhum artefato declara que a folga é zero.

**A change não é segura para implementar como está.** Dez achados de severidade BLOCKER, todos com
evidência file:line, e nenhum deles exige rediscutir o desenho: são famílias semânticas do oráculo
que os artefatos nunca nomeiam, mais três caminhos de congelamento deixados abertos.

O núcleo técnico **resiste inteiro**: a supressão de transição pelo guarda está no monitor gerado
(`:3715-3717` antes do `handleEvent` em `:3725`); identidade-versus-`equals`, aridade e o modelo
híbrido de INV-INS-131 são análogos fiéis do oráculo; o colapso de parâmetro primitivo foi
reproduzido e é exatamente como descrito (e **só** atinge arrays primitivos — arrays de referência
sobrevivem); as quatro regras de junção seguem de falhas medidas no piloto; o splitter "pelo
chamador" foi validado fim-a-fim; `Order` é regular e a alegação de equivalência por AFD é sólida.
A espinha aritmética também resiste: censo do oráculo, censo de sítios, a decomposição 134 =
23+27+49+9+25+1, os órfãos 17/9 e 18/10 — tudo re-derivado, vários à unidade.

Os defeitos estão concentrados em **`tasks.md`**, que lê como se tivesse sido escrito sem re-derivar
das fontes: o Grupo 3 nomeia quatro specs sem nenhum órfão e deixa 6 dos 17 sem dono; o Grupo 5
nomeia predicados que o oráculo não exige e omite nove cláusulas que exige. E o número-manchete da
change — 49.817 = 70,4 % — é a população de órfãos do **`jca` congelado**, não do `jca_android`.

---

## 2. Tabela de achados

Ordem: severidade decrescente. `[Dn]` indica o workstream; `[✓]` marca o que o orquestrador
verificou lendo a fonte, além do subagente.

### BLOCKER

| id | dim | veredito | alegação verificada | evidência | emenda recomendada |
|---|---|---|---|---|---|
| **B-1** | D5/D2b | **REFUTADO** | As tasks 5.4/5.5 cabem no teto do gerador | `CipherSpec.mop` = **17 eventos** (`g1,g2,g3,i1,i2,u1..u5,wkb1,f1,f2,f3,f5,f6,f7`) `[✓]`; teto = 18 ⇒ `StackOverflowError`, sem flag que levante. Cláusulas 7/9/10 precisam de `param`/`params`, não ligados pelo `i2` fundido (`CipherSpec.mop:78-80`) | Declarar a folga zero em INV-INS-145; **rotear** `randomized[ranGen]`, `preparedAlg[param]` e `prepared*[params]` para specs de junção (custo 0 no alfabeto do `CipherSpec`) e dizê-lo na task 5.4 |
| **B-2** | D2a/D2b/D7 | **REFUTADO** | O contrato de leitura cobre toda cláusula `REQUIRES` | **8 de 36** cláusulas são implicações guardadas (`Cipher:182,184`; `KeyPairGenerator`×4; `AlgorithmParameters`×2) `[✓]`. `grep` por `conditional`/`=>`/`CONSTRAINTS` nos quatro artefatos: nada sobre isto. INV-INS-133 reserva `condition(...)` para overload/`ORDER`, logo o guarda da cláusula não tem casa declarada | Fiar incondicionalmente acusa **todo** `Cipher.init` em ECB/GCM de IV ausente. Acrescentar a INV-INS-133: o guarda da cláusula é avaliado no corpo, antes da leitura, e vai para uma coluna `guard` do `predicate_graph.csv` |
| **B-3** | D2a/D2b/D7 | **REFUTADO** | O veredito trivalente cobre toda `REQUIRES` | **3 cláusulas negadas**: `Cipher.cryptsl:180 !macced[_,plainText]`, `Mac.cryptsl:82,84 !encrypted[…]` `[✓]`. `validate` não tem polaridade (`design.md:199`); "negated" só aparece nos artefatos a respeito do `defsuses` | A polaridade **inverte** a regra D-4: para `!macced`, "sem entrada" é o caso **conforme**, não artefato de alcance. Literal, INV-INS-133 emite *not observed* em todo `Mac.doFinal()` conforme. Definir `validateNegated` (ou a polaridade como parâmetro) e a tabela trivalente invertida |
| **B-4** | D5/D7/D2b | **REFUTADO** | F1 (absorver órfão) e F2 (mover leitura) são independentes | **8 órfãos são gêmeos discriminados só pelo predicado**, com pointcut idêntico ao irmão conforme: `IvParameterSpec c3,c4` · `SecureRandomSpec c3,setSeed3` · `SecretKeySpecSpec c3,c4` · `PBEParameterSpecSpec c3` · `PBEKeySpecSpec err2,err3` `[✓]` (ex.: `IvParameterSpec.mop:42-50` vs `:21-28`) | Executados literalmente, produzem uma chamada com **duas transições** — o defeito que o próprio delta define em `spec.md:404-409`. O reparo correto é **fundir** (apagar o gêmeo, dobrar a acusação no corpo do irmão), não "absorver". Trocar o verbo no Grupo 3 e nomear os casos |
| **B-5** | D5 | **REFUTADO** | `ensure/validate(Property, Object...)` carrega toda forma de chamada | Medido `[✓]`: passar `String[]{"km0","km1"}` a `f(P, Object...)` dá `args.length=2, args[0]=km0` — o **objeto ligado vira o primeiro elemento**; array vazio dá `args.length=0`, violando a pré-condição `args.length ≥ 1` do próprio desenho. Só *warning*, compila. Vivo em `KeyManagerFactorySpec.mop:72-75`, `TrustManagerFactorySpec.mop:74-77`; `SSLContext.cryptsl:7-9` liga `KeyManager[] kms`/`TrustManager[] tms` — exatamente a task 5.6 | Assinar `ensure(Property p, Object bound, Object... values)` (idem `validate`). Sem isto a cadeia TLS inteira liga o objeto errado, em silêncio |
| **B-6** | D8 | **REFUTADO** | A task 6.1 repara a conflação `preparedKeyMaterial ≡ RANDOMIZED` | 6.1 nomeia só a metade **produtora** (`SecretKeySpec.mop:26`) `[✓]`. A metade consumidora é `SecretKeySpecSpec.mop:25,42` (`validate(RANDOMIZED, keyMaterial)`), e **`SecretKeySpecSpec` não aparece em nenhum dos quatro artefatos** `[✓]` | Renomear só a escrita deixa a leitura sem produtor: depois de F2, `c1`/`c3` acusam **todo** `new SecretKeySpec(...)` conforme. É o aprendizado 3 dentro da própria lista de tasks. Task 6.1 tem de tocar os dois arquivos no mesmo commit |
| **B-7** | D7/D2a/D2b | **REFUTADO** | A task 4.3 "dá acusador" às leituras sem acusador como reparo | 5 das leituras não traduzem cláusula alguma `[✓]`: `Mac.cryptsl` exige `preparedHMAC` e `!encrypted`×2 — **nenhum `generatedKey`** (`MacSpec.mop:58,70`); `SecretKey.cryptsl` **não tem seção `REQUIRES`** (`SecretKeySpec.mop:25`); `RandomStringPassword.mop:11-21` não tem regra e propaga taint sobre `String.valueOf(Object)`/`toCharArray()` | Armá-las **fabrica** uma classe de misuse — precisamente o que o `gate_allowlist.csv` da gh104 recusou para `err2`/`c3`. A task 4.3 tem de separar "leitura que traduz cláusula" (ganha acusador) de "leitura de propagação" (perde a leitura ou vira junção) |
| **B-8** | D6 | **INCONSISTENTE** | "REMOVED Requirements: (none)" é compatível com apagar as sobrecargas depreciadas | `spec.md:623-626` sanciona apagar "the deprecated store overloads"; `ExecutionContext.remove(Property)` tem **4 chamadores no `jca` congelado** `[✓]`: `MacSpec.mop:87`, `KeyManagerFactorySpec.mop:91`, `TrustManagerFactorySpec.mop:87,88`. Contradiz INV-INS-132 no mesmo documento; nenhum gate cobre, e o ajc roda com `-proceedOnError` e stderr suprimido | Reescrever `spec.md:624-626`: as sobrecargas depreciadas **não** são apagadas; INV-INS-131 governa apenas o que a **nova** store oferece |
| **B-9** | D6/D2b | **INCOMPLETO** | "Every other class the frozen set calls is untouched" (INV-INS-132) | `Property.java` é importado por **23/23** `.mop` congelados `[✓]`. Fiar as cláusulas 7, 18, 19, 32 exige `PREPARED_ALG`, `PREPARED_RSA`, `PREPARED_DSA`, `PREPARED_KEY_MATERIAL` — **ausentes** do enum de 25 valores `[✓]`. Nenhum dos quatro artefatos menciona `Property`. E INV-INS-132 **não tem teste**: `FROZEN_PATHS` = (`jca/`, `CipherTransformationUtil.java`) `[✓]` — nem `ExecutionContext.java` nem `Property.java` | É a forma exata do aprendizado 5 (`233df18a`). Acrescentar a INV-INS-132: valores de `Property` **podem ser acrescentados**, nunca removidos/renomeados/reordenados (seguro: nenhum `ordinal()`/`values()` na árvore `[✓]`), e pôr os dois arquivos em `FROZEN_PATHS` com essa ressalva |
| **B-10** | D4 | **REFUTADO** | INV-INS-141 resolve a colisão com a gh104 e nada é removido | A gh104 **ADICIONA** a requirement `The Successor Set Carries the Predicates of Its Seed Unchanged` (`gh104 spec.md:197`) `[✓]`, cujos cenários dizem "the count per file MUST equal the frozen file's count, **summing to 134 over the 23 files**" (`:212`) e "**neither file MUST receive a report site**" para `RandomStringPassword.mop`/`SecretKeySpec.mop` (`:220`). As tasks 4.1/4.3 falsificam ambos. gh105 declara `REMOVED Requirements: (none)` | INV-INS-141 supersede o **invariante**, não a **requirement**. Quando as duas changes arquivarem, o spec principal carrega uma requirement que a implementação viola. Acrescentar entrada `## MODIFIED`(ou `## REMOVED`) para essa requirement no delta da gh105 |

### MAJOR

| id | dim | veredito | alegação verificada | evidência | emenda recomendada |
|---|---|---|---|---|---|
| **M-1** | D1 | **REFUTADO** | "os 17 acusadores órfãos sustentam 49.817 = 70,4 % da categoria" (proposal:10, spec:20, design:15,162; D-8 "measured 70.4 % payoff") | Re-derivado `[✓]`: ISoMC = 70.760 de 97.018. **49.817 = 70,40 % é a soma das 10 specs com órfãos no `jca` congelado** — inclui `MessageDigestSpec` (10.135), cujo órfão `reset` a gh104 já absorveu. O `jca_android` tem 17 órfãos em 9 specs = **39.682 = 56,08 %** | Trocar por 39.682 / 56,08 % em todos os quatro artefatos, e como **teto**, não causa (`docs/20260807_handoff_gh101_sessao3.md:169-176` proíbe explicitamente a leitura causal) |
| **M-2** | todos | **REFUTADO** | As tasks 3.1-3.5 cobrem os 17 órfãos | Censo próprio, reproduzido por 4 workstreams `[✓]`: `IvParameterSpec{c3,c4}`, `KeyPairGeneratorSpec{initError}`, `PBEKeySpecSpec{f1,f2,err1,err2,err3}`, `PBEParameterSpecSpec{c3}`, `SSLContextSpec{unsafe_protocol}`, `SecretKeySpecSpec{c3,c4}`, `SecureRandomSpec{c3,g4,setSeed3}`, `SignatureSpec{g3}`, `TrustManagerFactorySpec{g3}`. As tasks nomeiam `KeyStoreSpec`, `KeyManagerFactorySpec`, `MessageDigestSpec`, `MacSpec` — **zero órfãos nos quatro** `[✓]`; **6 órfãos ficam sem task** | Reescrever 3.1-3.5 a partir do censo. A task 3.6 ("G-ACC verde, zero órfãos") é inalcançável executando 3.1-3.5 |
| **M-3** | D1/D2a/D7 | **INCOMPLETO** | "as 35 cláusulas conectáveis são fiadas ou registradas" | Censo definitivo do orquestrador `[✓]`: das 36, **25 são fiáveis** (as duas pontas com `.mop`), 5 sem consumidor, 3 sem produtor no set, 2 sem nenhuma ponta, 1 não-conectável (`preparedEC`). O `unclosable` do delta (`:262`, `:305-311`) cobre **só** o caso do produtor ausente | O critério de saída da task 5.7 e o cenário `spec.md:519-525` são inalcançáveis. Definir uma segunda categoria de registro ("a regra consumidora não tem especificação no set") e trocar o alvo 35 → 25 fiadas + 10 registradas |
| **M-4** | D2a/D2b | **REFUTADO** | O §5 do `tasks.md` nomeia as cadeias do oráculo | `preparedPBE` (5.5) e `generatedSSLContext` (5.6) são **só ENSURES** — nenhuma regra os exige `[✓]`. `preparedAlg` (2 cláusulas, uma delas a do `Cipher` que 5.5 diz fechar), `macced`, `encrypted`, `preparedRSA`, `preparedDSA`, `generatedCertPathParameters` **não aparecem em nenhum dos quatro artefatos** `[✓]`. 5.3 diz "KeyPairGen" onde a regra é `KeyGenerator`; 5.4 lista `Mac.init`/`Signature` como consumidores de `generatedKey`, que não o exigem; 5.5 lista `preparedHMAC` (é do `Mac`) e `preparedDH` (é de `AlgorithmParameters`/`KeyPairGenerator`) como fechadores do `Cipher` | Reconstruir o §5 a partir da tabela de 36 cláusulas (§5 deste relatório) |
| **M-5** | D3/D8 | **INCOMPLETO** | As 2 requirements MODIFIED copiam o spec principal fielmente | O cenário `#### Scenario: A predicate's whole set is deleted` (principal `:1857-1861`) foi **descartado** `[✓]`, junto de `:1830` ("Nothing links the constant written…"), da enumeração "runs in all three directions" (`:1832`), do exemplo `lSeed` (`:1834`) e do argumento inerte-versus-converso (`:1836`) | É a armadilha documentada do OpenSpec: MODIFIED parcial **perde o detalhe no arquivamento**. O cenário descartado ainda descreve comportamento vivo do `jca` congelado (a sobrecarga de 1 argumento, 4 chamadores). Restaurar os cinco trechos |
| **M-6** | D3/D4 | **REFUTADO** | "Invariants INV-INS-111, 119, 123 and 128 are restated" (`proposal.md:32`) | `grep -rn` na change inteira `[✓]`: INV-INS-119 e INV-INS-123 aparecem **apenas nessa frase**; 111 é citado uma vez (`spec.md:165`); 128 é supersedido, não reafirmado | Ou reafirmar as quatro no delta, ou corrigir a frase. INV-INS-123 importa: ele e o cenário `gh104:413` ainda dizem que o `jca_android` "encodes no `REQUIRES` by construction" — a gh105 falsifica isso |
| **M-7** | D4 | **INCOMPLETO** | A lista de colaterais do G-PRED está completa | Os três sítios nomeados existem e as linhas batem (`accept_requires:1189-1191`, wiring `1454-1468` exatos; `PREDICATE_CALL` é `:516-518`, não `:514-517`) `[✓]`. **Faltam**: `gh104_message_gate.py::_clause_family:152-160` (perde a classificação `REQUIRES` em silêncio quando as leituras vão para o corpo) e `experimento-gh104/scripts/preflight.py:158-178` — **um segundo gate também chamado "G-PRED", de polaridade oposta**, no próprio experimento a que a gh105 adia a validação conjunta. E `data/jca_android/gate_allowlist.csv` tem 3 linhas que ficam falsas, sem nenhuma task | Acrescentar os três à task 2.5 |
| **M-8** | D3/D5/D7 | **INCOMPLETO** | O censo de 134 linhas tem destino integral | As **25 chamadas de accepting-state** (19 `set`/6 `unset`) não têm task alguma `[✓]` — não são leituras (G4), nem escritas (G5), nem remoções (6.4); só o gate de import as expulsa implicitamente. Idem 22 dos 35 sites written-never-read; `ENCRYPTED` (11 sites, a maior família) não aparece em nenhum artefato | Uma task explícita por balde do censo |
| **M-9** | D5/D2a | **INCOMPLETO** | O `validate` trivalente compõe com as leituras existentes | 8 dos blocos de condição são **compostos** `[✓]`: `CipherSpec.mop:82-86` é uma disjunção tripla; `PBEKeySpecSpec.mop:38-41` conjunção sobre **dois objetos diferentes**; 6 misturam a leitura com CONSTRAINTS (`validLengths.contains(tagLen)`, `iterationCount >= 10000`, `keyMaterial.length >= offset + len`) | "Toda leitura carrega seu acusador" aplicado por sítio emite **3 relatórios** num só `Cipher.init` onde hoje a disjunção silencia os três. Definir a composição (`PredicateVerdict` não tem `&&`/`\|\|`/`!`) e uma coluna de contexto booleano no `predicate_graph.csv` |
| **M-10** | D1 | **REFUTADO** | "21 de 27 leituras vivas são sobre `byte[]`" (design D-2) | Tipos declarados `[✓]`: `byte[]`=**17**, `char[]`=2, `Key`=5, `SecretKey`/`Object`/`String`=3 | 17 (19 com `char[]`). O argumento que sustenta sobrevive em 19/27; o número não |
| **M-11** | D4 | **INCOMPLETO** | Nada na gh105 antecipa o Grupo 10 da gh104 | Nenhuma das 49 tasks o executa `[✓]`, e isso é declarado 4×. Mas a task 2.5 **reescreve** o pytest de que 10.1 depende, e as tasks 3.2/3.3/3.4/5.6/6.2 tocam exatamente as três specs que 10.5 mede (`TrustManagerFactorySpec`, `KeyStoreSpec`, `SSLContextSpec`) | Rodar o Grupo 10 **antes** do Grupo 2 da gh105, ou reescopá-lo como conjunto |
| **M-12** | D5 | **REFUTADO** (como redigido) | "`condition(...)` is reserved for overload discrimination and `ORDER` branching" | Existem **50 sítios `condition(...)` não-predicativos legítimos** `[✓]` (30 de `ConscryptAliasTable` em 10 specs, `isValid`, verificações de comprimento/iteração que são CONSTRAINTS da regra) | O gate está certo (discrimina por `(Property`), o texto do invariante não. Reescrever: "`condition(...)` não pode conter **leitura de predicado**"; CONSTRAINTS e overload seguem válidos |
| **M-13** | D2b | **INCONSISTENTE** | As magnitudes publicadas dimensionam o `jca_android` | O `errors.csv` traz `{TLSv1.2, TLSv1.3}` ⇒ medido sobre o **`jca`**; as listas de constraints diferem entre os dois sets em 5 specs | Aprendizado 7. O ganho de 6.835 da task 3.3 encolhe sob o set-alvo. Marcar toda magnitude como medida-sobre-`jca` |
| **M-14** | D8/D6 | **REFUTADO** | "`backup/` (rv-android tree, **gitignored**)" (`spec.md:101`) | `git check-ignore` vazio; `git ls-files backup/` = **921 arquivos versionados**; `rvsec` e `rv-android` são **um** repositório `[✓]` | "Aposentar para `backup/`" **versiona** o módulo morto em vez de removê-lo (P3). Ou remover de fato, ou ignorar `backup/` de fato |
| **M-15** | D7/D8 | **REFUTADO** | "as 8 leituras sem acusador" / "as 8 specs leitoras restantes" | **10** arquivos têm leituras ⇒ 9 restantes após 4.1 `[✓]`. E são **9** leituras sem acusador: `PBEParameterSpecSpec.c2` (`:32-40`) lê `RANDOMIZED` e seu gêmeo `c3` liga só o construtor de 2 argumentos `[✓]` — mesmo teste pelo qual `GCMParameterSpecSpec.c1/c2` já estão na lista | Corrigir para 9/9. E `27−N` nunca define `N` (é 3) |
| **M-16** | D2b | **REFUTADO** | `SSLContext randomized[sr]` é conectável (task 5.3) | `SSLContext.cryptsl:9` — `Init: init(kms, tms, _)`: **`sr` não é ligado por evento algum** `[✓]`. É a única cláusula assim nas 33 regras; o próprio oráculo nunca a checa | Registrar como inexequível, não fiar |
| **M-17** | D5 | **REFUTADO** | O `CipherSpec` não tem defeito vivo de "dois eventos casam a mesma chamada" | `:56 doFinal()` e `:62 doFinal(..)` casam ambos a chamada sem argumentos; nenhuma task repara | Acrescentar ao Grupo 6 |

### MINOR (resumo; detalhe nas seções por dimensão)

`alg()` não é splitter — zero ocorrências em api30, o único é `part(0,"/",transformation)`, em 2
cláusulas · "31 de 90" exclui silenciosamente as 2 NEGATES (o total do oráculo é 92) · "11 generic
não-compiláveis" versus "11 + FSM358" = 12 · o `defsuses` está em `rvsec/rvsec/pom.xml:27`, não no
pom raiz · INV-INS-135 chama "archived" o `jca`, que é o congelado · `epsilon` é token reservado do
ERE — um gate ingênuo de direção reversa vai marcá-lo (idem `generic_new/ListIterator_Set.mop`) ·
o guarda negado é escrito `!( … )` em dois arquivos, que um regex `!\s*ExecutionContext` perde ·
"the two archived files whose `ere` names an undeclared event" — só o `GCMParameterSpecSpec` o faz ·
INV-INS-141/144 citam INV-INS-128/124, que só existem no delta não-arquivado da gh104, sem dizer que
a gh104 tem de arquivar antes · `design.md:85` mapeia `test_inv_ins_140_genericity_214`, que nenhuma
task cria · as tasks 6.2/6.3 e metade da 6.1 não rastreiam a requirement alguma · "F1-F6" na task
7.1 (não existe F6) · Português nos artefatos: `fiação` (`tasks.md:55`), `Fase`
(`proposal.md:6`, `design.md:3`), `PROVADO` (`design.md:24`), `FEN-PBK-RESIDUO` (`spec.md:354`,
`tasks.md:71`) — este último chega ao spec principal no arquivamento sem definição · o
`grep -r "defsuses"` do cenário `spec.md:619` é insatisfazível (4 referências vivas, uma na change
**aberta** gh48) · `ErrorType` do *not observed* não é especificado, e a gh104 legislou exatamente
essa decisão (`gh104 spec.md:232`) sobre uma premissa que a gh105 inverte · a requisição de
sobrecarga fixa no idioma `Object` falta em 4 lugares, incluindo a instrução operativa de
recuperação (`design.md:242`) · os artefatos ainda não estão versionados (`?? openspec/changes/gh105-…`),
logo não existe commit `refs #105`.

---

## 3. Seções por dimensão

### D1 — Exatidão factual

**Re-derivado da fonte e CONFIRMADO** (parsers próprios; onde havia dois métodos, os dois
concordaram): 33 regras · 54 ENSURES / 36 REQUIRES / 2 NEGATES / **32 predicados distintos** ·
aridades **59 unárias / 31 binárias sobre 90**, máximo 2 — o total do oráculo é 92 e o "90" exclui
as duas NEGATES, exatamente como o delta redige em `spec.md:234` · o `generatedKey` "quaternário"
**é** artefato de contagem de vírgulas (ingênuo 4 versus 2 com profundidade em
`part(0,"/",transformation)`) · **19 predicados conectáveis / 35 cláusulas conectáveis**, derivados
sem consultar o plano: 20 predicados distintos aparecem em `REQUIRES`, `preparedEC` é o único sem
nenhum `ENSURES` em qualquer regra ⇒ 19; 36 − 1 = 35 · 34 pares distintos (a dupla `!encrypted` do
`Mac.cryptsl:82,84`) · `Property` = **25** valores · 21 escritos / 4 lidos, e apenas 3 com as duas
pontas (`GENERATED_PRIVATE_KEY` é lido em `CipherSpec.mop:85` e nunca escrito) — donde "realiza 3" ·
**49 escritas (42 corpo / 7 `@match` / 0 `@fail`)**, **27 leituras (27/27 em `condition`)**,
**9 remoções (8 `@fail` + 1 corpo, 4 na sobrecarga depreciada)** · a armadilha do `validate(`
ingênuo (31 versus 27) confirmada: `KeyPairGeneratorSpec` tem um `validate(int)` privado ·
18 valores escritos-e-nunca-lidos sobre 35 sites · `MACED` e `GENERATED_CIPHER` com **zero** sites
em `jca` e `jca_android` (8 sites no set arquivado) · **134 = 23 import + 27 validate + 49
setProperty + 9 remove + 25 accepting-state + 1 comentário**, e a 134ª é o comentário em
`MessageDigestSpec.mop:37` (`:25` no `jca`, que é o que a gh104 cita — correto) · órfãos **17/9**
(`jca_android`), **18/10** (`jca`, o extra é `MessageDigestSpec{reset}`), **0** (arquivado) ·
`hasEnsuredPredicate`: **0** sites nos 214 · zero parâmetros de array primitivo nos 214 ·
214 = 23+23+23+118+27 · 0 de 145 arquivos `generic`/`generic_new` citam `ExecutionContext` ·
97.018 eventos, `UnsatisfiedConstraint` = **0** ocorrências.

**Linhas citadas, todas abertas e conferidas**: `PBEKeySpecSpec.mop:74` (`remove(SPECCED_KEY, s)`) ·
`KeyPairSpec.mop:38` (escreve `GENERATED_PUBLIC_KEY` sobre `privateKey`) · `SecretKeySpec.mop:26` ·
`TrustManagerFactorySpec.mop:74-78` — os **três** defeitos ao mesmo tempo: `returning(TrustManager[][])`,
`call(public KeyManager[] TrustManagerFactory.getTrustManagers())` e
`setProperty(GENERATED_KEY_MANAGERS, trustManager)` · `jca/GCMParameterSpecSpec.mop:23,34,48`
(`event c1` duplicado em 23 e 34; `ere : c1 | c2` em 48 nomeando um `c2` não declarado) ·
`DefsUsesGraph.java:65-66` (`new File("/pedro/…")`) · `javamop.jj:1456`/`:1470` ·
`AnalysisSeedWithSpecification.java` `doPredsMatch:475`/`trackedTypes:564` ·
`ConstraintSolver.java:174,:484`.

**Evidência do monitor gerado** (a peça de que a change inteira depende), citada literalmente de
`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`:

```java
3713 final boolean Prop_1_event_i2(int mode, Key key, Cipher c) {
3715   if ( ! (ExecutionContext.instance().validate(Property.GENERATED_KEY, key) || … ) ) {
3716     return false;
3717   }
…
3725   int nextstate = this.handleEvent(4, Prop_1_transition_i2) ;
```

O guarda falso retorna antes do `handleEvent`: a transição é suprimida e a **próxima** chamada é
acusada de ordem. CONFIRMADO.

**REFUTADO em D1**: M-1 (49.817 é a população do `jca`), M-10 (17 `byte[]`, não 21), M-2, M-3, e as
unidades erradas do aprendizado 15 — `newSslSocketFactory` é um método do okhttp3 lido como evento
`.mop`, e "3 de 35 cláusulas" é uma contagem de **predicados** apresentada como contagem de
cláusulas (`design.md:12`).

**Comandos** (saída relevante):
```
$ ISoMC total 70760 · jca 10 specs órfãs = 49817 (70.40%) · jca_android 9 specs = 39682 (56.08%)
$ grep -ho "setProperty(Property\.[A-Z_]*" jca_android/*.mop | wc -l           → 49
$ grep -ho "validate(Property\.[A-Z_]*"    jca_android/*.mop | wc -l           → 27  (ingênuo: 31)
$ grep -c "ExecutionContext" jca_android/*.mop | awk -F: '{s+=$2} END{print s}' → 134
```

### D2 — Conformidade CrySL

**Semântica do oráculo — CONFIRMADA com file:line** (checkout `349073ff`):
casamento **por nome** (`CrySLPredicate.equals` compara só `predName`) · `REQUIRES` **monotônico por
objeto** (`ensuredPredicates` só cresce) · comparação de valor **só** nas posições cujo tipo está em
`trackedTypes = ["java.lang.String","int","java.lang.Integer"]`
(`AnalysisSeedWithSpecification.java:564`), sem distinção de caixa, com splitters ·
**`NEGATES` é no-op nesta geração**: `if (predToBeEnsured.isNegated()) continue;` em `:232-234` e
`if (predToBeEnsured.isNegated()) return;` em `:243-245`.

**Divergências não declaradas** (o delta é mais forte que o oráculo em uma direção e mais fraco em
outra, e nenhuma das duas é declarada como fortalecimento deliberado):
- **mais forte**: a gh105 implementa `negate` como retirada real (INV-INS-142, `PredicateStore.negate`)
  onde o oráculo não faz nada. Fortalecimento silencioso — pode ser correto, mas tem de ser dito.
- **mais fraca**: o oráculo emite `RequiredPredicateError` para predicado **ausente**, igual ao caso
  de valor divergente. O `NOT_OBSERVED` da gh105 sub-acusa em relação ao oráculo. A justificativa
  em D-4 aponta o mecanismo errado (`doPredsMatch` com extração vazia, que mapeia para *satisfeito*);
  o análogo correto é o `ImpreciseValueExtractionError` (`ConstraintSolver.java:167-183`).
- **mais forte, outra vez**: a task 4.3 arma acusadores em leituras que não traduzem cláusula
  nenhuma (B-7).

**Fatos medidos além do briefing**: apenas **2 das 36 posições de `REQUIRES`** são alguma vez
comparadas por valor — as duas `part(0,"/",transformation)` do `Cipher`, e uma delas está na
cláusula 7, que não tem produtor no set. Isto é, toda a maquinaria de aridade-N com valores
rastreados serve, hoje, **uma** cláusula viva. Não é razão para removê-la, é razão para não a
apresentar como o motivo central da nova store.

**`ORDER` — CONFIRMADO**: a produção `Order` da gramática Xtext (`:99-134`) é sequência,
alternativa, `*`/`+`/`?` e agrupamento; os agregados (`Gets := g1 | g2`) são regulares (41 deles,
nenhum vazio ou cíclico). A alegação de equivalência por AFD do G-ORDER é formalmente sólida, e a
ressalva do mapeamento (o `.mop` separa overloads, logo não há bijeção) **é** honestamente carregada:
artefato versionado, invariante de não-inferência, risco R7 nomeado e duas tasks orçadas (2.6, 7.1).
Duas lacunas: o esquema do `order_alphabet_map.csv` é `.mop`→`ORDER` e **não tem classe ε** para os
eventos de ramo de constraint que a F1 cria; e os artefatos não registram que, nessa gramática, `,`
liga **mais fraco** que `|` — inverso da convenção de regex, e visível justamente no `Cipher`.
O `ORDER` do `SecureRandom` é `Ins, Seeds?, Ends*` e a omissão de `next2` no estado `end` confere.

**Versão da regra — CONFIRMADA**: api30 **é** a versão contra a qual o `jca_android` foi derivado
(cinco listas de constraints batem literalmente; zero batem contra o `jca`). O aprendizado 7 é
respeitado no set — mas **não** nas magnitudes publicadas (M-13), nem no Javadoc de
`Property.GENERATED_CIPHER`, que cita `generatedCipher[this] after Inits`, ausente do api30.

**Spot-checks fim-a-fim** (5 regras): `Cipher` → B-1, B-2, B-3, M-4 (das seis cláusulas, uma está
implementada e errada, uma não tem casa, duas são condicionais sem guarda declarada, uma é negada);
`SecureRandom` → `Ends*`/`next2` correto, órfãos corretos, mas a task 5.3 manda "descartar as
escritas de argumento autoboxado" quando o `next3` marca um **valor de retorno**; `PBEKeySpec` → o
único `NEGATES` verdadeiro, objeto nomeado, no evento do `after`, resíduo de Kleene declarado —
o mais limpo dos cinco; `Mac` → dupla `!encrypted`, `MACED` com zero sites, e o `MacSpec` lê
`generatedKey`, que a regra não exige; `SSLContext` → 7 escritas / 0 leituras, `sr` não ligado (M-16).

### D3 — Coerência interna

**CONFIRMADO**: 28 cenários, todos com exatamente 4 `#`; toda requirement tem ≥1 (na verdade ≥2);
exatamente **2 MODIFIED + 6 ADDED** e **16 invariantes INV-INS-130…145**, contíguos, sem duplicata;
RFC 2119 consistente (SHALL 22, MUST 100, MUST NOT 15, MAY 1); os 16 invariantes têm ao menos uma
task e uma linha no mapa de design — **nenhum invariante órfão**; a disposição dos `remove()`
concorda nos quatro artefatos; **toda quantidade afirmada em dois artefatos é afirmada
identicamente**; o delta da gh104 **não** modifica nenhuma das duas requirements que a gh105 modifica
(a cópia é da versão corrente, não de uma pré-gh104); os dois cenários herdados que **estão** lá são
byte-idênticos ao principal.

```
$ openspec validate gh105-predicate-wiring            → valid   rc=0
$ openspec validate gh105-predicate-wiring --strict   → valid   rc=0
$ openspec status --change gh105-predicate-wiring     → 4/4 artifacts complete
```
Nota: o `openspec` 1.7.0 passa a change e **não** detecta o MODIFIED parcial (M-5). Um `validate`
verde não é evidência de cópia fiel.

**Achados**: M-5, M-6 · INV-INS-143/141 dizem "na mesma task", o `tasks.md` codifica em checkboxes
separados (4.1/4.2) e "no mesmo **commit**" (2.5), e a nota de despacho autoriza 2.5 em paralelo ao
Grupo 3 — abrindo a janela em que os gates esperam a nova store e todas as specs ainda usam a antiga ·
o mapa de design tem linhas só para invariantes, **zero** para as 8 requirements, e as tasks 6.2/6.3
não rastreiam nada · `design.md:85` nomeia um teste que nenhuma task cria · o delta manda a junção
**incondicionalmente** para cadeias co-observáveis (`:457-460`) e não tem regra de desempate
store-versus-junção; a task 5.4 já a viola, e o delta é o que arquiva · o G-PRED2 é vermelho pelo
próprio contrato entre 2.4 e 5.7, e nenhum artefato declara essa janela · `27−N` nunca define `N`.

### D4 — Consistência com a gh104

**CONFIRMADO**: gh104 está em **87/96**, com as 9 abertas todas no Grupo 10 · o espaço de numeração
está limpo (principal 01-12/70-73/88-103/109-115; gh100 104-108/116-117; gh104 118-129; gh105
130-145; nenhum 130-145 usado em outro lugar) · INV-INS-145 e INV-INS-115 concordam literalmente
(17/53 s/18/`StackOverflowError`/parser de enable-set); a gh105 omite o número n=24 do limite de
String, omissão e não contradição · INV-INS-137 "realiza" INV-INS-111 de forma limpa e declarada ·
INV-INS-119 não colide · nenhuma das 49 tasks executa o Grupo 10, declarado 4× · o `@Deprecated` é
seguro para todos os outros consumidores de `ExecutionContext` · **medido**: rodar o `gh104_gates.py`
sobre o controle `jca` e depois sobre uma cópia com os três marcadores `ExecutionContext`
substituídos por `PredicateStore` produz **0 registros de hit alterados**.

**Achados**: B-10, M-7, M-11 · "G-PRED continua a tranca de identidade byte-a-byte do `jca`" é
refutado pela docstring do próprio gate (`gh104_gates.py:1026`: *"The seed is its own oracle, which
makes the gate trivially green on `jca`"*) — restrito ao `jca` ele é tautológico; a tranca real é
INV-INS-109(a) mais o censo de 134 em `test_gh104_structural_gates.py:230` · a razão que a task 2.5
dá para a urgência está errada (o `accept_requires` é um `any(...)`, fica verdadeiro até a **última**
spec migrar; o que fica vermelho em 4.1 é o G-PRED e o pytest de INV-INS-128 — o *timing* está certo,
a justificativa não) · a gh104 tem uma incoerência própria, herdada: INV-INS-118 diz "21 specifications
… which INV-INS-128 removes" enquanto a árvore tem 23.

### D5 — Viabilidade técnica

**Matriz de colapso, medida** (binários `target/release`, em scratch próprio):

| parâmetro declarado | cabeçalho do `.rvm` | `CachedWeakReference` no monitor | rc |
|---|---|---|---|
| `byte[]` | `TByte()` — lista **inteira** apagada | 0 | 0 (mensagem de sucesso) |
| `char[]` | `TChar()` | 0 | 0 |
| `int[]` | `TInt()` | 0 | 0 |
| `String[]`, `Object[]`, `Object` | preservado | 9 | 0 |

O colapso é **específico de arrays primitivos**, a redação do delta está exata, e o segundo parâmetro
inocente também é apagado. Dois corolários úteis: o G-PARAM tem de ler o **`.rvm`** (o `.aj` ainda
carrega `byte[] x`), e arrays de **referência** sobrevivem — logo as ligações `KeyManager[]`/
`TrustManager[]` da task 5.6 não precisam do idioma `Object` (precisam do reparo B-5, que é outro).

**CONFIRMADO**: o guarda compila para `return false` antes do `handleEvent` (64 instâncias) e as
leituras trivalentes são consistentemente "só no corpo" nos quatro artefatos · o splitter "pelo
chamador" é implementável e foi validado fim-a-fim em scratch (`.mop` → `.rvm` → monitor, com helper
e leitura trivalente de aridade 2 sobreviventes); `currentTransformation` já é campo vivo do
`CipherSpec` · as **quatro** regras de junção seguem de falhas medidas no piloto, uma a uma
(a=E1, b=E3, c=E4, d=fricção 1) · `SecureRandomSpec` (15→13), `SSLContextSpec` (5), `PBEKeySpecSpec`
(7→5) e `MacSpec` (8) ficam longe do teto — só o `CipherSpec` não.

**Achados**: B-1, B-4, B-5, M-8, M-9, M-12, M-17 · a razão dada em `design.md:215` para não oferecer
o bookkeeping de accepting-state ("write-only leak") é **refutada**: há 396 chamadas leitoras via
`Assertions.mustBe/mustNotBeInAcceptingState` e 360 de `hasEnsuredPredicate` no corpus de testes do
`rvsec-agent`. O congelamento segue seguro (esse corpus tece `jca`), mas a task 8.3 replica esse
corpus e nenhum artefato diz que ele é preso ao `jca` · a coexistência do spec de junção com o
`CipherSpec` no mesmo joinpoint (`Cipher.init`) e a deduplicação de relatórios não têm uma linha em
nenhum artefato, e o piloto marca isso como não testado · a requisição de sobrecarga fixa falta em 4
lugares, incluindo a instrução operativa de recuperação em `design.md:242`.

**NÃO VERIFICÁVEL AQUI**: se `args(Object)` do AspectJ casa primitivos autoboxados. O delta afirma
as duas direções — `spec.md:157` diz que sim, `spec.md:399` diz que `Object+` rejeita primitivos.
Não há `ajc` na árvore. Um único weave contra `SecureRandom.setSeed(long)` resolve.

### D6 — Segurança do congelamento

**CONFIRMADO**: o `@Deprecated` é **inerte nos cinco sítios de compilação** — `showDeprecation=false`
no pom raiz (`:256-257`) e no `docker/mop`, ajc com `-Xlint:ignore -proceedOnError` e stderr
suprimido, dexlib2 falhando só em `exit!=0`, `TraceRunner` com `-nowarn -proc:none`; não há
`-Werror`, `compilerArgs` ou `Xlint` em nenhum pom, e o spotbugs roda com `failOnError=false` ·
`codes.csv` é **por set** por construção — só existe `jca_android/codes.csv`, e o message gate
resolve por diretório; a família *not observed* não alcança o `jca` · INV-INS-09 existe literalmente
(`specs/instrumentation/spec.md:273`) e a exclusão das duas stores no mesmo processo é **mais forte**
do que os artefatos dizem: `jca` e `jca_android` têm nomes de arquivo idênticos, logo um diretório não
pode conter os dois — é prova onde o invariante é só regra · nada no reator depende do
`rvsec-mop-defsuses` (2 linhas em pom, nenhuma entrega via `main.basedir`) · nenhum caminho de
geração perturba as saídas do `jca` (um diretório de set por execução, controle com manifesto sha256).

**Achados**: B-8, B-9, M-14 · o `grep -r "defsuses"` do cenário é insatisfazível: sobrevivem
`rvsec/CLAUDE.md:12`, `rvsec/rvsec/CLAUDE.md:11,23`, `check_no_legacy_mop.py:128` e a change **aberta**
`gh48-project-finalization` · o `ErrorType` do *not observed* não é especificado, e é outro enum
compartilhado (23/23 importam `eh.*`); a gh104 legislou exatamente essa decisão e recusou
`RequiredPredicate` sobre uma premissa que a gh105 inverte · o helper óbvio para os splitters
(`CipherTransformationUtil`) **está** em `FROZEN_PATHS`; o lugar certo é o
`Api30CipherTransformationUtil` · o `gh101_predicate_inventory.py` regenera o inventário do `jca` e
compara byte a byte com a baseline versionada — é uma edição proibida que nenhuma task nomeia.

**Resumo da dimensão**: o congelamento está protegido por construção contra o caminho exato que
falhou da última vez, e continua aberto nos três caminhos vizinhos por onde o mesmo erro viaja —
`Property.java`, a nota REMOVED sobre as sobrecargas, e a ausência de teste para o próprio
INV-INS-132. Todos fecháveis com texto de invariante; nenhum exige redesenho.

### D7 — Completude e lacunas

**CONFIRMADO**: as **sete** lacunas de genericidade do §8-bis do plano estão todas carregadas ·
`jca/GCMParameterSpecSpec.mop:23,34,48` confere exatamente · **todos os nove itens abertos do §7**
da verificação v2 estão carregados nos artefatos.

**Achados**: B-4, B-6, B-7, M-2, M-3, M-8, M-15 · o `gate_allowlist.csv` tem 3 de 7 linhas que ficam
falsas e nenhuma task o toca · o corpus C5 da task 8.3 é descrito como `errors_unit_tests.csv`, que é
um agregado de 298 linhas, **não** traços (aprendizado 9); o corpus real é `rvsec-agent/src/test`,
preso ao `jca` pelo `pom.xml:106` · o "before" do harness na task 8.4 não tem quem o produza: o
harness recebe dois diretórios de set e nada tira o snapshot pré-mudança do `jca_android` · a
pré-condição bloqueante do weaver está em Non-Goals mas **nenhuma task roda o gate de alcance**, e a
8.7 pode fechar `closes #105` sem ele · INV-INS-140 encaminha uma geração que falhou sem `.rvm` para
"skipped and counted" — silêncio parecendo sucesso dentro do gate construído para impedir isso.

**Sobre a ordem F2 → F3** (o ponto que o mandato pedia para examinar com cuidado): o veredito
trivalente **de fato** fecha o aprendizado 3 para a janela entre F2 e F3 — mover uma leitura de
predicado nunca escrito para o corpo produz `NOT_OBSERVED`, não `UnsatisfiedConstraint`, logo não há
falsa acusação. Mas duas consequências ficam sem declaração: a janela é de **100 % `NOT_OBSERVED`**
para todas as leituras cujos produtores só chegam no Grupo 5, e nesse intervalo o par de traços
"satisfaz/viola" que INV-INS-144 exige é impossível de produzir do lado "satisfaz". A task 4.4 pede
esse par.

### D8 — Princípios e workflow

**CONFIRMADO**: nomenclatura da change, `.openspec.yaml` com `schema: rv-sdd`, issue #105 aberta com
`type:feature` + `track:full-sdd`, `#105` no cabeçalho, `refs`/`closes` na 8.7, **nenhum
`Co-Authored-By`** em nenhum commit desde 2026-08-07, conjunto de artefatos completo para a trilha
(sem README, seguindo o precedente da gh104), `validate` verde, cenários no formato WHEN/THEN/AND com
valores concretos, **zero linguagem promocional**, a requirement `Event Membership` copiada como
superconjunto fiel, `BREAKING` marcado, e nenhum ADR faltando pelo precedente gh104/gh101.

**P1** — em geral honesto. O **G-PARAM não é especulativo**: ele guarda trabalho que a task 5.1
agenda nesta mesma change, contra uma falha que retorna 0 com mensagem de sucesso. G-ACC, G-PRED2 e
o gate de import são todos ganhos por defeito medido, e o G-PRED2 é **substituição**, não adição.
A folga real é pequena e concentrada: "MUST support arity N" sobre-especifica contra um máximo
medido de 2, e o idioma de holder arrasta um `reset()` público de teste para a API de produção.

**P2** — falha o teste de execução em 3 de 5 tasks amostradas (3.5, 6.1, 7.1). Termos usados sem
definição para quem não leu o plano de 1.230 linhas: `FEN-PBK-RESIDUO`, `PROVADO`, "bucket (a)",
"mechanism A/B" (indefinido dentro do próprio `spec.md:151`), `27−N`, `C5`, "plan §8-bis/§3.1-bis".
As 35 cláusulas e os 17 órfãos são afirmados nove vezes e **enumerados em lugar nenhum** — que é
exatamente por onde M-2, M-3 e M-4 passaram.

**P3** — a decisão de manter o `ExecutionContext` é sólida; a **alegação** de conformidade não é.
`WORKFLOW.md:254` nomeia "deprecation annotations" na lista do proibido, e D-1 rebate só a metade
"shim". A tensão é real mas resolúvel dos dois lados: o `ExecutionContext` **não** é código morto —
serve o `jca` congelado —, o que tira a anotação do alcance de P3; e, como ela é comprovadamente
inerte, retirá-la não custa nada e deixa o arquivo byte-idêntico. Recomendo retirá-la: o argumento
de "congelado por construção" fica mais forte sem exceção alguma. Ver também M-14 sobre o `backup/`.

**P4** — a metade promocional está impecável. A metade de linhagem tem dois pontos de vazamento para
Javadoc (`design.md:201-202` prescreve um comentário que diz "on the old substrate too"; a task 1.2 e
INV-INS-132 mandam um "Javadoc pointer to the successor") mais o nome `G-PRED2`, que é linhagem num
gate cujo predecessor continua vivo.

---

## 4. A razão das 35 cláusulas

As 36 cláusulas `REQUIRES` das 33 regras api30, extraídas por parser próprio. **Conectável** = o
predicado tem ao menos um `ENSURES` em alguma regra (35 das 36; só o `preparedEC` falha).
**Fiável no set** = a regra consumidora **e** ao menos uma regra produtora têm `.mop` em
`jca_android` — **25 das 35**. "Casa" é onde os quatro artefatos colocam a cláusula.

| # | consuming rule | clause | neg | cond | wireable in set? | tasks.md §5 home | verdict |
|---|---|---|---|---|---|---|---|
| 1 | AlgorithmParameters | `preparedAlg[parAr]` |  |  | no consumer .mop | **NONE** | **REFUTED** — no home |
| 2 | AlgorithmParameters | `alg in {"AES", "DESede"} => preparedIV[params]` |  | Y | no consumer .mop | 5.1/5.5 | **INCOMPLETE** — unwireable, no record category |
| 3 | AlgorithmParameters | `alg in {"DiffieHellman"} => preparedDH[params]` |  | Y | no consumer .mop | 5.5 (listed as Cipher-closing; it is not) | **INCOMPLETE** — unwireable, no record category |
| 4 | CertPathTrustManagerParameters | `generatedCertPathParameters[params]` |  |  | no consumer .mop | **NONE** | **REFUTED** — no home |
| 5 | Cipher | `generatedKey[key, part(0,"/",transformation)]` |  |  | yes | 5.4 | CONFIRMED |
| 6 | Cipher | `randomized[ranGen]` |  |  | yes | 5.1/5.3 | CONFIRMED |
| 7 | Cipher | `preparedAlg[param, part(0,"/",transformation)]` |  |  | no producer .mop | **NONE** | **REFUTED** — no home |
| 8 | Cipher | `!macced[_, plainText]` | Y |  | yes | **NONE** | **REFUTED** — no home |
| 9 | Cipher | `part(1,"/",transformation) in {"CBC", "CTS", "CTR", "CFB", "PCBC", "OFB"` |  | Y | yes | 5.1/5.5 | **REFUTED** — polarity/guard unaddressed |
| 10 | Cipher | `part(1,"/",transformation) in {"GCM"} => preparedGCM[params]` |  | Y | yes | 5.5 | **REFUTED** — polarity/guard unaddressed |
| 11 | GCMParameterSpec | `randomized[src]` |  |  | yes | 5.1/5.3 | CONFIRMED |
| 12 | IvParameterSpec | `randomized[iv]` |  |  | yes | 5.1/5.3 | CONFIRMED |
| 13 | KeyGenerator | `randomized[ranGen]` |  |  | yes | 5.1/5.3 | CONFIRMED |
| 14 | KeyManagerFactory | `generatedKeyStore[keyStore]` |  |  | yes | 5.6 | CONFIRMED |
| 15 | KeyPair | `generatedPrivkey[consPriv]` |  |  | yes | 5.7 catch-all | INCONSISTENT / INCOMPLETE |
| 16 | KeyPair | `generatedPubkey[consPub]` |  |  | yes | 5.7 catch-all | INCONSISTENT / INCOMPLETE |
| 17 | KeyPairGenerator | `alg in {"DH"} => preparedDH[params]` |  | Y | yes | 5.5 (listed as Cipher-closing; it is not) | **REFUTED** — polarity/guard unaddressed |
| 18 | KeyPairGenerator | `alg in {"DSA"} => preparedDSA[params]` |  | Y | no producer .mop | **NONE** | **REFUTED** — no home |
| 19 | KeyPairGenerator | `alg in {"RSA"} => preparedRSA[params]` |  | Y | no producer .mop | **NONE** | **REFUTED** — no home |
| 20 | KeyPairGenerator | `alg in {"EC"} => preparedEC[params]` |  | Y | — non-connectable (no producer rule) — | 5.5 `unclosable` | CONFIRMED |
| 21 | Mac | `preparedHMAC[params]` |  |  | yes | 5.5 (listed as Cipher-closing; it is Mac's) | CONFIRMED |
| 22 | Mac | `!encrypted[output1, _]` | Y |  | yes | **NONE** | **REFUTED** — no home |
| 23 | Mac | `!encrypted[output2, _]` | Y |  | yes | **NONE** | **REFUTED** — no home |
| 24 | PBEKeySpec | `randomized[salt]` |  |  | yes | 5.1/5.3 | CONFIRMED |
| 25 | PBEParameterSpec | `randomized[salt]` |  |  | yes | 5.1/5.3 | CONFIRMED |
| 26 | PKIXBuilderParameters | `generatedKeyStore[keyStore]` |  |  | no consumer .mop | 5.6 | **INCOMPLETE** — unwireable, no record category |
| 27 | PKIXParameters | `generatedKeyStore[keyStore]` |  |  | no consumer .mop | 5.6 | **INCOMPLETE** — unwireable, no record category |
| 28 | SSLContext | `generatedKeyManager[kms]` |  |  | yes | 5.6 | CONFIRMED |
| 29 | SSLContext | `generatedTrustManager[tms]` |  |  | yes | 5.6 | CONFIRMED |
| 30 | SSLContext | `randomized[sr]` |  |  | yes (mas `sr` não é ligado por evento algum — M-16) | 5.1/5.3 | **REFUTADO** — inexequível na própria regra |
| 31 | SecretKeyFactory | `speccedKey[keySpec, _]` |  |  | no consumer .mop | 5.7 (names the PRODUCER PBEKeySpec) | **INCOMPLETE** — unwireable, no record category |
| 32 | SecretKeySpec | `preparedKeyMaterial[keyMaterial]` |  |  | yes | 6.1 (producer half only) | INCONSISTENT / INCOMPLETE |
| 33 | SecureRandom | `randomized[seed]` |  |  | yes | 5.1/5.3 | CONFIRMED |
| 34 | Signature | `generatedPrivkey[priv]` |  |  | yes | 5.7 catch-all | INCONSISTENT / INCOMPLETE |
| 35 | Signature | `generatedPubkey[pub]` |  |  | yes | 5.7 catch-all | INCONSISTENT / INCOMPLETE |
| 36 | TrustManagerFactory | `generatedKeyStore[keyStore]` |  |  | yes | 5.6 | CONFIRMED |

**Contagens**: 11 CONFIRMADAS · 5 INCONSISTENTE/INCOMPLETO · 6 INCOMPLETO (infiável, sem categoria
de registro) · 13 REFUTADAS · 1 CONFIRMADA como `unclosable` correta (`preparedEC`).
**Nove cláusulas não têm casa alguma nos quatro artefatos**: 1, 4, 7, 8, 18, 19, 22, 23 e — pela
metade — 32. Delas, 8 têm consumidor vivo no set.

**Do lado ENSURES (54)**: 21 não têm casa — 12 em regras sem `.mop`, mais `macced`×3 e
`encrypted`×3 (justamente os produtores das três cláusulas negadas), `SecretKeySpec speccedKey` e as
duas do `KeyStore`. Outras 13 são write-only no oráculo e precisam do registro de omissão
deliberada que INV-INS-137(b) exige e nenhuma task cria.
**Do lado NEGATES (2)**: `SecretKey generatedKey[this,_] after d` → CONFIRMADA como `unclosable`
(não há evento `destroy` no set); `PBEKeySpec speccedKey[this,_] after cP` → colocação CONFIRMADA
(`PBEKeySpecSpec.mop:74`, objeto nomeado, no evento do `after`), semântica INCONSISTENTE
(fortalecimento silencioso — o oráculo trata `NEGATES` como no-op).

**Posições curinga `_`** — inexprimíveis na API acordada `validate(Property, Object...)`, que não
tem forma de "qualquer valor aqui": `Cipher !macced[_, plainText]` (curinga na posição **0**, a do
objeto ligado), `Mac !encrypted[output1|output2, _]`, `SecretKeyFactory speccedKey[keySpec, _]` e as
duas NEGATES. O `Property.java:25-35` já registra a resposta certa para o caso do `macced`
(a projeção sobre a posição unária) — a gh105 perde esse conhecimento.

---

## 5. Perguntas abertas para o pesquisador

Só o que é genuinamente decisão sua, com os números prontos.

1. **Orçamento de alfabeto do `Cipher` (B-1).** O `CipherSpec` está em 17/17. Fechar as cláusulas
   7/9/10 dentro dele custa ≥1 e até 6 eventos; 18 não gera. As saídas: (a) rotear
   `randomized[ranGen]`, `preparedAlg[param]` e `prepared*[params]` para **specs de junção**, custo
   zero no alfabeto do `CipherSpec` — parece a única saída que preserva a D-9; (b) dividir o
   `CipherSpec` em dois `.mop`; (c) registrar as três como não fiáveis nesta change. Qual?
2. **Escopo real da F3 (M-3).** O alvo honesto é **25 cláusulas fiadas + 10 registradas**, não 35.
   Aceita reescrever a meta, e aceita criar a segunda categoria de registro ("a regra consumidora
   não tem especificação no set", 7 cláusulas) ao lado do `unclosable` (3 cláusulas + `preparedEC`)?
3. **Polaridade negada (B-3).** Três cláusulas. Implementar `validateNegated` com a tabela
   trivalente invertida, ou registrá-las como fora de escopo desta change? A segunda opção é
   defensável e barata; a primeira fecha o `Mac` de verdade.
4. **`NEGATES` como fortalecimento (D2).** O oráculo não faz nada com `NEGATES`. A gh105 implementa
   retirada real. Declarar como fortalecimento deliberado (com a justificativa) ou alinhar ao
   oráculo e manter o `PBEKeySpecSpec.mop:74` apenas como registro?
5. **`NOT_OBSERVED` como sub-acusação (D2).** O oráculo emite `RequiredPredicateError` para
   predicado ausente. A gh105 emite um código próprio. É a decisão certa para o alcance de
   instrumentação, mas é uma divergência de **direção** e precisa ser declarada como tal — e o
   `ErrorType` que a carrega ainda não foi escolhido (a gh104 recusou `RequiredPredicate` sobre uma
   premissa que esta change inverte).
6. **`@Deprecated` (D8/P3).** Recomendo **retirar**: é comprovadamente inerte (`showDeprecation=false`,
   nenhum `-Werror`), `WORKFLOW.md:254` nomeia deprecation annotations no proibido, e sem ela o
   `ExecutionContext.java` fica byte-idêntico — o argumento de "congelado por construção" fica sem
   exceção alguma. Aceita?
7. **`Property.java` (B-9).** Acrescentar constantes é seguro e necessário. Prefere (a) acrescentar
   ao enum compartilhado com uma cláusula append-only em INV-INS-132 e os dois arquivos em
   `FROZEN_PATHS`, ou (b) um enum próprio da nova store, que preserva INV-INS-132 literalmente?
8. **Grupo 10 da gh104 (M-11).** Rodá-lo **antes** do Grupo 2 da gh105, ou reescopá-lo como parte da
   validação conjunta? Como está, a task 2.5 reescreve o teste de que 10.1 depende.
9. **O número-manchete (M-1).** 39.682 = 56,08 % é o teto correto para os 17 órfãos do
   `jca_android`. Confirma a troca nos quatro artefatos — e na eventual redação do artigo?

---

## 6. Limitações

O que esta verificação **não** pode decidir, e o que decidiria:

- **Qualquer coisa que precise de dispositivo.** O R4 (`equals` de `OpenSSLRSAPublicKey`/
  `BCRSAPublicKey`) segue aberto e muda a análise identidade-versus-valor para as leituras de
  `GENERATED_KEY`/`GENERATED_PUBLIC_KEY`. Uma execução por `rv-experiment`/`rv-platform` resolve.
- **Qualquer coisa que precise de weave.** Não há `ajc` na árvore, logo a contradição do delta sobre
  `args(Object)` e primitivos autoboxados (`spec.md:157` versus `:399`) fica sem veredito, e o
  idioma `Object` está validado **só** até o monitor gerado — o caminho `.aj`/dexlib2 sobre um APK
  real continua sendo trabalho do experimento conjunto.
- **A pré-condição bloqueante da própria change.** Se o `UnsatisfiedConstraint` continuar em zero no
  caminho de produção (é zero nos 97.018 eventos publicados, contra 43 no controle AspectJ), a gh105
  está bloqueada e o weaver vira pré-requisito. Nenhuma task mede isso, e nada impede a 8.7 de
  fechar sem medir.
- **Escala das junções.** O custo O(#produtores × #consumidores) de monitores silenciosos em joins
  desconectados não foi medido além do piloto, e a coexistência do spec de junção com o `CipherSpec`
  no mesmo joinpoint — incluindo a deduplicação de relatórios — não foi exercitada por ninguém.
- **Uma campanha.** Todas as magnitudes deste relatório vêm do dataset publicado, que foi medido
  sobre o `jca`. O que os 17 órfãos do `jca_android` realmente sustentam, e o que a fiação realmente
  troca de falso positivo por detecção, só uma campanha sobre o set-alvo mostra.

---

## 7. Nota de método

Nove workstreams independentes, cada um re-derivando das fontes primárias. Onde dois discordaram, o
orquestrador mediu de novo em vez de escolher: (i) a lista de leituras sem acusador — D1 disse "8,
sem nona", D7 disse 9; medido, são **9** (`PBEParameterSpecSpec.c2` passa exatamente no mesmo teste
que já pôs `GCMParameterSpecSpec.c1/c2` na lista: o overload de 3 argumentos não tem gêmeo negativo);
(ii) quantas das 35 cláusulas são fiáveis — três estimativas diferentes convergiram para **25** sob
um censo explícito das duas pontas. Onze afirmações de alto impacto dos subagentes foram conferidas
lendo o arquivo citado antes de entrarem neste relatório; duas tinham a linha errada e estão
corrigidas aqui (`PREDICATE_CALL` é `:516-518`; a proibição de deprecation annotations é
`WORKFLOW.md:254`, não `:262`), com a substância intacta nas duas.

Um resultado que merece ser dito sem rodeio: **a espinha aritmética e o núcleo técnico da change
resistiram a tudo**. O censo do oráculo, o censo de sítios, a decomposição das 134 linhas, os
contadores de órfãos, o mecanismo de supressão do guarda, o modelo híbrido da store, a regularidade
do `ORDER` e o colapso de parâmetro primitivo foram todos re-medidos e todos conferem, vários à
unidade. O que não resistiu foi o `tasks.md` — e o `tasks.md` é reescrevível sem tocar no desenho.
