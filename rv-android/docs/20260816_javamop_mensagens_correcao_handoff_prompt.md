# Handoff — corrigir o documento de mensagens JavaMOP e destravar o processo

**Data:** 2026-08-16
**Como usar:** cole este arquivo inteiro como primeira mensagem da nova sessão.
**Estado:** nada implementado, nada commitado. A linhagem inteira — 18 arquivos, 9.032 linhas — está
untracked.

---

## 1. O que é isto, em duas respiradas

Os relatórios de violação do RVSEC são ilegíveis. No dataset do artigo, 72,93 % dos 97.018 registros
carregam o literal `unknown` e existem 19 mensagens distintas no corpus inteiro. O ensaio pós-reparo
do Estudo 03 é pior: 79,91 %.

Três sessões já rodaram sobre esse problema. Elas produziram um documento de design, duas análises
adversariais e uma validação da linhagem inteira. Ninguém implementou nada ainda — de propósito. A
sua sessão é a que finalmente **mexe no documento** e **destrava o processo** para que as issues
possam ser abertas.

Você não vai escrever código de produção. Vai corrigir um documento de design, arquivar duas changes
que estão prontas há dias, e resolver uma colisão de identificadores que já aconteceu e está
bloqueando um gate formal. É trabalho de arrumação — mas é a arrumação sem a qual as oito mudanças
planejadas não podem começar.

---

## 2. A história, contada direito

Vale ler esta seção inteira antes de abrir qualquer arquivo. Ela explica **por que** cada documento
existe, e sem isso você vai tratar todos como se tivessem o mesmo peso — e eles não têm.

**Começou com um plano.** `docs/20260815_javamop_mensagens.md` (982 linhas) é a investigação de
causa-raiz: por que uma linha de violação do RVSEC não diz nada útil. Ele mapeia oito causas (L1–L8),
propõe oito frentes de trabalho (WS-1 a WS-8), abre oito decisões para o pesquisador (D-1 a D-8) e
cataloga cinquenta defeitos concretos (D01–D50). É o documento mais completo da linhagem em termos de
cobertura do problema, e é o que você mais vai precisar consultar — por um motivo que aparece na §4.

**O plano foi atacado.** `docs/20260815_javamop_mensagens_analise.md` (797 linhas) é uma revisão
adversarial, com seis passes independentes reabrindo cada `arquivo:linha` que o plano usa para
decidir alguma coisa. O que não foi relido está marcado UNVERIFIED, o que é honesto e raro.

**Depois foi para fora.** Quatro LLMs externos receberam o mesmo prompt
(`docs/20260815_javamop_mensagens_validacao_prompt.md`) e devolveram quatro relatórios independentes:
`_claude_fable5.md` (751 l.), `_gpt5_codex.md` (480 l.), `_gemini36flash.md` (286 l.),
`_deepseek_v4_flash.md` (237 l.). O do codex se declara explicitamente de "primeiro estágio" — bom o
bastante para bloquear implementação, insuficiente para encerrar a investigação. Guarde essa ressalva,
ela volta na §9.

**Aí veio o documento de design.** `docs/20260815_javamop_mensagens_FINAL.md` (521 linhas) consolidou
tudo e propôs o que de fato seria implementado: oito mudanças (C-0, C-1a, C-1, C-V, C-2, C-3, C-4,
C-5), nove decisões de pesquisador (D-A a D-I), oito gates formais (G-1 a G-8) e nove opções em aberto
(O-1 a O-9). O cabeçalho dele diz, com todas as letras, que é a **entrada de Fase 0 do OpenSpec**:
cada mudança do §8 vira uma issue e um `openspec/changes/gh<N>-<nome>/`. **É este o documento que
você vai corrigir.**

**Sessão 1 — análise adversarial do FINAL.** `docs/20260815_javamop_mensagens_FINAL_analise.md`
(648 linhas). O achado que mais rendeu: eles pegaram o gate que o próprio documento propõe (G-2 /
`INV-INS-110`), rodaram sobre as tabelas dos monitores compilados, e descobriram que o conjunto `jca`
congelado — o que o Estudo 03 executa — viola o invariante **18 vezes em 10 de 23 specs**, enquanto o
`jca_android` pós-gh101 tem zero. O documento nunca tinha registrado isso.

**Sessão 2 — fechamento de lacunas e as decisões.**
`docs/20260815_javamop_mensagens_FINAL_analise_lacunas.md` (818 linhas). Fechou três lacunas que a
sessão 1 deixou abertas, achou seis coisas novas, e — o mais importante — **o pesquisador tomou
quatro decisões**, que são vinculantes e estão na §3 abaixo. Essa sessão também produziu
`docs/20260815_javamop_extracao/` (4 arquivos, 1.269 linhas), que é o casamento item a item dos quatro
relatórios externos contra o FINAL: 581 itens, 450 carregados, 70 parciais, 61 ausentes.

**Sessão 3 — validação da linhagem inteira.**
`docs/20260815_javamop_mensagens_validacao.md` (850 linhas). Dez subagentes com recortes disjuntos, e
uma regra dura: leitura integral, nunca amostragem. O veredito e os achados estão na §3.

