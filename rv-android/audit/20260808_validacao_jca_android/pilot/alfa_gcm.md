# ALFA — parecer piloto: `GCMParameterSpecSpec.mop` ↔ `GCMParameterSpec.cryptsl` (api30)

Agente Alfa · 2026-08-08 · rodada-piloto, sem leitura cruzada.

**Artefatos (SHA-256, 16 hex):** `GCMParameterSpecSpec.mop` `18c84f8f64f3b5dd` (byte-idêntica à homônima do conjunto congelado `jca` — manifesto Fase 0, teste da tese D-S10) · `GCMParameterSpec.cryptsl` `26474144cee2ab7f`.

**Limitação declarada:** linguagem MOP modelada da sintaxe `.mop`; autômato efetivo e geração são de outro agente. Duas hipóteses sintáticas ficam abertas (GCM-01, GCM-08) e **condicionam** os PASS de linguagem.

## 1. Log científico (resumo)

1. **Q:** o `ere: c1 | c2` corresponde ao ORDER `Cons`? **Achado prévio:** os **dois** eventos declarados chamam-se `c1` (linhas 23 e 34) e **não existe evento `c2`** — o `ere` referencia um símbolo não declarado. **T:** inspeção do validador do gerador (`javamop/output/MOPErrorChecker.java`): não valida símbolos da propriedade contra eventos declarados. **H-GCM:** eventos homônimos disparam o mesmo símbolo; `c2` nunca dispara; linguagem efetiva `{c1}`. **R:** sob H-GCM, dupla inclusão VALE (script); sem H-GCM confirmada, INCONCLUSIVA. **D:** delegar geração ao agente executável.
2. **Q:** CONSTRAINT (tLen) e REQUIRES (randomized) preservam report? **R:** ambos vivem no `condition()` do **creation event** — violação ⇒ evento não dispara ⇒ **monitor nunca existe** ⇒ nenhum report desta spec, nunca (o `@fail` é código morto). Acusação só surge, deslocada e desatribuída, se o objeto chegar a um `Cipher.init` em modo GCM. **D:** INCORRETA (FN terminal realizável).

## 2. Matriz normativa

### 2.1 OBJECTS (4)

| Objeto | Binding MOP | Status |
|---|---|---|
| tLen | `tagLen` em ambos os eventos | FIDELIDADE_DEMONSTRADA |
| src | `src` em ambos | FIDELIDADE_DEMONSTRADA |
| offset, len | bound no 2º evento | FIDELIDADE_DEMONSTRADA |

### 2.2 EVENTS / α

| CrySL | MOP | Status | Nota |
|---|---|---|---|
| c1: `GCMParameterSpec(tLen, src)` | evento `c1` (linha 23), `after returning`, ctor `(int, byte[])` | FID (binding) | — |
| c2: `GCMParameterSpec(tLen, src, offset, len)` | evento declarado **também como `c1`** (linha 34), ctor `(int, byte[], int, int)` | **INCONCLUSIVA** (ALFA-GCM-01) | nome duplicado + símbolo `c2` órfão no `ere`; sob H-GCM a fusão α({c1,c2})=Cons é preservada; se o gerador rejeitar, a spec não constrói |
| Cons := c1 \| c2 | `ere: c1 \| c2` | idem | `c2` sem produtor ⇒ ramo morto |

### 2.3 ORDER

| Claim | Cláusula | Status | Evidência |
|---|---|---|---|
| ALFA-GCM-02 | `Cons` (exatamente um construtor por objeto) | PASS **condicional a H-GCM** | produto BFS sem separador (`alfa_automata_output.txt`); paramétrico por `s`: cada objeto vê exatamente um construtor, re-ocorrência é irrealizável |

### 2.4 CONSTRAINTS / REQUIRES

