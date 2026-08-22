# Tarefa 5.1 — a cadeia do IV chega ao consumidor, e o arquivo novo não afirma ordenação

**Data**: 2026-08-22 · **Grupo 5, primeira tarefa** · cláusula #9 do ledger de 36
**Arquivo criado**: `rvsec/rvsec-mop/src/main/resources/jca_android/IvChainJunction.mop`
**A décima quinta forma de passagem**: a que **cria** especificação em vez de editar uma, e cujo
autômato não acusa nada.

---

## O que a tarefa pediu, e o que a árvore respondeu

A 5.1 foi escrita como piloto do **mecanismo B**: `IvChainJunction.mop` cobrindo
`SecureRandom → byte[] → IvParameterSpec → Cipher`, cláusulas **#9 e #12**, com as regras
INV-INS-136(a-d) verdes e as fixtures negativas do piloto viradas pares committados.

A árvore que o Grupo 4 deixou responde outra coisa, e três medições a dizem:

1. **A cláusula #12 (`randomized[iv]`) já estava fiada.** `IvParameterSpec.c1/c2` lê
   `RANDOMIZED` do store com três valores e códigos próprios desde a **4.4**;
   `SecureRandomSpec.next2`/`@match2` escreve desde a **4.5**. Um `mk` acusador seria um
   **segundo acusador da mesma cláusula**, que o `design.md` proíbe em tantas palavras ("the
   ledger routes each clause to exactly one accuser"). Quem estava sem leitor era só a **#9**.
2. **O autômato do piloto não passa no próprio portão dele.** Rodado como está, o `fsm` da
   variante E2 tira **6 achados INV-INS-136(b)**: o gate exige totalidade sobre o alfabeto, e o
   piloto tem `start` sem `mk`/`use`, `got_mk` sem `gen`/`mk` e `ok` sem `gen`/`mk`.
3. **Tornado total, ele deixa de poder acusar por `@fail`.** Escrevi a variante total e li a
   tabela de transição do monitor gerado:

   ```
   Prop_1_transition_gen[] = {2, 1, 2, 3}
   Prop_1_transition_mk[]  = {1, 1, 2, 3}
   Prop_1_transition_use[] = {0, 1, 2, 3}     estado 3 = fail
   ```

   Nenhuma entrada dos estados 0, 1, 2 chega ao 3. Um junção conforme ao gate **nunca falha**, e
   a acusação teria de migrar para um handler de categoria de estado.
4. **E um junção sem chamada de store não fecha nada.** As linhas do `predicate_graph.csv` saem
   do texto `PredicateStore.instance().<op>(Property.X`; um junção que acusa pelo autômato não
   produz linha nenhuma, e o G-PRED2 fica nos mesmos **10** achados, com
   `IvParameterSpec.mop match/PREPARED_IV` intacto.

A variante que de fato fecha a cláusula — uma especificação consumidora de um evento, que lê
`PREPARED_IV` do store no corpo — mede **G-PRED2 10 → 9**, **INV-INS-136 zero achados**, gera, e
tem a lista de parâmetros preservada. **Quatro decisões levadas ao pesquisador; as quatro
recomendações ratificadas** (#49 a #52).

## Por que um arquivo, e não uma edição no `CipherSpec`

A cláusula liga `params`, e `CipherSpec.i2` é `call(public void Cipher.init(int, Key, ..)) &&
args(mode, key, ..)` — um evento só, valendo pelos i3 a i8 da regra, que não liga o terceiro
argumento. Estreitá-lo para ligá-lo tiraria as inicializações de dois argumentos do autômato, e
acrescentar evento não está disponível: o `CipherSpec` declara exatamente 17, que é o teto do
gerador (INV-INS-145). **Uma especificação separada é o único sítio que sobra.**

## A guarda, e o controle que a mede

A #9 é implicação: `part(1,"/",transformation) in {CBC, CTS, CTR, CFB, PCBC, OFB} && encmode == 1`.
Ela é avaliada **no corpo, antes da leitura** (INV-INS-133, D-4). `part(1,…)` sai de
`c.getAlgorithm()`, e duas medições dizem que isso é seguro: `Cipher.getInstance("AES/")` lança
`NoSuchAlgorithmException: Invalid transformation format` antes de existir Cipher nenhum, então o
que chega ao `init` já foi aceito; e `getAlgorithm()` devolve a transformação verbatim
(`"AES/CBC/PKCS5Padding"` → `"AES/CBC/PKCS5Padding"`), medido, não deduzido da documentação.

## O par de traces, medido nos três snapshots

Três traces novas, escritas **antes** da edição (aprendizado 47), replicando inteiras
(`unresolved: []`) contra a pré-imagem, contra a árvore editada **e** contra o controle congelado
(aprendizado 52).

| trace | semente (HEAD) | editado | o que mede |
|---|---|---|---|
| `IvChainJunctionSpec.txt` | silêncio | **silêncio** | a cadeia conforme; o controle que mede zero |
| `IvChainJunctionSpec-unprepared.txt` | 1 relato | **2 relatos** | a acusação nova, e a cascata |
| `IvChainJunctionSpec-decrypt.txt` | 1 relato | **1 relato** | a guarda: `encmode` a 2, antecedente falso |

A sonda é auditável porque as duas últimas diferem **no mesmo carregador**: a não preparada
ganha `IVCHAINJUNCTION-NOBS-00` e a de decrypt não. Se as duas acusassem, a leitura estaria
ignorando a cláusula que diz traduzir.

O `VIOLATED` **não tem programa que o produza hoje**, e isto é registro e não afirmação:
`PREPARED_IV` é escrito em aridade 1 por `IvParameterSpec.@match` e negado em lugar nenhum, então
`validate` só pode responder `SATISFIED` ou `NOT_OBSERVED`. O ramo é escrito assim mesmo, porque
uma predicate ganha `negate` no dia em que a cláusula `NEGATES` de alguma regra for fiada nela, e
uma leitura que tivesse dobrado `VIOLATED` em `NOT_OBSERVED` passaria a relatar uma preparação
retirada como uma não observada. **O lado violador do par é o não observado, declarado e não
fabricado.**

## O custo, por inteiro: a cascata que a 4.4 deixou nomeada

O `IvParameterSpec.mop` escreveu, na 4.4, que o lado satisfeito da escrita ficava em aberto para
"whoever gives it a reader through the store". **Esta tarefa é esse whoever.** `@match` lá escreve
`preparedIV[this]` só para uma construção cuja própria leitura de `randomized[iv]` respondeu
`SATISFIED`, de modo que um iv que a instrumentação não viu randomizar não prepara nada, e o
mesmo limite de alcance passa a ser relatado **duas vezes**: `IVPARAMETERSPEC-NOBS-00` na
construção e `IVCHAINJUNCTION-NOBS-00` no `init`. Medido: a trace não preparada vai de um relato
para dois.

A alternativa — preparar em `NOT_OBSERVED`, para que o limite custe um relato em vez de dois —
faria um `IvParameterSpec` de origem desconhecida satisfazer esta cláusula. É mudança
comportamental sobre decisão ratificada, e foi levada ao pesquisador como opção: **recusada**.

## O harness diferencial

104 traces contra `backup/gh105-preimage/jca_android`, cumulativo:
**67 inalteradas · 21 movidas · 9 introduzidas · 7 removidas**.

As **9 `introduced` não se moveram** — de 9 antes desta passagem para 9 depois. **Esta tarefa não
abre janela nenhuma.** As três traces novas entram como 2 `moved` e 1 `removed`, e nenhuma como
`introduced`.

E a asserção mais barata e mais forte (aprendizado 53): `git diff --stat --
data/gh105/evidence/harness/` sai **vazio**. **Nenhum dos 23 relatórios existentes mudou**; o
único arquivo novo é `f2-IvChainJunctionSpec.md`. As passagens 4.11 a 4.14 mexiam em até dois.

Duas leituras do relatório novo que não são desta tarefa, e que vale nomear porque uma linha do
harness pode ser exatamente a que mede um ganho alheio (achado 46):

- as duas `moved` têm A acusando `IvParameterSpecSpec.c3` com `IVPARAMETERSPEC-CONSTR-00` e B
  acusando `c1` com `NOBS-00` — é a **fusão do gêmeo negado do Grupo 3** mais a separação de três
  valores, testemunhadas por traces que não existiam quando aquilo foi feito;
- a `removed` é a trace **conforme**, e o que a pré-imagem acusava nela era
  `SECURERANDOM-ORDER-00` em `next2`: os dois `nextBytes` seguidos. É o defeito de 12.400 eventos
  que a **4.5** reparou ao pôr `next2` no estado `end`, ganhando aqui uma testemunha nova.

## Os portões

| portão | antes | depois |
|---|---|---|
| G-PRED2 | 10 | **9** — `IvParameterSpec.mop match/PREPARED_IV` sai (`repaired`) |
| INV-INS-136(a)(b)(d) | 0 | **0** |
| G-ORDER | 4 divergências | 4 — o arquivo novo é `skipped` |
| universo enumerado | 214 | **215** |
| `predicate_graph.csv` | 45 linhas | **46** |
| `divergence_record.csv` | 277 hunks | **278**, todos registrados |
| `codes.csv` | 69 códigos | **71** |
| traces | 101 | **104** |
| as quatro suítes | 94 | **94 passam** |

A linha que a baseline imprimiu ao ser reescrita:

```
[G-PRED2] repaired jca_android/IvParameterSpec.mop match/PREPARED_IV
no finding outside the recorded baseline
```

**O `skipped` do G-ORDER aqui é certo, e não é o do achado 53.** Lá o gate pulava o
`KeyManagerFactorySpec` e o pulo escondia uma divergência real contra o ORDER da regra. Aqui não
há ORDER contra o que comparar: regra nenhuma da api30 declara uma ordenação que este arquivo
traduza, porque a ordenação do Cipher é do `CipherSpec`. Conferido, não presumido.

## Os gates estruturais do gh104, e as três falhas que não são minhas

Sobre o monitor gerado, o arquivo novo acrescenta **exatamente +1** a quatro gates:
`G-2a 4→5 · G-2b' 11→12 · G-2c 1→2 · G-2d 2→3`. Os quatro achados são **um só fato de projeto
dito de quatro formas**: esta especificação não carrega afirmação de typestate.

- **G-2a** (linha de transição idêntica): `use` tem `[0, 1]`, porque o autômato não é o que acusa.
- **G-2c** (estado inalcançável): o rv-monitor emite o estado de violação implícito de todo jeito,
  e nada chega nele — lido da tabela, não inferido.
- **G-2d** (o índice mais alto não é a categoria `fail`): o arquivo não declara `@fail`, então o
  índice mais alto não nomeia violação e a leitura do gate não se aplica.
- **G-2b'** já estava coberto pela linha `*`/`*` da allow-list.

Os três primeiros ganharam linha em `data/jca_android/gate_allowlist.csv`, seguindo o precedente
exato do `SecretKeySpec` — que tem os mesmos três — com uma diferença nomeada na razão: **os dele
são herança tolerada até quem revisitar o D-11; os meus são o projeto**, e uma linha de transição
que deixasse de ser a identidade aqui significaria que uma afirmação de typestate entrou por
acidente.

Restam **três falhas G-2a que não são desta passagem**: `PBEKeySpecSpec.f1`, `PBEKeySpecSpec.f2` e
`SecureRandomSpec.g4`. Provado em vez de argumentado (achado 59): regenerei o conjunto **sem** o
arquivo novo e as três continuam lá, com as mesmas linhas `[0, 1, 2, 3]`. São as **três absorções
com laço benigno do Grupo 3** — o `design.md` diz que `g4`, `f1` e `f2` entram como auto-laço
porque o ORDER da regra não tem símbolo para uma chamada que ela recusa —, e um auto-laço em todo
estado *é* uma linha de transição idêntica. Elas estão fora do contrato de CI para `jca_android`
(a suíte estrutural afirma G-2a sobre o controle congelado, não sobre o conjunto), o que é
exatamente por que ninguém as viu. **Registro, não reparo: não são desta tarefa.**

## Três achados sobre o instrumento

1. **O gate INV-INS-136(b) implementa uma regra mais forte que o invariante enuncia, e a mais
   forte torna o `@fail` inalcançável.** O `spec.md` diz "every state a disconnected join can
   reach carries the benign self-loop"; o gate exige transição para **todo** evento em **todo**
   estado. Sob a versão do gate, um junção não pode acusar por `@fail` — medido na tabela de
   transição. Quem escrever o próximo mecanismo B precisa saber disso antes de desenhar o
   autômato: a acusação vai ter de sair de um handler de categoria de estado, e um estado
   absorvente re-acusa a cada evento seguinte.
2. **Um nome de handler com maiúscula nunca casa.** O `RVMErrorChecker` compara
   `handlerName + " condition"` contra a propriedade que o plugin `fsm` registra como
   `stateName.toLowerCase() + " condition"` (`JavaFSM.java:155,177`). `@notPrepared` morre com
   `notPrepared is not a supported state in this logic, fsm`; `@notprepared` gera. E todo nome de
   estado vira categoria automaticamente — o `alias` só é preciso para agrupar mais de um.
3. **O lint balanceia chaves sobre o arquivo inteiro, comentário incluído.** Um `` `}` `` escrito
   em prosa derruba a profundidade e sai como `unbalanced`. É o irmão do achado 32 (o portão do
   INV-INS-130 conta menções em comentário e string) e do aprendizado 43. Custou-me duas
   passagens no lint: a primeira, sessenta `undeclared-symbol` por ter posto um bloco de
   comentário **entre o `ere` e o primeiro `@handler`** — o aprendizado 43 literal, redescoberto
   por não o ter aplicado.

## Recontagem do censo que a tarefa afirma (achado 49)

A 5.1 diz "the pilot's four fixture traces become committed pairs, including the rule-violating
negative fixtures for (a), (b), (d)". A árvore desmente três coisas:

- o piloto tem **três drivers** (`DriverB.java`, `DriverB2.java`, `DriverB3.java`) de três
  cenários cada e **quatro variantes de spec** (E1 a E4) — não quatro traces;
- a regra **(d) não tem modo de falha observável em trace**: ela falha na *compilação* do monitor
  (custo 1 do relatório do piloto; o próprio INV-INS-136 a chama de "compile-time visibility
  fact"). Só (a) e (b) têm fixture negativa possível, e a de (c) é artefato de geração (E4), não
  de trace;
- com a #9 fiada pelo store, (a) e (b) deixam de ter sujeito nesta passagem: não há junção-cadeia
  para violá-las.

## Arquivos

| arquivo | o que mudou |
|---|---|
| `jca_android/IvChainJunction.mop` | **novo**, 151 linhas |
| `jca_android/codes.csv` | +2 códigos, na posição alfabética, sem reordenar |
| `data/jca_android/predicate_graph.csv` | +1 linha (a 46ª), a primeira com `guard` preenchido |
| `data/jca_android/divergence_record.csv` | +1 linha, `hunk=new-file`, kind `junction` (o primeiro uso do kind), CRLF preservado |
| `data/jca_android/gate_allowlist.csv` | +3 linhas (G-2a, G-2c, G-2d) |
| `data/jca_android/gate_baseline.json` | G-PRED2 10→9, universo 214→215 |
| `data/gh104/traces/IvChainJunctionSpec{,-unprepared,-decrypt}.txt` | **novas** |
| `data/gh105/evidence/harness/f2-IvChainJunctionSpec.md` | **novo**; os outros 23 intactos |
| `tests/parity/test_gh105_predicate_gates.py` | dois censos 14→15; o teste do G-PARAM passa a afirmar o `skip` |

**Sobre o G-PARAM**: o teste comparava 23 e passava, porque o arquivo novo é `skipped` — o
`results/gh51_e2e_test/monitors` é fixture anterior a esta change e não tem `.rvm` para ele. Um
`skip` silencioso esvaziaria a promessa do teste justamente para os arquivos para que ele foi
escrito, que é o achado 56 em outro sítio. Agora o teste **afirma o pulo pelo nome**, de modo que
um segundo arquivo sem monitor o quebra em vez de sumir na contagem. Que o junção fatia por
`Cipher` foi lido do monitor gerado (`IvChainJunctionSpec_c_Map`, `CachedWeakReference`), não
inferido do gate.

## O que fica para o Grupo 5

- A **5.8** vai querer a mesma guarda para `preparedGCM` (`part(1,…) in {GCM}`, ledger #10) e o
  mesmo padrão de sítio. `GCMParameterSpecSpec.@match` já escreve `PREPARED_GCM`; falta o leitor,
  e ele esbarra no mesmo teto de 17 do `CipherSpec`. **Este arquivo é o precedente**, e a decisão
  de nome fica então em aberto de novo: um segundo consumidor do Cipher cabe aqui dentro ou pede
  arquivo próprio.
- `CipherTransformationUtil.mode("AES/")` lança `ArrayIndexOutOfBoundsException` — medido. É
  inalcançável por esta rota, porque `getInstance` recusa a transformação antes, mas é defeito
  latente do `rvsec-core` e não foi reparado aqui.