Há ainda três prompts de handoff das sessões anteriores (`_analise_handoff_prompt.md`,
`_FINAL_analise_handoff_prompt.md`, `_validacao_handoff_prompt.md`), que valem como registro de o que
cada sessão recebeu como encomenda — útil se você quiser entender por que uma sessão olhou para uma
coisa e não para outra.

---

## 3. Onde as coisas estão hoje

### O veredito da validação

O núcleo numérico da linhagem é **sólido**: de vinte grandezas remedidas, dezessete reproduzem
exatamente. O que é frágil é o aparato de citação e de escopo. As três divergências têm todas a mesma
assinatura — número transportado de um documento para outro em vez de medido, com o denominador
trocado no caminho.

### As quatro decisões já tomadas (vinculantes, não reabra)

| Decisão | Escolha | O que isso cria de trabalho |
|---|---|---|
| **D-A** — conjunto alvo | **(ii)**: conjunto sucessor `jca_v2` derivado do `jca` congelado. **Não mexer em `jca_android`.** | `jca_v2` = `jca` + lista de reparos nomeados. Como não herda cobertura de auditoria, **C-V vira pré-requisito duro de C-4**. |
| **`st=`** no envelope | **Sai do contrato.** Fica `v=1 code=… ev=… obj=… val='…' exp='…' msg='…'` | O-1 deixa de ser pré-requisito de C-3. Mas veja a armadilha na §5. |
| **D-C** — aridade `args()` | **Landar agora**, com a regra corrigida em três cláusulas. | Fechar antes as tarefas pendentes da gh100. |
| **Ordem** | **Corrigir o documento antes de abrir issues.** | É exatamente o que você vai fazer. |

### A decisão que continua pendente

**D-B, o oráculo.** CrySL 1.5.2 contra MetaCrySL api30, por família de cláusula. Ficou mais urgente
porque `jca_v2` deriva do `jca`, cuja âncora é a 1.5.2, não a api30. A sessão 3 corrigiu o número que
dá consequência a ela: **não são 97 % da categoria `UnsafeAlgorithm` que sumiriam sob a api30, são
38 %** — as 6.048 linhas do numerador são a fatia do `MessageDigestSpec`, não a categoria, que tem
15.444. Isso reduz a urgência por um fator de 2,5 e afia o alvo: é uma decisão sobre MD5/SHA-1 numa
spec, não sobre o catálogo inteiro.

### Os três achados estruturais da sessão 3

**Primeiro: o documento amputou 76 % dos arquivos de spec sem declarar.** A árvore tem 191 arquivos
`.mop`. Os conjuntos `generic` (118) e `generic_new` (27) — **145 arquivos, 75,9 %** — não passam pelo
`ErrorCollector`/`ErrorDescription` em ponto algum: emitem `android.util.Log.v` cru. O `generic`
inteiro colapsa numa única mensagem (`<Spec> went into an error state.`), sem tipo de erro, sem valor
observado, sem nome de classe. Trinta e dois dos 118 importam AWT/Swing, mortos no Android. O
contrato de relatório do `FINAL` §7.1 não os alcança. O plano dedicava a **WS-8 inteira** a isso; o
`FINAL.md` menciona `generic/` **zero vezes** e não o lista nos non-goals. As duas análises
adversariais não pegaram porque as duas partiram do `FINAL.md` — só a leitura do plano revela.
Atenuante honesto: o conjunto **nunca rodou** (os 63 manifestos de campanha dizem `jca`).

**Segundo: o gate formal é cego para a variante majoritária do defeito.** `INV-INS-110` exige que todo
evento **apareça** no autômato. Isso pega a Forma A (evento sem linha nenhuma → tudo vai ao sink) e
não pega a Forma B: o evento aparece só como **auto-laço**, e quem afunda é a chamada seguinte. Cinco
specs — `CipherSpec`, `KeyStoreSpec`, `KeyManagerFactorySpec`, `MacSpec`, `KeyGeneratorSpec` — passam
limpas no gate carregando o defeito, e respondem por 3.038 linhas mudas (19,3 %); com o
`MessageDigestSpec`, que o gate pega por outro evento, a família chega a 5.046 (32,1 %). O
`jca/KeyManagerFactorySpec.mop:66-84` mostra a anatomia: o autor **criou** o estado `unsafeAlg` e não
lhe deu linha `init`. E tem um efeito perverso: **reparar o órfão converte Forma A em Forma B** — foi
o que a gh101 fez no `SSLContextSpec`, medido nas tabelas.

**Terceiro: 26 dos 134 eventos são despachados ao slice global.** JavaMOP liga evento a parâmetro
**por nome**; onde o nome diverge, o evento vira global e é difundido a todos os monitores vivos.
`KeyStoreSpec` é 7 de 7 (declara `ks`, os eventos ligam `k`) — um monitor único para o processo
inteiro, e o terceiro maior produtor de mudas do corpus. Nenhum dos onze documentos enumera a classe.

---

## 4. O plano em cinco fases (o resumo executivo)

