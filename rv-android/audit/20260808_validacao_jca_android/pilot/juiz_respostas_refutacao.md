# JUIZ — Respostas à refutação (REF-01..REF-13)

Juiz · 2026-08-08. Alvo: `pilot/refutacao_parecer.md`. Protocolo §15: decisão final só após
resposta a cada objeção. Nenhum gate ou critério pré-registrado é alterado aqui; o que exige
mudança de protocolo vira proposta de desvio (lista consolidada na "Decisão final
pós-refutação" de `juiz_sintese.md`). Correções aplicadas em
`juiz_claims_resolvidos.csv` (rev. 2) e refletidas no score re-somado.

Registro prévio (conferência (e) do mandato da refutação): a premissa "70 declarados × 72
resolvidos" foi **falsificada pelo revisor** — os CSVs dos agentes têm 34+20+18 = 72 claims,
em bijeção exata com o CSV do juiz (`refutacao_parecer.md:40-43`). Nada a corrigir; fica
registrado que a suspeita foi testada e não se sustentou.

## REF-01 — ALFA-CIP-17/18: registro de omissão existe — **ACEITA**

Verifiquei o fonte apontado: `openspec/changes/gh101-jca-spec-conformance/tasks.md:117`
(tarefa 4.11, `[x]`) registra explicitamente, **com razão**, `noCallTo(IWOIV)` e `callTo(iv)`
como fora de escopo, inclusive a nota de recuperabilidade via o mesmo `instanceof` do
init-3. Minha resolução pesquisou apenas `data/gh101/` e conflacionou a citação de Gama
(`gama_sinergia.md:57`, "tarefa 4.11") com o comentário do `.mop` — erro meu de busca,
exatamente do tipo que o meu próprio ajuste 5 pretendia prevenir. Correções aplicadas:

- **ALFA-CIP-17**: FAIL mantido; classificação corrigida de "OMITIDA (crítica; sem registro
  algum)" para **OMITIDA com registro deliberado** (`tasks.md:117`). Severidade **crítica
  mantida**, agora fundada só no que a sustenta: FN realizável (decrypt CBC-família via
  init sem IV não reporta; nenhum código consome a distinção IWOIV×IWIV) — o critério §4
  ("FP ou FN demonstrável em trace realizável") independe de registro. Registrado ≠
  aprovado: a omissão registrada continua bloqueando aderência total
  (`modelo_semantico.md:98-99`).
- **ALFA-CIP-18**: FAIL mantido; classificação corrigida para **OMITIDA com registro
  deliberado** (`tasks.md:117` — não apenas o comentário do spec); severidade major mantida
  (FN realizável, mas cláusula de valor semântico questionável, candidata a redução formal
  de escopo — como Alfa já ponderava).
- Matriz #14 da síntese corrigida na decisão final; a busca padronizada de registro passa a
  cobrir `data/gh101/` **e** `openspec/changes/gh101-*/` (tasks/design/proposal) — absorvida
  no ajuste 5.

Sem efeito em resolução (FAIL), em G4 (FAIL por c4/c5–c8/14a além destes) ou em score.

## REF-02 — ALFA-GCM-05: "COMPROVADA (INFERIDO)" — **ACEITA**

O rótulo era autocontraditório: DIVERGÊNCIA_EQUIVALENTE_COMPROVADA exige demonstração
(`modelo_semantico.md:94-99`) e a linha Binding/cláusula do pré-registro
(`pre_registro.md:41`) manda INCONCLUSIVE quando a determinação exige execução não
realizada. A equivalência (condições extras sempre-verdadeiras sob `after returning` porque
o ctor lança `IllegalArgumentException` nos mesmos casos) depende do comportamento do
construtor no android-30 em execução — não executado por ninguém. **ALFA-GCM-05:
PASS → INCONCLUSIVE**; teste discriminante padronizado (harness JVM com casos-limite dos
dois ctors contra o android-30 congelado) adicionado ao pacote D-piloto-2. Efeito no score:
bindings perde 1 PASS do denominador.

## REF-03 — BETA-SET-03: PASS por leitura em claim de toolchain — **ACEITA**

