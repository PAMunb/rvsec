# Tarefa 11.3 — os instrumentos apontam para o oráculo único

**Data**: 2026-08-26 · **Grupo**: 11 (F8, D-16) · **Espécie**: troca de insumo, medida dos dois lados
**Oráculo**: `RVSec-replication-package/tools/rules/` (49 regras, sha256 `d7bcc019…`)
**Insumos retirados**: `MetaCrySL/generated/api30/` e `data/jca_android/order_alphabet_map.csv`

## 1. O que a tarefa fez

Quatro instrumentos liam a api30. Depois desta tarefa nenhum lê:

| instrumento | o que mudou |
|---|---|
| `scripts/gh105_order_gate.py` | `DEFAULT_RULES` passa a ser a cópia expert; `DEFAULT_MAP` passa a ser o `order_alphabet_map_expert.csv`; as duas mensagens de veredito e o docstring do `accepted_by` dizem `the expert ORDER` |
| `scripts/gh104_gates.py` | `--value-crysl` é absorvido pelo `--crysl` — um único diretório para o G-2, o G-CONF e tudo o mais |
| `scripts/gh105_spec_gates.py` | o G-FORB lia dois catálogos e passa a ler um; `--api30-rules` sai, `--expert-rules` vira `--rules` |
| `scripts/gh104_message_gate.py` | a linha de uso nomeava `generated/api30` como o valor do `--crysl` |

**O mapa anda junto com as regras.** Apontar o `--rules` para a cópia expert e deixar o mapa da
api30 no lugar compararia símbolos expert contra âncoras api30 — uma comparação mal chaveada que
o portão leria como um conjunto de defeitos de ordenação. É por isso que os dois defaults trocam
na mesma passagem, e é por isso que a 11.2 existiu antes desta.

O `order_alphabet_map.csv` fica em disco, com o cabeçalho reescrito para dizer que **nada o lê**.
Fica pela razão que todo registro superado desta mudança fica: é o artefato sobre o qual os
vereditos pré-D-16 foram computados, e a evidência que os cita (`f1-order-gate-precedence.md`,
`f2-*.md`, `f3-OrderMapComplete.md`) resolve sobre ele (INV-INS-118). Não é fallback: não existe
caminho de código que o alcance.

## 2. O que a troca moveu, medido dos dois lados

### 2.1 `jca_android` sob o `gh104_gates.py`: nada

Mesmo monitor, os dois catálogos, nove portões:

```
--crysl api30   {G-2:0, G-2a:12, G-2b':19, G-2c:2, G-2d:3, G-6':0, G-ERE:0, G-CONF:0, G-PRED:0}  ok=True
--crysl expert  {G-2:0, G-2a:12, G-2b':19, G-2c:2, G-2d:3, G-6':0, G-ERE:0, G-CONF:0, G-PRED:0}  ok=True
```

`skipped` vazio nos dois; G-PRED em `superseded` nos dois. O conjunto migrado não sente a troca
neste portão, o que era esperado: o G-CONF já lia a cópia expert desde a D-15, e o G-2 do
`jca_android` não tem órfão nenhum a classificar.

### 2.2 O controle congelado `jca`: dois números se movem, e é a mesma causa

| medida | api30 | expert |
|---|---|---|
| `G-2` (`orphan-without-clause`) | 3 | **2** |
| `G-2` notas (`orphan-with-clause`) | 15 | **16** |
| órfãos brutos | 18 | 18 |
| `wrong-error-type` (portão de mensagem) | 3 | **4** |

Os dois movimentos são **o mesmo sítio**: `SecretKeySpecSpec.c3`, cujo `condition()` testa
`keyAlgorithm` e `keyMaterial`.

- A `MetaCrySL/generated/api30/SecretKeySpec.cryptsl` declara em CONSTRAINTS **uma única cláusula**,
  `length(keyMaterial) >= off + len` — não diz nada sobre nenhum dos dois objetos que a guarda
  testa. Nenhuma cláusula respondia pelo evento, então o G-2 o chamava de falha e o portão de
  mensagem não tinha família de cláusula para comparar contra o `ErrorType`.