| Fase | O que é | Bloqueia | Estado |
|---|---|---|---|
| **0** | Duas decisões do pesquisador que definem o tamanho do programa | tudo | **aberta** |
| **1** | Corrigir o `FINAL.md` — 11 correções antigas + 9 novas | Fase 3 | **é a sua sessão** |
| **2** | Destravar o processo: arquivar gh101/gh102, resolver a colisão de invariantes, fechar as pendências da gh100 | Fase 3 | **é a sua sessão** |
| **3** | Abrir as issues e criar as changes OpenSpec via skills | Fase 4 | próxima |
| **4** | Implementar, em quatro ondas | — | depois |

**Por que a Fase 0 vem antes de tudo.** Duas perguntas precisam de resposta do pesquisador porque
mudam o **tamanho** do programa, não o conteúdo. (a) O que fazer com a WS-8 / conjunto `generic`: vira
uma mudança C-6, ou entra nos non-goals com a razão escrita? São 145 arquivos — a resposta muda o
programa inteiro. (b) D-B, o oráculo, agora com o número corrigido. Nenhuma das duas é decisão de
implementador.

**Por que a Fase 1 antes da 3.** Já foi decidido assim, e a razão é boa: o §4 do `FINAL.md` é citado
como fonte pelas seções §5 a §9, e ele carrega erros que se propagam — o mais caro é a linha do
`okio.`/85,44 %, que registra como concordância um número que a fonte refuta, e da qual o default de
D-F é derivado diretamente. Abrir issues sobre isso propaga o erro para dentro dos artefatos OpenSpec.

**Por que a Fase 2 é sua e não da próxima.** Porque a Fase 3 não pode acontecer sem ela: `INV-INS-109`
e `INV-INS-110` estão definidos **duas vezes com significados incompatíveis**, nas deltas de gh100 e
gh101, ambas ativas. O gate G-2, a §7.4 do FINAL e a tarefa C-V(2) citam "INV-INS-110" no sentido da
gh101. Enquanto as duas coexistirem, a citação é ambígua.

**As quatro ondas da Fase 4**, para você saber onde isso vai dar: onda A = C-0 + C-1a + C-V(a) em
paralelo (arquivos disjuntos); onda B = C-1 + C-V(b/c); onda C = **C-4 → C-3 sequenciadas** (a
mensagem nomeia estados que C-4 vai criar, então a ordem importa e a intercalação "por arquivo" que o
documento propõe não funciona); onda D = C-2 (device-side, depois do Estudo 03 fechar) + C-5.

---

## 5. O que fazer nesta sessão

### Passo zero, antes de qualquer coisa: commite a linhagem

Os 18 arquivos estão untracked. Você vai editar o `FINAL.md` pesadamente. Sem um commit antes, não há
como diferenciar o que você mudou nem reverter se der errado. **Atenção: a raiz do repositório git é
`rvsec`, não `rv-android`** — os caminhos no `git status` vêm prefixados com `rv-android/`.

Aproveite e resolva o que está solto e pertence ao tema: há quatro arquivos tracked modificados
(`experimento-cal/scripts/consolidate_cal.py`, `verify_iteration.py`,
`experimento-cal/tests/test_consolidate_verify.py` — que são **uma correção só**, o filtro de smoke
por timeout, e devem ir juntos — mais `scripts/validate_instrument_jca190.py`, independente), e sete
deleções de `docs/analise_*.md` nunca commitadas.

### Fase 0 — leve as duas perguntas ao pesquisador

Não decida sozinho. Apresente as duas com o número medido do lado e pergunte. Use
`AskUserQuestion` se fizer sentido, mas o importante é que a resposta seja dele.

### Fase 1 — as vinte correções ao `FINAL.md`

Vale dizer uma coisa que destrava a sua cabeça: **corrigir o `FINAL.md` com `Write`/`Edit` é
legítimo.** O `docs/WORKFLOW.md:47` é explícito — um documento técnico de Fase 0 é *material de
referência, não artefato OpenSpec*. A proibição do `CLAUDE.md` de escrever artefatos à mão vale para
o que está sob `openspec/changes/gh<N>-*/`. O `FINAL.md` não está.

**As 11 correções herdadas** estão listadas na §7.1 do `_lacunas.md`. Mas sete delas nascem
incompletas — a sessão 3 mostrou onde. As duas que mais importam:

- O **item 7** remove `st` do contrato e **não manda tocar a §7.2**, que continua prescrevendo
  `int stateBefore`, `stateBefore = getState();` em cada corpo de evento e o texto de código
  `<SPEC>-ORDER-00 = "sequence violation at event ev in state st"`. Se você aplicar só o item 7, o
  documento fica com um contrato sem `st` e um mecanismo que ainda o escritura.
- O **item 10** carrega só uma das quatro componentes de D-C. Faltam o teste que fixa a decisão, o
  sítio declarado fora de escopo (advices `before` não passam por wrapper) e a ordem obrigatória.

**As 9 correções novas** estão na §5 do `_validacao.md`. As de maior efeito a jusante:

1. Trocar a razão escrita da decisão de ordem. Hoje ela se justifica com *"111 dos 225 IDs não têm
   referente possível (§2.1)"* — e a §2.1 é exatamente onde essa alegação foi **retirada como falsa**.
   A decisão continua de pé pelos outros motivos; a razão escrita não.
2. Reformular o item 2 de "reintroduzir" para "desopacificar": o falso negativo do `KeyGeneratorSpec`
   não sumiu, ele chega como o token opaco `D11`.