| Claim | Cláusula | Tradução | Status | FP/FN |
|---|---|---|---|---|
| ALFA-GCM-03 | `tLen in {128,120,96,112,104}` | `validLengths` = {96,104,112,120,128} — mesmos 5 valores — mas em `condition()` do creation event | **INCORRETA** (mecânica), valores FID | violação ⇒ supressão silenciosa: sem monitor, sem `UnsatisfiedConstraint`, `@fail` inalcançável. FN terminal realizável: `new GCMParameterSpec(64, rnd)` nunca usado num Cipher ⇒ **zero** report; usado ⇒ report do CipherSpec sem atribuição a esta regra/cláusula. Mesma família que GH101 removeu de outras specs (D-S9); aqui persiste por D-S10 (freeze byte-a-byte) |
| ALFA-GCM-04 | REQUIRES `randomized[src]` | `validate(RANDOMIZED, src)` no mesmo `condition()` | **INCORRETA** (mesma mecânica) | writer existe (`SecureRandomSpec:121`, nextBytes); identidade de `byte[]` compatível com o store por identidade |
| ALFA-GCM-05 | *(sem contraparte CrySL)* `offset>=0 && len>=0 && src.length>=offset+len` no 2º evento | condições **adicionadas** | DIVERGÊNCIA_EQUIVALENTE (INFERIDO) | o construtor lança `IllegalArgumentException` exatamente nesses casos e o evento é `after returning` ⇒ condições sempre verdadeiras quando o evento dispara; equivalência depende do `android.jar` API 30 real (verificação de captura: Beta) |

### 2.5 ENSURES

| Claim | Cláusula | Tradução | Status |
|---|---|---|---|
| ALFA-GCM-06 | `preparedGCM[this]` | `@match`: `setProperty(PREPARED_GCM, spec)`; `spec` é o próprio `s` (instance var por monitor paramétrico); leitor: `CipherSpec.reportUnpreparedParams` via `requiresPreparedGcm` | FIDELIDADE_DEMONSTRADA — acoplamento do ENSURES às constraints (só marca quando o `condition()` passou) espelha a semântica CrySL de predicado garantido apenas em uso conforme |

### 2.6 Sintaxe/geração (transversal)

| Claim | Achado | Status |
|---|---|---|
| ALFA-GCM-08 | `List`/`Arrays` usados sem `import` no `.mop` (imports: linhas 3-7). No modo agregado, `java.util.List` viria de `MessageDigestSpec`; **nenhum** spec de `jca_android` importa `java.util.Arrays` | INCONCLUSIVA — se o aspecto gerado não suprir o import, não compila; a evidência de produção do conjunto `jca` (byte-idêntico) sugere que compila, mas não localizei o mecanismo. Teste executável: outro agente |
| ALFA-GCM-07 | byte-identidade com `jca` congelado confirma D-S10 como freeze **byte-a-byte, não comportamental**: os defeitos GCM-01/03/04 são pré-existentes e não foram alcançados pelas correções da gh101 | OBSERVADO_EM_ARTEFATO (nota, sem severidade própria) |

## 3. Busca ativa de FP/FN

| Par de traces | Difere só em | Regra | Spec | Veredito |
|---|---|---|---|---|
| `new GCMParameterSpec(128, rndMon)` × `new GCMParameterSpec(64, rndMon)` | tLen | 2º viola c/ constraint | 2º: silêncio total | **FN** |
| `new GCMParameterSpec(128, rndMon)` × `new GCMParameterSpec(128, constante)` | randomized[src] | 2º viola REQUIRES | 2º: silêncio total | **FN** |
| os dois acima + `cipher.init(1,k,spec)` AES/GCM | idem | idem | report deslocado (`UnsatisfiedConstraint` do **CipherSpec**) | FN de atribuição (diagnóstico) |
| construtor 4-args com offset inválido | constraint extra | regra silente (não tem a cláusula) | evento não dispara (ctor lança antes) | concordam (equivalente) |

## 4. Veredito preliminar de Alfa (dimensões 1, 3, 4, parte da 6)

**INCONCLUSIVA, com defeitos demonstrados**: a linguagem do ORDER é trivialmente preservável e o ENSURES é fiel, mas (i) o par c1-duplicado/`c2`-órfão impede afirmar sem o artefato gerado que a spec constrói o autômato pretendido, e (ii) CONSTRAINT e REQUIRES são **suprimidos** em vez de reportados — FN terminal realizável e perda total de atribuição diagnóstica. `INCONCLUSIVE` não vira aprovação (pré-registro §3); os FN de supressão valem independentemente de (i).