- A `RVSec-replication-package/tools/rules/SecretKeySpec.crysl:18,20` declara
  `keyAlgorithm in {"AES", "HmacSHA256", "HmacSHA384", "HmacSHA512"}` e
  `neverTypeOf[keyMaterial, java.lang.String]`. Com elas o evento é `orphan-with-clause` — sai dos
  *hits* e entra nas notas — e o sítio `SecretKeySpecSpec.mop:48` ganha família
  `CONSTRAINTS-value`, contra a qual o seu `UnsatisfiedConstraint` é o `ErrorType` errado (um
  `in {...}` sobre `String` pede `UnsafeAlgorithm`).

Nada do conjunto congelado foi tocado: 3 + 15 e 2 + 16 são os mesmos 18 órfãos brutos, e é por isso
que o `JCA_RAW_ORPHANS` é afirmado ao lado do split. **Isto é reclassificação de portão, não
mudança do que o monitor acusa** — o `jca` continua byte a byte o que a tarefa 8.2 prova. E é a
D-15 aparecendo na sua forma mais nítida: a regra gerada tinha *perdido* a cláusula de algoritmo
que a fonte tem, e a perda produzia dois falsos vereditos de portão sobre o controle congelado.

O `wrong-error-type` do `SecretKeySpecSpec.mop:48` **não se repara**: o `jca` está congelado. Fica
fixado no arnês de paridade ao lado dos outros três, com o motivo escrito.

### 2.3 O G-FORB perde metade da contagem e nenhum veredito

```
antes   G-FORB checked 18  failed 0  allowlisted 12  skipped 14
depois  G-FORB checked  9  failed 0  allowlisted  6  skipped  8
```

Exatamente a metade, porque a segunda leitura produzia uma duplicata de cada verificação e de cada
skip. Conferido cláusula a cláusula: nas duas regras que este conjunto tem `.mop` os dois catálogos
dizem o mesmo (`PBEKeySpec(char[])` e `PBEKeySpec(char[],byte[],int)` proibidos; `getDefault()`
proibido). Onde diferem — a api30 proíbe `on(java.lang.String)` no `DigestOutputStream` onde a
expert proíbe `on(boolean)`, mais um defeito da cadeia gerada — a regra não tem `.mop` em conjunto
nenhum e a cláusula é skip declarado dos dois lados.

### 2.4 O G-ORDER sai 1, com seis achados medidos

```
antes   14 passed, 0 failed, 8 allow-listed, 2 skipped
depois  13 passed, 6 failed, 3 allow-listed, 2 skipped
```

É o estado que a 11.2 já tinha medido e escrito. Os seis se separam em dois grupos, e **nenhum é
regressão**:

| espec | testemunha | dono |
|---|---|---|
| `CipherOutputStreamSpec` | `c1 cl1` (era `c2 c`) | 11.4 — rechavear a linha do allowlist |
| `KeyGeneratorSpec` | `g1 g1 gk1` (era `g1 g1 gk`) | 11.4 |
| `SSLContextSpec` | `g1 i1 se1 se1` (era `g1 Init se1 se1`) | 11.4 |
| `SecretKeySpec` | `d1` (era `d`) | 11.4 |
| `KeyPairSpec` | sequência vazia | **11.6** — decisão do pesquisador |
| `MacSpec` | `g1 i1 f1` | **11.6** — decisão do pesquisador |

Os quatro primeiros são a mesma divergência com a testemunha escrita nos símbolos do outro
catálogo; o allowlist chaveia pelo texto da testemunha, então a linha deixa de casar sem que nada
tenha mudado no conjunto. Uma quinta linha do allowlist **deixa de ser necessária**: o
`CipherInputStreamSpec` passa a passar, porque a testemunha que ela perdoava vinha do construtor
de um argumento que só a api30 declarava.

## 3. As fixtures de paridade

**185 passed / 3 failed** — a linha de base, com as mesmas três falhas pré-existentes de outras
frentes (`test_baseline_not_older_than_jar`, `test_repo_is_clean`, `test_real_gator_json_parses_with_complete_true`).

O que foi reancorado, e como:

- `test_gh104_structural_gates.py`: `CRYSL` passa a ser a cópia expert e `VALUE_CRYSL`/`_value_crysl`
  somem com o flag; `JCA_BASELINE["G-2"]` 3 → 2 e as notas 15 → 16, com os 18 brutos afirmados ao
  lado; `JCA_MESSAGE["wrong-error-type"]` 3 → 4, e o teste passa a fixar **os sítios** e não só a
  contagem — um total que ficasse em quatro enquanto um achado fechasse e outro abrisse relataria o
  mesmo número para um conjunto diferente de defeitos.
- `test_gh105_predicate_gates.py`: `ORDER_MAP` passa ao mapa expert; `Cipher.cryptsl` →
  `Cipher.crysl` e `SecureRandom.cryptsl` → `SecureRandom.crysl`; o alfabeto esperado do
  `SecureRandom` ganha o split `nI`/`nIR` que a regra expert faz e a gerada não fazia; o
  `KeyPairGeneratorSpec` afirma `i1` onde afirmava `i3` — a permutação de quatro vias.
- **Os seis achados são fixados por nome e testemunha**, na constante `OPEN_ORDER_DIVERGENCES`, e
  não tolerados por contagem. Um sétimo reprova o `test_inv_ins_138_gorder`; um dos seis fechando
  sem o registro andar junto também reprova. O que a invariante deixou de fazer é ler uma
  testemunha mal chaveada como convergência.
- O caso de saída 0 do `main()` passou a construir o allowlist que cobre os seis, em vez de ler o
  da árvore: com seis abertos o arquivo vivo produz saída 1, e o caso não conseguiria mostrar a
  tradução de uma passagem limpa. A saída 1 deixou de precisar de mutante — o arquivo vivo a produz.
- O caso do mutante compara os achados contra os da passagem sã, em vez de contra um literal: a
  diferença entre as duas passagens é o único campo alterado, e a asserção passa a dizer isso
  diretamente. O `CipherSpec` continua sendo o sujeito porque a sua linha perdoa `g1 i1 u1` nos dois
  catálogos — é o que mantém o caso medindo o portão e não a troca.

## 4. Bateria completa, depois da troca

```
gh104_gates                 exit=0     gh105_predicate_graph       exit=0
gh104_divergence_record     exit=0     gh105_order_gate            exit=1  ← os seis, 11.4/11.6
gh104_message_gate          exit=0     gh105_spec_gates            exit=0
gh104_mop_lint              exit=0     gh105_expert_ledger         exit=0
gh101_conformance_check     exit=0     gh105_expert_alphabet       exit=0
```

## 5. O que continua lendo a api30, de propósito

O contrato "nenhuma CLI mantém caminho de código api30" vale para os instrumentos que decidem sobre
o conjunto vivo. Três leitores permanecem, e cada um por uma razão declarada:

- **`scripts/gh101_conformance_check.py`** — guarda o conjunto **arquivado**
  `jca_android_bug_predicate/`, derivado da api30, e a INV-INS-118 manda o veredito resolver sobre o
  artefato em que foi computado. O seu `--specs` default nomeia o arquivo, não o sucessor.
- **`scripts/gh105_expert_ledger.py` e `scripts/gh105_expert_alphabet.py`** — os instrumentos de
  derivação das 11.1 e 11.2. Leem os dois catálogos **por construção**: é o que produz a tabela de
  delta. Um delta com um lado só não é delta.
- A extensão `.cryptsl` no `RULE_EXTENSIONS` do `gh104_gates.py`, pelo primeiro motivo: é o portão
  que o gh101 chama sobre o conjunto arquivado. Não é fallback — o `--crysl` nomeia um diretório e
  todos os portões leem esse.

## 6. Uma dívida encontrada e entregue à 11.4

O `scripts/gh104_baseline.py:1912` emite, no relatório que gera, a frase *"This is what makes
`MetaCrySL/generated/api30/*.cryptsl` **the** oracle and not one option among several"* — voz
presente, afirmando autoridade que a D-16 retirou. Não é caminho de código (o script não lê regra
nenhuma) e não é mensagem de violação (o escopo da 11.8 são as strings de report do `.mop`): é
narração de registro, que é matéria da **11.4**. Fica anotado aqui para que a 11.4 não tenha de
redescobri-lo. As outras duas menções do mesmo arquivo (`:775`, `:1769`) descrevem contra o que a
medição de agosto foi feita, em contexto passado, e são exatas como história.