3. Corrigir os três números que não reproduzem (§3.1 do `_validacao.md`).
4. Registrar as quatro decisões no §6 do alvo — hoje ele ainda apresenta D-A e D-C como abertas com
   "recommended default".
5. Acrescentar o censo de mensagens que mentem como **pré-condição** de C-3, não consequência. Se C-3
   reescrever toda mensagem sobre um `ErrorType` errado e uma constante errada, o envelope passa a
   carregar um `code` que certifica uma mentira.
6. Acrescentar os gates **G-2b** (Forma B) e **G-1b** (slice-raiz) a C-V. E note: o terceiro gate que
   a validação pede **já existe** — `INV-INS-111`, na delta da gh101, exige que toda `Property`
   escrita seja lida ou registrada como omissão deliberada. O `jca` o viola 18 vezes e nenhum
   documento da linhagem o cita. Não é gate a escrever, é gate a adotar.

**Recorte sugerido para subagentes** (veja a §6): um agente por seção do `FINAL.md` — §2 (a tabela
F1–F14, que tem nove citações "review §X" falsas ou imprecisas), §4 (a coluna `Item(s)`, 225 IDs),
§7 (contrato + gramática + matriz de consumidores), §8/§9 (grafo de mudanças, opções, mapeamento
`C-x → gh<N>`).

### Fase 2 — destravar o processo

**Arquive a gh102.** Está completa (28/28) e a delta dela **já está sincronizada** nas specs
principais. Só falta commitar duas caixas marcadas no working tree e rodar o archive.

**Arquive a gh101.** Está completa (84/84) e a delta **não** está sincronizada — `INV-INS-109` a
`INV-INS-115` só existem dentro da change. Arquivar sincroniza e **força a resolução da colisão**.

**Resolva a colisão INV-INS-109/110.** As quatro definições estão em
`openspec/changes/gh100-*/specs/instrumentation/spec.md:63,65` e
`openspec/changes/gh101-*/specs/instrumentation/spec.md:43,47`. gh100 aloca 104–110, gh101 aloca
109–115; colidem exatamente em 109 e 110. O primeiro ID livre é **INV-INS-116** (há lacunas antes:
28, 46–49, 74–79, se preferir não esticar o topo). Cuidado: os IDs colididos são citados em ~35
lugares dentro das duas changes — renumerar não é editar duas linhas.

**Feche as pendências da gh100.** A decisão D-C manda fechar as tarefas 7.4–7.6 antes de C-1a. Mas
olhe o arquivo: `tasks.md:96` é uma 7.4 marcada `[x]` com resultado completo e `tasks.md:97` é uma
7.4 `[ ]` duplicada — resíduo de checklist. O trabalho real é **7.5** (`/rv-code-reviewer`) e **7.6**
(`/rv-docs-sync`, condicional em "se a doc do módulo precisar"), mais apagar a linha duplicada.

**Anote duas coisas para a Fase 3.** (a) Os templates de issue vivem em `rvsec/.github/ISSUE_TEMPLATE/`
(um nível acima do `rv-android`), são cinco, e `blank_issues_enabled: false` — **não dá para abrir
issue sem template**. Não existe `Documentation+scripts`, que é o que a linha do C-0 declara; o mais
próximo é `documentation.yml`, que auto-aplica `track:quick-path`. (b) O primeiro `gh<N>` livre é
**104**.

### O que NÃO fazer nesta sessão

- **Não implemente nenhuma mudança C-\*.** Nem a C-1a, por mais tentadora que a regra de três
  cláusulas pareça.
- **Não abra issues nem crie changes** antes das Fases 1 e 2 fecharem.
- **Não edite `jca_android`.** Decisão D-A.
- **Não edite os documentos históricos.** O `FINAL.md` é o único artefato vivo. As duas análises e a
  validação são registro do que foi encontrado quando foi encontrado — corrigi-los retroativamente
  destrói a rastreabilidade. É P4 aplicado a documentos.
- **Não rode experimento em device.** Nem emulador, nem `adb`, nunca, por nada.

---

## 6. Como trabalhar

### Use subagentes, e use direito

O trabalho é largo e paralelizável. Despache em recortes **disjuntos**, num único bloco de chamadas.
A regra do próprio repositório (`docs/WORKFLOW.md:326-331`) é boa: agrupe por **independência**
(tarefas que não compartilham arquivo vão para agentes diferentes) e por **localidade** (tarefas no
mesmo módulo ou diretório vão para o mesmo agente, para não brigar por merge). Cada agente deve
receber entre 3 e 15 arquivos — menos que isso é overhead, mais que isso arrisca compactação dentro do
próprio agente.

Passe para o subagente: os arquivos exatos, os critérios de aceitação, as constantes e convenções que
ele precisa, e os princípios P1–P4 se ele for escrever documentação. **Não** passe o histórico da
conversa nem o resultado de outros grupos.

E o mais importante, que custou caro descobrir: **instrua leitura integral, explicitamente, e proíba
grep para estabelecer presença ou contagem**. Grep só serve para *confirmar ausência* depois de já ter
lido. Peça a cada agente que declare, no fim, quantas linhas leu e em quantos blocos — é assim que
você audita a cobertura dele.

### Use o sequential thinking