A objeção aplica contra mim a regra que eu mesmo enunciei ("alegação só de leitura não
fecha claim de toolchain", `juiz_sintese.md:4-5`). O claim foi fechado PASS com evidência
exclusivamente de leitura (`MonitorInvokeBuilder.java:69-78` etc.) e com a metade decisiva
(o que é tecido de fato no DEX) declaradamente NÃO_VERIFICADA. O re-escopo "no escopo
código" divulgava a limitação, mas convertê-la em PASS pleno de denominador é inconsistente.
**BETA-SET-03: PASS → INCONCLUSIVE** (a leitura do emissor vigente permanece registrada
como evidência favorável; o fechamento espera o weave dexlib2 + baksmali diff de G6, já
previsto). Efeito no score: toolchain perde 1 PASS do denominador.

## REF-04 — Assimetria 14a × 14b — **ACEITA** (na direção de re-elevar 14b)

A inconsistência era real: os dois claims são divergências textuais provadas cujo impacto
comportamental depende de semântica externa não testada (`part()` sobre componente ausente;
case-insensitivity do JCA), e eu as resolvi em direções opostas. Das duas saídas que o
revisor aponta, a correta pelo pré-registro é **re-elevar 14b a FAIL**, não rebaixar 14a:
o critério de constraints (`pre_registro.md` §3, linha Binding/cláusula + tabela) dá FAIL
quando o conjunto de valores traduzido difere do da regra, e o oráculo entra **cru**
(`pre_registro.md:22-25`) — o folding aceita strings que o conjunto cru rejeita, fato
provado por leitura de `AndroidCipherTransformationUtil.java:251-253`. Equivalência
comportamental **não provada** não converte um FAIL textual em INCONCLUSIVE; ela fica como
incerteza residual registrada (e o teste D-piloto-2 pode, na rodada das 23, reclassificar o
defeito para DIVERGÊNCIA_EQUIVALENTE_COMPROVADA). O mesmo padrão sustenta 14a como FAIL.

- **ALFA-CIP-14b: INCONCLUSIVE → FAIL**, INCORRETA (minor; contra o oráculo cru;
  equivalência JCA possível, não testada — incerteza residual explícita).
- **ALFA-CIP-14a**: mantido FAIL/INCORRETA (major), com a mesma estrutura de incerteza
  declarada. Consistência restaurada com uma única regra: divergência textual provada =
  FAIL sob oráculo cru; equivalência não provada = incerteza registrada, nunca rebaixamento.

## REF-05 — ALFA-CIP-15/16: minor por mitigação inferida — **ACEITA**

Verifiquei: a tarefa 4.11 registra apenas `noCallTo`/`callTo`/`neverTypeOf`; c4 (encmode) e
c5–c8 (comprimentos) não constam de `data/gh101/` nem do ledger da change. Pela letra do
§4 (`pre_registro.md:56-57`), OMITIDA sem registro de omissão deliberada é **major**; o
rebaixamento a minor apoiava-se em mitigação pela API marcada por mim mesmo como "INFERIDA".
**ALFA-CIP-15 e ALFA-CIP-16: severidade minor → major** (resoluções FAIL inalteradas; sem
efeito aritmético no score; efeito real na contabilidade de pendências de G13). O harness
proposto pelo revisor (`init(7, key)` e os 4 casos de comprimento) entra na lista de testes
padronizados da rodada das 23.

## REF-06 — Sensibilidade da atribuição claim→dimensão e claims de conjunto — **ACEITA PARCIALMENTE**

Aceito integralmente a qualificação: (i) a atribuição claim→dimensão não é pré-registrada e
fenômenos únicos entram como FAIL em mais de uma dimensão, enquanto a metade FAIL de
BETA-GCM-02 foi alojada em GAMA-GCM-01 — decisão minha, coerente mas discricionária;
(ii) 12 claims SET-wide entram no denominador de um score apresentado como "do piloto
(2 specs)" — isso agora está declarado na decisão final, com a sensibilidade estimada
(±≈2 pontos; com REF-02/03/04 aplicadas o total move de 58,0 para 55,9). Rejeito apenas a
implicação de refazer a atribuição ex post nesta rodada: trocar a regra depois de ver o
resultado seria exatamente o vício que o pré-registro proíbe. A regra de atribuição e o
tratamento de claims de conjunto ficam propostos como **desvio D-piloto-4** (texto na
decisão final), a fixar ANTES da rodada das 23. O número re-somado é publicado com ambas as
ressalvas no rótulo.

## REF-07 — GAMA-CIP-07: rebaixamento com raciocínio não executado — **ACEITA PARCIALMENTE**

A resolução INCONCLUSIVE permanece — é o estado pré-registrado correto: o próprio Gama
rotulou o claim INFERIDO/hipotético, e a linha de diagnóstico do pré-registro dá
INCONCLUSIVE para dano "não determinável por leitura + execução" (nenhum harness exercitou
a serialização). Aceito a objeção quanto ao **fundamento**: meu argumento adicional
("transformation com `\n` não sobrevive ao `getInstance`") era plausível porém não
executado, e não pode carregar a decisão — foi rebaixado a hipótese no CSV; a justificativa
oficial do INCONCLUSIVE passa a ser somente o critério pré-registrado (dano não demonstrado;
fato do escape comentado registrado). Assimetria probatória reconhecida e corrigida na
redação; direção da resolução inalterada (INCONCLUSIVE não favorece a spec: fica fora do
denominador e impede score completo).

## REF-08 — Ameaça A1 sem estado normativo; dimensão 5 sem cobertura — **ACEITA PARCIALMENTE**

Mantenho BETA-CIP-10 como PASS: o claim, como formulado, afirma o mecanismo
(todo evento é creation event) — observado e correto. Aceito o resto integralmente:
(i) o qualificador volta ao CSV (classificação "FIDELIDADE_DEMONSTRADA … com ameaça A1
registrada e não adjudicada — FP condicional, pendência G10"), em vez de pendência
apenas; (ii) a lacuna estrutural é real e passa a ser declarada: a dimensão 5 do modelo
semântico (paramétrica/ciclo de vida) **não produziu claims próprios no piloto** e isso
não constava da declaração de escopo — corrigido na decisão final, que também retifica a
frase "o piloto validou o protocolo no essencial" para registrar essa lacuna; (iii) ajuste
novo para a rodada das 23: claims obrigatórios de ciclo de vida por spec (interleaving,
identidade, creation) com a dimensão 5 declarada no escopo de cada rodada. Sem efeito
aritmético (o revisor o concede).

## REF-09 — §2.2 incompleto — **ACEITA**

O diff do revisor está correto: BETA-GCM-02 (`FAIL(texto)/PASS(linguagem)`→PASS, com a
metade FAIL migrada para GAMA-GCM-01), BETA-SET-03 (`PASS(codigo)/NAO_VERIFICADO`→PASS),
BETA-SET-05 (`PASS(sem efeito no piloto)`→PASS) e BETA-CIP-10 (`PASS-com-ameaca`→PASS)
foram normalizações de posições qualificadas que não constavam da tabela de mudanças. A
tabela consolidada na decisão final lista **todas** as divergências posição-do-agente ×
resolução-do-juiz, incluindo re-escopos; dois desses quatro casos mudaram de novo nesta
rodada (BETA-SET-03 → INCONCLUSIVE por REF-03; BETA-CIP-10 requalificado por REF-08), o
que reforça o valor da objeção.

## REF-10 — Completude do BFS do GCM não argumentada — **ACEITA (registro)**

O PASS está correto e o revisor não o contesta; o registro estava incompleto. Argumento de
completude, agora registrado: a busca poda por estados visitados do produto
(`alfa_automata_check.py:192`), logo é exaustiva sobre o espaço de estados alcançável
quando o horizonte (12) excede o diâmetro do produto; para o GCM o produto tem ≤ 9 estados
(3 efetivos do MOP × ≤ 3 do autômato de referência de `Cons`), diâmetro < 12 — a busca é
decisão, não amostragem. Ajuste para a rodada das 23 (já proposto pelo revisor, adotado):
o script passa a imprimir |estados do produto| e diâmetro em toda verificação de inclusão.

## REF-11 — "Duas rotas de geração independentes" — **ACEITA (retórica corrigida)**

Correto: Beta e Gama usaram os mesmos jars, a mesma spec e o mesmo modo; a identidade dos
artefatos evidencia **determinismo do gerador** (que Beta já provara por hash entre modos),
não replicação independente. A evidência decisiva para H-GCM é o conteúdo do artefato —
uma geração bastaria. A frase da síntese §0.1 fica retificada na decisão final; nenhuma
resolução se apoiava na duplicação como força probatória adicional (confirmado pelo
próprio revisor).

## REF-12 — android-36 do Docker não triangulado — **ACEITA PARCIALMENTE**

Fato: Beta triangulou 30×37.0 (host); o Docker resolve android-36 (`fase0/manifesto.md:54-58`)
e ninguém mediu 36. As resoluções PASS de BETA-CIP-04/BETA-GCM-03 permanecem — o gate de
captura é contra o android-30 real (o oráculo), que **foi** medido; a triangulação 37.0 era
evidência extra sobre o defeito G10. Corrijo a redação: "insensível ao G10" passa a
"insensível ao G10 **no host** (30×37.0); android-36 do container não triangulado —
pendência", registrada no CSV de BETA-CIP-04, BETA-GCM-03 e BETA-SET-05. Teste adotado
para a rodada das 23: mesma mesa contra o `android-36/android.jar` do container.

## REF-13 — Coluna `classificacao` não normalizada — **ACEITA**

O CSV rev. 2 normaliza a coluna aos seis estados da matriz normativa
(`modelo_semantico.md:92-95`) — todo claim carrega exatamente um de
FIDELIDADE_DEMONSTRADA / DIVERGÊNCIA_EQUIVALENTE_COMPROVADA /
LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA / OMITIDA / INCORRETA / INCONCLUSIVA, com detalhes em
parêntese. Claims de medição de toolchain/gerabilidade que verificam a cadeia (não uma
cláusula CrySL) entram como FIDELIDADE_DEMONSTRADA da dimensão correspondente quando PASS
e INCORRETA (defeito de toolchain) quando FAIL — convenção declarada no cabeçalho lógico
do CSV e proposta para pré-registro da rodada das 23 junto com D-piloto-4.

## Saldo das respostas

| Objeção | Resposta | Efeito material |
|---|---|---|
| REF-01 | ACEITA | classificação/evidência de ALFA-CIP-17/18 corrigidas (registro existe); severidades mantidas por fundamento correto |
| REF-02 | ACEITA | ALFA-GCM-05 PASS→INCONCLUSIVE |
| REF-03 | ACEITA | BETA-SET-03 PASS→INCONCLUSIVE |
| REF-04 | ACEITA | ALFA-CIP-14b INCONCLUSIVE→FAIL (consistência com 14a sob oráculo cru) |
| REF-05 | ACEITA | ALFA-CIP-15/16 minor→major |
| REF-06 | ACEITA PARCIALMENTE | ressalvas (ii) e sensibilidade declaradas; regra de atribuição vira desvio D-piloto-4; sem re-atribuição ex post |
| REF-07 | ACEITA PARCIALMENTE | resolução mantida; fundamento trocado pelo critério pré-registrado |
| REF-08 | ACEITA PARCIALMENTE | BETA-CIP-10 requalificado; lacuna da dimensão 5 declarada; ajuste novo |
| REF-09 | ACEITA | tabela de mudanças completada na decisão final |
| REF-10 | ACEITA | argumento de completude registrado; output do script ampliado (rodada 23) |
| REF-11 | ACEITA | retórica de independência corrigida |
| REF-12 | ACEITA PARCIALMENTE | redação corrigida; pendência android-36 registrada; PASS mantidos |
| REF-13 | ACEITA | CSV rev. 2 normalizado aos seis estados |

Nenhuma objeção foi rejeitada integralmente; nenhuma alcançou os vereditos (conclusão do
próprio revisor, `refutacao_parecer.md:252-257`, com os FAILs estruturantes re-executados
por ele). Score re-somado e vereditos finais: seção "Decisão final pós-refutação" de
`juiz_sintese.md`.