O MCP `sequential-thinking` está disponível e é apropriado aqui, especialmente para a Fase 0 (as duas
decisões têm consequências em cadeia: o destino da WS-8 muda o tamanho do programa, e D-B muda o
catálogo de C-4) e para desenhar a ordem das ondas da Fase 4. Use para pensar, não para narrar.

### Verifique os subagentes, inclusive o denominador

Na sessão 2, três conclusões de agente foram descartadas por medição direta e **duas afirmações do
próprio orquestrador caíram por denominador não verificado**. Na sessão 3 aconteceu de novo, comigo:
fiz um censo do grafo de predicados procurando `getProperty`/`hasProperty` quando a API real de
leitura é `validate(...)`, e a coluna inteira saiu zerada. Um subagente depois achou que eu também
tinha errado a remoção — é `remove(Property.X)`, e `removeProperty(` não aparece nenhuma vez no
conjunto.

Verificar uma contagem exige verificar **o universo sobre o qual ela é feita**, não só o valor contado.

### Siga o WORKFLOW rigorosamente

Quando chegar a hora de criar changes (Fase 3, não esta sessão), a regra do `CLAUDE.md:187-189` é
não-negociável: artefatos OpenSpec são criados **exclusivamente** via as skills, pelo `Skill` tool.
Nunca `Write`/`Edit` direto em `proposal.md`, `design.md`, `tasks.md` ou delta specs.

A rota canônica do Full SDD é `openspec-new-change` → `openspec-continue-change` **quatro vezes**
(proposal, specs, design, tasks — a skill cria **um artefato por invocação**, é guardrail dela) →
`openspec-apply-change` → `rv-code-reviewer` → `openspec-verify-change` → `openspec-archive-change`.
No FF SDD, `openspec-ff-change` gera tudo de uma vez. Existem na árvore duas skills não documentadas
(`openspec-propose`, `openspec-update-change`) — funcionam, mas divergem do que o WORKFLOW prescreve;
prefira `/opsx:ff`.

Escolha o track pela pergunta *"isto exige decisões de design que precisam de artefato de spec?"*, e
**nunca por contagem de arquivos** — o WORKFLOW tem um aviso explícito sobre isso
(`docs/WORKFLOW.md:193`). Na dúvida, Quick Path.

### As regras duras do projeto

Português com acentuação correta. Código e comentários em inglês. Sem `Co-Authored-By` nos commits —
o pesquisador é o autor único. "MOP" significa *monitored operations*, nunca terminologia de
segurança. Testes sempre com `--import-mode=importlib -o "addopts="`. E os princípios P1–P4
(simplicidade; documentação narrativa que explica o *porquê*; sem retrocompatibilidade, com backup em
`backup/` antes de deletar; comentários descrevem o estado atual, sem histórico de migração).

---

## 7. Os documentos, com tamanho e papel

Tudo em `rv-android/docs/`. **Os 18 estão untracked.**

### A linhagem principal

| Arquivo | Linhas | Papel |
|---|---:|---|
| `20260815_javamop_mensagens.md` | 982 | **o plano**: causa-raiz L1–L8, WS-1..8, D-1..8, D01–D50. Leia-o — é o único que conhece o `generic/` |
| `20260815_javamop_mensagens_analise_handoff_prompt.md` | 311 | encomenda da revisão do plano |
| `20260815_javamop_mensagens_analise.md` | 797 | revisão adversarial do plano |
| `20260815_javamop_mensagens_validacao_prompt.md` | 349 | prompt dado aos quatro LLMs externos |
| `20260815_javamop_mensagens_claude_fable5.md` | 751 | validação externa 1 |
| `20260815_javamop_mensagens_gpt5_codex.md` | 480 | validação externa 2 (declara-se de primeiro estágio) |
| `20260815_javamop_mensagens_gemini36flash.md` | 286 | validação externa 3 |
| `20260815_javamop_mensagens_deepseek_v4_flash.md` | 237 | validação externa 4 |
| **`20260815_javamop_mensagens_FINAL.md`** | **521** | **o documento de design — o que você vai corrigir** |
| `20260815_javamop_mensagens_FINAL_analise.md` | 648 | sessão 1: análise adversarial do FINAL |
| `20260815_javamop_mensagens_FINAL_analise_handoff_prompt.md` | 308 | encomenda da sessão 2 |
| `20260815_javamop_mensagens_FINAL_analise_lacunas.md` | 818 | **sessão 2: lacunas fechadas + as quatro decisões (§6) + as 11 correções (§7.1)** |
| `20260815_javamop_mensagens_validacao_handoff_prompt.md` | 425 | encomenda da sessão 3 |
| **`20260815_javamop_mensagens_validacao.md`** | **850** | **sessão 3: a validação da linhagem — leia §3, §4 e §5** |
| `20260816_javamop_mensagens_correcao_handoff_prompt.md` | — | **este arquivo** |

### As listas de extração — `docs/20260815_javamop_extracao/`

581 itens dos quatro relatórios, casados item a item contra o `FINAL.md`.

| Arquivo | Linhas | Itens |
|---|---:|---|
| `claude_fable5.md` | 509 | 193: 148 carregados, 23 parciais, 22 ausentes |
| `gpt5_codex.md` | 423 | 202: 166 carregados, 16 parciais, 20 ausentes |
| `deepseek_v4_flash.md` | 169 | 113: 84 carregados, 16 parciais, 13 ausentes, 3 invertidos |
| `gemini36flash.md` | 168 | 73: 52 carregados, 15 parciais, 6 ausentes |

**Ressalva importante:** os totais reproduzem, mas **não são somáveis**. As quatro listas não
compartilham definição de "item" nem escala de transporte — seis fatos recebem estados diferentes
conforme quem classifica, contra a mesma célula do FINAL. Descontando repetição e classificação
errada, a contagem honesta de ausências distintas é ~40, não 61.

### Fontes de evidência

- **Datasets.** `/home/pedro/.../ase-journal/dataset/results/errors.csv` — 97.018 linhas, **10
  colunas, sem `source`**. `experimento-comp162/results/*/*/errors.csv` — 8 réplicas, 19.664 linhas,
  11 colunas. `experimento-comp162-ajc/consolidado/` — 6 CSVs de comparação AspectJ × dexlib2.
- **Monitores gerados** (o oráculo que diz a verdade): `results/gh56-smoke/monitors/` (jca congelado,
  18 órfãos), `results/gh99_jca_android_monitors/` (pré-gh101, 18 órfãos),
  `results/gh101_group8_jca_android/` (pós-gh101, **0 órfãos**),
  `results/gh101_group8_jca_frozen_control/` (controle congelado, 18).
- **Specs.** `rvsec/rvsec-mop/src/main/resources/{jca,jca_android,generic,generic_new}/` — 23, 23,
  118, 27 arquivos.
- **Oráculos CrySL.** `/home/pedro/.../Crypto-API-Rules/JavaCryptographicArchitecture/src/` (51
  `.crysl`, a 1.5.2) e `/home/pedro/.../MetaCrySL/generated/api30/` (33 `.cryptsl`, a api30).
- **Auditoria.** `audit/20260808_validacao_jca_android/` — `fase0/pre_registro.md:10` delimita o
  escopo a `jca_android` (o `jca` **nunca** foi auditado); `global/juizglobal_relatorio.md` §10 traz o
  veredito REPROVADA 22/22.
- **Trabalho anterior.** `openspec/changes/gh10{0,1,2}-*/` (ativas), `archive/…gh103-*`.

---

## 8. Comandos que reproduzem as medições

Todos somente-leitura, rodados de `rv-android/`. **Foram executados e validados** — se algum falhar,
o problema é ambiente, não o comando.

**Antes de usar qualquer um: as definições importam mais do que o comando.** Um subagente rodou a
decomposição do comp162 com a definição errada de "gêmeo muda↔muda" e obteve **11.751 linhas** onde a
linhagem tem **838**. Mesmo nome, números diferentes por uma ordem de grandeza. Então fixe:

- **muda** = `message == 'unknown'`
- **sítio** = a 4-tupla `(spec, class, method, source)`
- **gêmeo muda↔legível** = sítio com ≥1 muda **e** ≥1 legível
- **gêmeo muda↔muda** = sítio 100 % mudo que emite **dois `ErrorType` diferentes com contagem
  idêntica** (não é "sítio mudo com ≥2 linhas")
- **Forma B** = spec com **zero** órfãos, um evento com auto-laço no estado 0, e ≥1 evento que vai ao
  sink a partir do estado 0
- **slice-raiz** = evento cujo método `*Event` resolve `matchedEntry = <Spec>__Map;`

**Dataset de referência** — deve dar `97018 linhas | 19 mensagens | 70760 unknown = 72.93 %`:
```bash
python3 -c "
import csv,collections
r=list(csv.DictReader(open('/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv')))
c=collections.Counter((x.get('message') or '').strip() for x in r)
print(len(r),'linhas |',len(c),'mensagens |',c['unknown'],'unknown =',round(100*c['unknown']/len(r),2),'%')
"
```

**Decomposição do comp162** — deve dar 19.664 linhas, 15.714 mudas, 296 sítios, 101 gêmeos
muda↔legível com 3.950 mudas, 12 gêmeos muda↔muda com 838 linhas, 183 solitários com 10.926:
```bash
python3 -c "
import csv,glob,collections
rows=[]
for f in sorted(glob.glob('experimento-comp162/results/*/*/errors.csv')): rows+=list(csv.DictReader(open(f)))
def et(r):
    p=(r.get('unique_msg') or '').split(':::'); return p[3] if len(p)>3 else '?'
mute=lambda r:(r.get('message') or '').strip()=='unknown'
site=lambda r:(r['spec'],r['class'],r['method'],r['source'])
m=collections.Counter(site(r) for r in rows if mute(r)); l=collections.Counter(site(r) for r in rows if not mute(r))
print(len(rows),'linhas |',sum(m.values()),'mudas |',len(m),'sitios')
print('gemeas muda-legivel:',sum(m[s] for s in m if s in l),'em',len([s for s in m if s in l]),'sitios')
per=collections.defaultdict(collections.Counter)
for r in rows:
    if mute(r): per[site(r)][et(r)]+=1
mm=[(s,c) for s,c in per.items() if len(c)>1 and min(c.values())==max(c.values())]
print('gemeas muda-muda  :',sum(sum(c.values()) for s,c in mm),'em',len(mm),'sitios')
"
```

**Eventos órfãos (o gate G-2)** — aceita qualquer um dos quatro monitores como argumento; no
`gh56-smoke` deve dar `23 monitores | 18 eventos orfaos em 10 specs`:
```bash
python3 -c "
import re,collections,sys
f=sys.argv[1]; cur=None; res=collections.defaultdict(dict)
for l in open(f):
    m=re.match(r'\s*(?:final )?class (\w+SpecMonitor) extends', l)
    if m: cur=m.group(1)
    m2=re.match(r'\s*static final int Prop_\d+_transition_(\w+)\[\] = \{([0-9, ]+)\};', l)
    if m2 and cur: res[cur][m2.group(1)]=[int(x) for x in m2.group(2).split(',')]
bad=[(mon,ev,row) for mon,tbl in sorted(res.items()) for ev,row in tbl.items()
     if all(v==max(max(r) for r in tbl.values()) for v in row)]
print(len(res),'monitores |',len(bad),'eventos orfaos em',len(set(b[0] for b in bad)),'specs')
[print('  ',*b) for b in bad]
" results/gh56-smoke/monitors/MultiSpec_1RuntimeMonitor.java
```

**Forma B (o gate G-2b que ainda não existe)** — deve dar 5 specs:
```bash
python3 -c "
import re,collections,sys
f=sys.argv[1]; cur=None; res=collections.defaultdict(dict)
for l in open(f):
    m=re.match(r'\s*(?:final )?class (\w+SpecMonitor) extends', l)
    if m: cur=m.group(1)
    m2=re.match(r'\s*static final int Prop_\d+_transition_(\w+)\[\] = \{([0-9, ]+)\};', l)
    if m2 and cur: res[cur][m2.group(1)]=[int(x) for x in m2.group(2).split(',')]
n=0
for mon,tbl in sorted(res.items()):
    sink=max(max(r) for r in tbl.values())
    if [e for e,r in tbl.items() if all(v==sink for v in r)]: continue
    loop=[e for e,r in tbl.items() if r[0]==0]; tosink=[e for e,r in tbl.items() if r[0]==sink]
    if loop and tosink:
        n+=1; print(' ',mon.replace('Monitor',''),'| auto-laco:',','.join(sorted(loop)),'| ao sink do estado 0:',','.join(sorted(tosink)))
print(n,'specs na Forma B')
" results/gh56-smoke/monitors/MultiSpec_1RuntimeMonitor.java
```

**Slice-raiz (o gate G-1b que ainda não existe)** — deve dar 26 eventos em 10 specs:
```bash
python3 -c "
import re,sys,collections
f=sys.argv[1]; src=open(f).read().splitlines()
cur=None; body=[]; out=collections.defaultdict(list)
sig=re.compile(r'\s*public static final void (\w+Spec)_(\w+)Event\(')
def flush():
    if cur and any(('matchedEntry = %s__Map;'%cur[0]) in l for l in body): out[cur[0]].append(cur[1])
for l in src:
    m=sig.match(l)
    if m: flush(); cur=(m.group(1),m.group(2)); body=[]
    elif cur is not None: body.append(l)
flush()
print(sum(len(v) for v in out.values()),'eventos no slice-raiz em',len(out),'specs')
for s,evs in sorted(out.items()): print('  %-28s %s'%(s,', '.join(evs)))
" results/gh56-smoke/monitors/MultiSpec_1RuntimeMonitor.java
```

**Grafo de predicados** — cuidado com os nomes de API: leitura é `validate(`, remoção é `remove(`.
Deve dar 23 propriedades, 1 lida sem produtor (`GENERATED_PRIVATE_KEY`), 18 escritas sem leitor:
```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources && python3 -c "
import re,glob,collections
W=collections.defaultdict(set); R=collections.defaultdict(set); D=collections.defaultdict(set)
for f in sorted(glob.glob('jca/*.mop')):
    b=f.split('/')[-1]; s=open(f).read()
    for p in re.findall(r'setProperty\(Property\.([A-Z0-9_]+)',s): W[p].add(b)
    for p in re.findall(r'validate\(Property\.([A-Z0-9_]+)',s):    R[p].add(b)
    for p in re.findall(r'remove\(Property\.([A-Z0-9_]+)',s):      D[p].add(b)
print('propriedades              :',len(set(W)|set(R)|set(D)))
print('LIDAS SEM PRODUTOR        :',sorted(set(R)-set(W)))
print('ESCRITAS SEM LEITOR       :',len(set(W)-set(R)),sorted(set(W)-set(R)))
print('REMOVIDAS SEM ESCRITA     :',sorted(set(D)-set(W)))
"
```

**Os quatro conjuntos de specs** — deve mostrar `jca` 23/21/0, `jca_android` 23/21/0, `generic`
118/0/118, `generic_new` 27/0/27:
```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources && for d in jca jca_android generic generic_new; do
  printf "%-12s arquivos=%3d  com addError=%3d  com Log.v=%3d\n" "$d" \
    "$(ls $d/*.mop 2>/dev/null | wc -l)" \
    "$(grep -l addError $d/*.mop 2>/dev/null | wc -l)" \
    "$(grep -l 'Log\.v' $d/*.mop 2>/dev/null | wc -l)"
done
```

**`read_errors_csv` contra os dois datasets** — o `ValueError` no ARTIGO é o **resultado esperado**,
não uma falha: o dataset publicado tem 10 colunas e não tem `source`:
```bash
uv run python -c "
from aperv_tool.analysis.violations import read_errors_csv, ERRORS_CSV_HEADER
print('header esperado:',ERRORS_CSV_HEADER)
for lbl,p in [('ARTIGO','/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv'),
              ('COMP162','experimento-comp162/results/comp162_00/comp162_00/errors.csv')]:
    try: read_errors_csv(p); print(lbl,'OK')
    except Exception as e: print(lbl,type(e).__name__,str(e)[:300])
"
```

**Colisão de invariantes** — o spec principal para em INV-INS-103; as definições conflitantes estão
nas duas deltas:
```bash
grep -oE "INV-INS-[0-9]+" openspec/specs/instrumentation/spec.md | sort -u -V | tail -3
grep -nE "INV-INS-1(09|10|15)" openspec/changes/gh10{0,1}-*/specs/instrumentation/spec.md | cut -c1-120
```

**Testes** (contrato de CI — sem estas flags a coleta quebra):
```bash
uv run pytest --import-mode=importlib -o "addopts=" modules/<modulo>/tests
```

---

## 9. O que aprendemos do jeito difícil

**Leitura integral vence amostragem, e a diferença não é marginal.** Uma sessão contou 116 itens
amostrando três blocos por relatório; a leitura integral encontrou **581**. A conclusão errada
derivada dos 116 sobreviveu a uma rodada inteira de verificação — porque a verificação também
amostrou. Quando a pergunta é "o que foi deixado de fora", só leitura integral responde. Use grep
apenas para *confirmar* ausência, jamais para estabelecer presença ou contagem.

**Verificar uma contagem exige verificar o denominador.** Esta é a irmã da anterior e derrubou mais
afirmações do que qualquer outra coisa: o numerador estava certo, o universo estava errado. Aconteceu
com "111 de 225 IDs", com "97 % da categoria `UnsafeAlgorithm`" (era 97 % de uma spec, 38 % da
categoria), e comigo, num censo que zerou uma coluna inteira porque eu procurei o nome errado de API.

**Rode o gate que o próprio documento propõe.** É o teste mais barato e mais revelador que existe. A
sessão 1 achou os 18 órfãos rodando o G-2 que o documento propunha como gate futuro e nunca tinha
aplicado ao conjunto em produção. A sessão 3 foi além e descobriu que **o gate é cego** para a
variante majoritária do defeito. Um gate verde não é o mesmo que um sistema são.

**Extraia semântica do artefato gerado, não do texto-fonte.** Os índices de estado não seguem a ordem
de declaração no `.mop`, símbolos ERE não declarados somem em silêncio, eventos duplicados fundem, e o
fatiamento por slice-raiz só é visível no monitor gerado. Só o artefato gerado diz a verdade.

**Leia o documento *anterior* ao alvo.** Este é o aprendizado mais novo e o mais transferível. Duas
análises adversariais completas passaram por cima da amputação de 76 % dos arquivos de spec, e a razão
é simples: as duas partiram do `FINAL.md`. O que não está lá é invisível para quem só lê ele. Foi
preciso ler o plano original para ver o buraco.

**Distinga "registro que precisa de mensagem melhor" de "registro que não deveria existir".** É a
distinção que faltava no documento alvo, e 30,5 % do volume mudo é da segunda categoria — some por
deleção, sem design de mensagem nenhum. Corolário desconfortável: como C-1a e C-4 encolhem o
denominador de propósito, a métrica "% de `unknown`" pode **subir** com o sistema melhorando.

**Reparar um defeito pode escondê-lo em vez de resolvê-lo.** O reparo dos eventos órfãos converte a
Forma A na Forma B — sai do radar do gate e mantém o comportamento. Se você só olha o gate, parece
progresso.

**Um número verificado como "exato" pode contar o fenômeno errado.** "8.371 `found .`" é exato para o
que conta, e é o denominador errado do fenômeno, que são 8.843 em cinco specs.

**As fontes pedem para não serem citadas como certificação, e são.** O relatório do codex declara-se
de primeiro estágio e diz que concordância entre passes nunca vale como prova — *"as citações é que
valem"*. O `FINAL.md` faz o oposto. Vale para você também: **não trate concordância entre subagentes
como evidência.** Peça a citação, e meça você mesmo o que sustenta decisão.

---

## 10. Primeira ação sugerida

Leia, nesta ordem e por inteiro: `docs/20260815_javamop_mensagens_validacao.md` (850 l., é o mais
recente e traz o mapa de tudo), depois `docs/20260815_javamop_mensagens_FINAL.md` (521 l., o alvo),
depois a §6 e a §7 do `docs/20260815_javamop_mensagens_FINAL_analise_lacunas.md` (as decisões e as 11
correções). Se sobrar fôlego, o plano original — é o único que conhece o `generic/`.

Depois disso, commite a linhagem, leve as duas perguntas da Fase 0 ao pesquisador, e só então
despache os subagentes da Fase 1.
