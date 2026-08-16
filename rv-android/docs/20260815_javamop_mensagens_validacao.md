# Validação da linhagem de documentos sobre mensagens JavaMOP

**Data:** 2026-08-15
**Natureza:** terceira sessão sobre a linhagem. **Nada foi implementado.** Toda a investigação foi
somente-leitura; nenhum emulador foi tocado; nenhuma issue foi aberta; nenhuma change OpenSpec foi
criada.
**Alvo:** a linhagem inteira — o plano (982 l.), sua revisão adversarial (797 l.), os quatro
relatórios de validação externa (1.754 l.), o documento de design `..._FINAL.md` (521 l.), a análise
adversarial da sessão 1 (648 l.), o fechamento de lacunas da sessão 2 (818 l.) e as quatro listas de
extração (1.269 l.).

**Método.** Dez subagentes com recortes disjuntos, todos sob instrução explícita de **leitura
integral, nunca amostragem** — o aprendizado mais caro das duas sessões anteriores, onde uma
contagem por amostragem produziu 116 itens onde a leitura integral encontrou 581. Seis recortes de
consistência (interna do `_lacunas.md`; `_lacunas` × `_analise`; cobertura das 11 correções; listas
de extração; remedição de todos os números; `FINAL` contra o plano e sua revisão) e quatro de
descoberta (as 61 ausências e 70 parciais item a item, em dois recortes; as nove opções; caça a
melhorias não propostas).

**Arbitragem.** Vinte medições próprias, feitas antes ou depois dos relatórios, decidiram todos os
casos em que os agentes divergiram entre si ou do documento. Estão marcadas **[medido aqui]** ao
longo do texto. Duas conclusões de agente foram corrigidas por essa via e estão registradas em §6.
Concordância entre agentes **não** foi aceita como evidência em nenhum ponto.

---

## 1. Veredito

**A pergunta 1 — está tudo consistente? Não, e os defeitos se concentram num lugar específico:** o
**núcleo numérico da linhagem é sólido** e o **aparato de citação e de escopo é frágil**. Das vinte
grandezas que remedi, dezessete reproduzem exatamente e três divergem — e as três divergências têm
a mesma assinatura: número **transportado** em vez de medido, com o denominador trocado no caminho.

**A pergunta 2 — deixamos passar alguma sugestão que melhore o sistema? Sim, e uma delas é
estrutural.** O documento de design amputou **76 % dos arquivos de especificação da árvore** sem
declarar; o gate formal que ele adota como pedra angular é **cego para a variante majoritária** do
defeito que ele existe para pegar; e há uma classe inteira de defeito de fatiamento — 26 dos 134
eventos — que nenhum dos onze documentos enumera.

A conclusão da sessão 2 — "o documento está pronto para virar issues depois das correções" — **se
mantém**, mas a lista de correções cresce de 11 itens para 11 + 9, e **duas** delas precisam
acontecer antes de qualquer decisão de escopo, não depois.

---

## 2. O que a remedição confirmou

Isto importa dizer primeiro, porque o resto do documento é uma lista de defeitos e seria fácil ler o
conjunto como frágil. Não é. **[medido aqui]**, em todos os casos com o denominador verificado:

| Grandeza | Documento | Medido | |
|---|---|---|---|
| dataset de referência | 97.018 linhas / 19 mensagens / 72,93 % `unknown` | idem | ✓ |
| `but found .` | 8.843 em 5 specs (TMF 8.371, Sig 234, MD 156, SSL 51, Mac 31) | soma = 8.843 | ✓ |
| mensagens com vírgula | 27,06 % (26.251) | idem | ✓ |
| comp162 | 19.664 linhas / 15.714 mudas / 79,91 % / 16 mensagens | idem | ✓ |
| gêmeas muda↔legível | 3.950 em 101 sítios | idem | ✓ |
| gêmeas muda↔muda | 838 em 12 sítios | idem | ✓ |
| gêmeas = total de linhas legíveis | 3.950 = 3.950 | idem | ✓ |
| sítios exclusivamente legíveis | nenhum | 0 | ✓ |
| partição de sítios | 101 + 12 + 183 | = 296, o número da sessão 1 | ✓ |
| "registro que não deveria existir" | 4.788 = 30,5 % | 30,47 % | ✓ |
| specs de emissão zero | 9 das 23, por nome declarado | 14 emitem | ✓ |
| eventos órfãos | `jca` 18 em 10 specs; `jca_android` pós-gh101 = 0 | idem, lista nominal item a item | ✓ |
| advices sem `args()` | 114 com `call()`, 79 com `args()`, 16 sem | denominador fecha (+19 sem parâmetro) | ✓ |
| divergência entre conjuntos | 19 de 23 specs, 882 linhas | idem | ✓ |
| `@fail` / `ErrorDescription` no `jca` | 21 / 51 (25 de 3 args + 26 de 4) | idem | ✓ |
| invariantes | spec principal para em INV-INS-103; 109 e 110 duplos e incompatíveis; primeiro livre = 116 | idem | ✓ |
| estado das changes | gh100 com 3 tarefas abertas; gh101 84/84 e gh102 28/28 completas e **não arquivadas**; primeiro `gh` livre = 104 | idem | ✓ |

A decomposição de §3.1 do `_lacunas.md` — o achado central da sessão 2 — **reproduz linha a linha**,
inclusive os três desvios declarados (−2, +1, +1). É o trabalho mais confiável da linhagem.

---

## 3. Frente A — os defeitos de consistência

### 3.1 Os três números que não reproduzem

**(a) `jca_android` tem UM `@fail` sem `__RESET`, não cinco.** **[medido aqui]** Contando blocos
`@fail` com chaves balanceadas nos dois conjuntos: **21 `@fail` em cada, exatamente 1 sem `__RESET`
em cada, e é o mesmo arquivo** — `KeyPairGeneratorSpec.mop` (`jca:110`, `jca_android:137`). Logo
`_lacunas.md:565` (*"cinco `@fail` não têm `__RESET`, contra um único no `jca`"*) é falso, e
`_lacunas.md:633` (*"medido: é o único nos dois conjuntos"*) é verdadeiro. **Os dois vivem no mesmo
documento, a 68 linhas de distância**, e o falso é apresentado como *"nota de contraste para o
dimensionamento de C-4"* — isto é, como custo de `jca_android`, a favor da decisão D-A=(ii) já
tomada. Nesse eixo os dois conjuntos são idênticos e a nota não dimensiona nada.

**(b) Não são 97 % da categoria `UnsafeAlgorithm`, são 38 %.** **[medido aqui]** A categoria tem
**15.444** linhas no dataset de referência; as **6.048** de `_lacunas.md:170` são a fatia do
`MessageDigestSpec`. Dela, **5.892** nomeiam MD5/SHA-1/SHA1/SHA — e não 5.891: falta a única linha
`but found SHA.`, o dígito que denuncia número transportado. Sob o oráculo api30 desapareceriam
5.892 de 15.444 = **38,15 %**, concentradas numa spec. Isto importa porque é a evidência que dá
consequência a **D-B, a única decisão ainda pendente**: a urgência cai por um fator de 2,5 e o alvo
fica mais nítido — é uma decisão sobre MD5/SHA-1 no `MessageDigestSpec`, não sobre o catálogo.

**(c) O ganho de C-1a é 3.151, não 6.033.** **[medido aqui]** `_lacunas.md:351` marca
`SecureRandomSpec` (2.882 mudas) como "sim" na coluna *"afetada pela aridade `args()`"*, ao lado de
TMF e KMF, enquanto `:671` credita a C-1a apenas 3.151 (TMF 2.855 + KMF 296). O perfil de sítios
decide: as mudas de TMF caem em `platformTrustManager` (2.540), `findTrustManager` (82),
`newTrustManager` (64) — aquisição e inicialização; as de KMF em `newKeyManager` (191) e
`createDefaultX509KeyManager` (105) — idem; as de `SecureRandomSpec` caem em `secureRandomBytes`
(731), `invokeSuspend` (1.152), `randBytes` (204), `secureRandomUuid` (201), `getEntropy` (118) —
**sítios de geração de bytes**. É a assinatura do falso positivo do `next2`, reparo de autômato
(lane C), não de weaver. O `FINAL:242` já dizia isso. A marca "sim" é sobre o mecanismo existir na
spec, não sobre as 2.882 linhas virem dele, e sem nota alguém soma 6.033.

Três contagens menores caem junto, todas por não terem sido medidas: os "730 arquivos com 10
colunas" são **725 + 1 vazio** (o 730 saiu de 784 − 54, absorvendo em silêncio quatro arquivos
dentro de `backup/`); as 115 linhas do `mop_diff_ajc_x_dexlib2.csv` cobrem **22 APKs**, não 41; e as
1.163 linhas legíveis do `MessageDigestSpec` têm **dois** emissores com mensagem byte-idêntica
(`update:69-70` e `d2:91-92`), de modo que atribuí-las a `update` é uma afirmação por evento que os
dados não suportam — precisamente o que o documento existe para tornar possível.

### 3.2 A razão escrita de uma decisão tomada é uma alegação retratada

`_lacunas.md:702` justifica a decisão "corrigir o documento antes de abrir issues" com *"o §4 é
citado como fonte por §5–§9, e **111 dos seus 225 IDs não têm referente possível (§2.1)**"* — e
`_lacunas.md:59-68` é exatamente onde essa alegação é **retirada** (*"Falso, e retirado"*), com
cinco IDs testados resolvendo para conteúdo real e o denominador corrigido de 116 para 581. A
citação `(§2.1)` aponta para a seção que a desmente.

A decisão continua defensável pelos outros motivos — o erro `okio.`/85,44 % em `FINAL:114`, que o
default de D-F herda; e o esquema `A/B/C` que nenhuma fonte usa. Mas a razão registrada caiu, e ela
reaparece duas vezes mais: em `_lacunas.md:719-721`, que manda **"reintroduzir"** o falso negativo
do `KeyGeneratorSpec` quando o próprio documento estabeleceu que ele sobrevive como o token opaco
`D11` (o trabalho é desopacificar, não reintroduzir); e em `_lacunas.md:787-788`, que reinstala a
dúvida sobre os IDs "agora com a ressalva mais séria" — no lugar mais visível para quem for abrir
issues.

### 3.3 Nove citações "review §X" do `FINAL.md` são falsas ou imprecisas

A sessão 1 achou uma (F10, que promove um item marcado `U` a fato estabelecido citando uma seção do
review que diz o contrário). Existem mais oito, e o padrão é o mesmo: o cabeçalho de §2 declara
*"Verified in source by the review and re-verified by ≥2 external validations unless marked"* e a
tabela não sustenta a frase.

- **F6** cita "review §1-L6/L7" para dois fatos que estão em **review §3.7** — e a §3.7 os arquivava
  como *workstreams faltantes*, não como fatos assentados.
- **F3** cita "review §1-§4" para "15/23 monitores atômicos"; o review diz **16/23**, duas vezes.
- **F8** cita "review §5" para três números de linha (`result_processor.py:631,999,1038`) que **não
  existem no review**, e marca o item de origem como `R` ("já verificado no review").
- **F8** estabelece como fato o comportamento do `violations.py` da gh103 que a linha `c-A32` do
  próprio §4 marca **`U`** — o mesmo defeito de F10, na segunda ocorrência.
- **F2** cita "review §2" para uma afirmação que está em review §0, acrescenta uma lista de
  substituições que **não aparece no review**, e larga o marcador "UNVERIFIED in an rvsec oracle"
  que a fonte carregava.
- **F5**, **c-C7** e **F4**: seção errada, seção errada e deriva de linha não declarada.

### 3.4 O que a §7.1 não cobre

Das 11 correções prescritas, **sete nascem incompletas ou erradas** à luz das quatro decisões
tomadas. As duas mais graves:

**O item 7 remove `st` do contrato e não manda tocar a §7.2**, que continua prescrevendo
`int stateBefore`, `stateBefore = getState();` em cada corpo de evento e o texto de código
`<SPEC>-ORDER-00 = "sequence violation at event ev in state st"` (`FINAL:336-343`). Depois da
correção, o documento fica com um contrato sem `st` e um mecanismo que ainda o escritura.

**O item 10 carrega só uma das quatro componentes de D-C.** A decisão tem regra em três cláusulas,
teste que a fixa, sítio declarado fora de escopo (advices `before`) e **ordem obrigatória** — fechar
antes as tarefas 7.4–7.6 da gh100, que estão abertas **[medido aqui: 3 de 58]**. O item traz a
regra. E `FINAL:293` continua condicionando D-C a *"if Study 03 has not started its final runs"*,
condição já resolvida.

Além disso, **nenhum item registra as quatro decisões no §6 do alvo**: `FINAL:289-299` continua
apresentando D-A e D-C como abertas com "recommended default".

E ficaram **órfãos** dois requisitos que a própria sessão 2 derivou (o parser de C-1 tratar aspa não
fechada como registro truncado; o teto em `val`, que não tem limite em camada alguma), mais três
recomendações da sessão 1: **prólogo de condição e herança por clone** (a decisão `st` não os
resolve — `lastEventName` continua sendo escrituração spec-side sujeita aos dois), o **split de C-V**
em V-a/V-d, e a **renegociação do critério 8**, que D-A=(ii) piorou: a conjunção READY é definida
sobre `jca_android` (`fase0/pre_registro.md:10`), logo fica indefinida por construção para `jca_v2`.

### 3.5 Defeitos do `FINAL.md` que as duas análises não pegaram

Os quatro mais concretos, todos **[medido aqui]**:

- **`*-NOOBS-*` aparece uma única vez no documento inteiro** (`FINAL:381`), dentro do critério de
  aceitação 2. Nenhuma tabela de códigos o define; nenhuma tarefa de §8 é dona de emitir valor
  observado. O critério exige um código que não existe.
- **A escada B0→T0→T1→T2 é declarada *"adopted in §8"*** (`FINAL:212`) e §8 não a menciona.
- **D-E é opção não agendada e tarefa agendada ao mesmo tempo**: `FINAL:295` diz que bloqueia O-4,
  `:485` marca O-4 como não agendada, `:457` põe o contador de suprimidos como tarefa 4 de C-2, e o
  critério 7 (`:389`) o exige.
- **A lane A nomeia `rv-experiment`** (`FINAL:398`) e nenhuma linha da tabela de §8 o lista.

E um defeito de raciocínio na abertura: **§1 compara percentuais de dois corpora não comparáveis
para afirmar regressão** (72,93 % de 97.018, dez colunas, múltiplas ferramentas, contra 79,9 % de
19.664, onze colunas, um ensaio) — quando parte do aumento é, medidamente, uma família de gêmeos que
**apareceu** como efeito colateral da gh100. É o parágrafo designado para virar a issue.

### 3.6 As listas de extração reproduzem, mas não são somáveis

Os quatro totais conferem exatamente (202+193+113+73 = 581; 450+70+61 = 581), e cada linha existe.
**Mas as quatro listas não compartilham definição de "item" nem escala de transporte.** Duas delas
declaram a mesma regra de fusão e diferem por 1,87× em itens por linha de fonte; uma conta linhas de
tabela de veredito; outra acrescenta os estados `PARCIAL — INVERTIDO` e `CARREGADO por referência`.
A prova é que **seis fatos recebem estados diferentes conforme quem classifica, contra a mesma
célula do `FINAL`** — o funil 661/207/136 é simultaneamente CARREGADO, PARCIAL, PARCIAL e AUSENTE.
Somar 148 + 166 + 84 + 52 através dessas escalas produz um número sem significado único.

Descontando ~15 itens de repetição pura entre listas e seis classificações erradas, a contagem
honesta de ausências distintas é **≈ 40, não 61**. E uma das doze "ausências que mudam trabalho"
precisa mudar de palavra: `logcat_parser.py:306` **não** está ausente — `FINAL:166` traz as duas
palavras *"prose discriminator"* dentro de uma linha que comprime seis itens. Verifiquei o código
(`logcat_parser.py:305`: `if message.endswith("went into an error state.")`, casamento por sufixo
exato). Não é ausência nem transporte: é **token opaco**, a mesma patologia do `D11`. A consequência
que muda trabalho — que C-3 reescreve o texto de todo `@fail` e reroteia essas linhas para o
fallback de malformado — continua não estando em lugar nenhum.

---

## 4. Frente B — o que deixamos passar

### 4.1 O documento amputou 76 % dos arquivos de especificação sem declarar

#### 4.1.1 O tamanho da amputação

**[medido aqui]**, varrendo os quatro diretórios de `rvsec/rvsec-mop/src/main/resources/`:

| conjunto | arquivos | com `addError` | com `Log.v` direto | selecionável na CLI |
|---|---|---|---|---|
| `jca` | 23 | 21 | 0 | sim |
| `jca_android` | 23 | 21 | 0 | sim |
| **`generic`** | **118** | **0** | **118** | **sim** |
| **`generic_new`** | **27** | **0** | **27** | não |

**145 dos 191 arquivos `.mop` da árvore (75,9 %) não passam pelo `ErrorCollector`/`ErrorDescription`
em ponto algum.** O contrato de relatório desenhado em `FINAL` §7.1 — o envelope `key=value`, o
campo `code`, a identidade de dedup do `ErrorSummary`, as colunas do `errors.csv`, o `codes.csv` por
conjunto — é definido inteiramente sobre a família `jca`, que são os outros 46 arquivos.

#### 4.1.2 O que o conjunto `generic` de fato emite

`jca/*` compõe um `ErrorDescription` com tipo, spec, localização e (em 26 dos 51 sítios) texto. O
conjunto `generic` faz outra coisa. `generic/FSM100.mop:43-47`, lido por inteiro, é o arquivo
canônico — e os 118 são idênticos exceto pelo nome:

```java
  @fail {
         //android.util.Log.v("RVSEC",__DEFAULT_MESSAGE);
         android.util.Log.v("RVSEC",__LOC + " ::: FSM100 went into an error state.");
         __RESET;
  }
```

**[medido aqui]** os 118 arquivos têm exatamente 2 sítios `Log.v` cada — um comentado com
`__DEFAULT_MESSAGE`, um ativo — e o texto ativo colapsa em **uma única forma**: `<Spec> went into an
error state.` Não há `ErrorType`. Não há valor observado. Não há nome de classe monitorada. Não há
nome de evento. O conjunto inteiro tem **uma** mensagem, parametrizada apenas pelo nome da
especificação. Se o problema que a linhagem estuda é "19 mensagens distintas para 97.018 registros",
o conjunto `generic` é o caso degenerado do mesmo problema levado ao limite: **118 specs, uma
mensagem**.

E a mesma leitura mostra um segundo defeito que nenhum documento posterior ao plano cita:
`FSM100.mop:6` importa `java.awt.TextArea` e monitora `TextArea.new()`, `setEditable`, `append`,
`setBounds`. **[medido aqui] 32 dos 118 arquivos importam `java.awt` ou `javax.swing`** — APIs que
não existem no Android. São 27 % do conjunto instrumentando classes que nunca serão carregadas.

#### 4.1.3 O conjunto `generic_new` usa um terceiro formato, e duas specs usam um quarto

`generic_new` não segue nenhum dos dois padrões anteriores. **[medido aqui]: zero dos 27 arquivos**
usam o sufixo `went into an error state`; usam `__LOC + " ::: <Spec> <texto descritivo>"` —
`generic_new/CharSequence_NotInSet.mop:25,32`. É um formato melhor (o texto descreve o defeito), e é
**um terceiro formato de transporte** que a §7.3 do documento alvo não lista.

Duas specs usam um quarto. `generic_new/ServerSocket_Backlog.mop:20-21` e
`generic_new/TreeMap_Comparable.mop:23-24` emitem **duas** linhas por violação, a partir de um método
auxiliar, com o prefixo literal `"[helper] ::: <Spec> "` — sem `__LOC`:

```java
android.util.Log.v("RVSEC", "[helper] ::: ServerSocket_Backlog " + msg);
android.util.Log.v("RVSEC", "[helper] ::: ServerSocket_Backlog " + "The backlog argument " + backlog + " is invalid; it should be greater than 0.");
```

e `msg` é `""` em **todos** os sítios de chamada (`:30,:36` e `:30,:36,:41,:46`), de modo que a
primeira das duas linhas é sempre vazia de conteúdo.

E os 27 arquivos carregam `@severity warning` **dentro de um bloco javadoc**
(`CharSequence_NotInSet.mop:17`), inerte em tempo de execução — a severidade é exatamente o campo
que o plano queria (Q4) e que o envelope de §7.1 não tem.

#### 4.1.4 O que o parser de produção faz com cada um desses formatos

`modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py`, lido nos três ramos:

**`generic` (118 arquivos)** casa o **Formato 1** (`:305`, `message.endswith("went into an error
state.")`) e vai para `_parse_generic_spec_error` (`:374-398`). O regex extrai `class`, `method`,
`file_name`, `line_number` e `spec` — e o construtor logo acima (`:307-315`) descarta o
`line_number` e passa `error_type := spec`. Ou seja: para 118 das 191 specs da árvore, o tipo de
erro é **fabricado** a partir do nome da spec e o número de linha é **medido e jogado fora**.

**`generic_new` (25 dos 27)** não casa o Formato 1 (o sufixo é outro) nem o Formato 2 (não tem seis
vírgulas). Cai no **Formato 3** (`:355-372`), que fabrica **duas** coisas: `error_type := spec`
(primeira palavra depois do `:::`) e `source := "Unknown Source:1"` — descartando o `file:line` real
que o `__LOC` acabou de fornecer.

**As duas specs `[helper]`** não casam formato algum. No Formato 3, `split[0]` é `"[helper] "`, o
`rfind(".")` devolve −1, e a execução chega ao fallback de `:370-372`, que **loga um warning e
devolve `None`**. O registro é descartado silenciosamente e **não é contado** — o que viola
`INV-CAN-04` (`openspec/specs/campaign-analysis/spec.md:50`: *"No loader or reader SHALL silently
drop a run, a record or a line. Every omission SHALL be counted"*), invariante que a §7.3 do
documento alvo não lista.

#### 4.1.5 O conjunto é selecionável e nunca foi exercitado

`generic` é um valor de primeira classe do `click.Choice` da CLI
(`modules/rv-experiment/src/rv_experiment/__main__.py:443`: `["jca", "jca_android", "generic",
"custom"]`) e o `CLAUDE.md` do projeto o documenta como um dos três conjuntos usados **separadamente
entre experimentos**. `generic_new` **não** está na lista — só é alcançável por
`--specification-set custom`, que é o item WS-8.5 do plano, o único da WS-8 que sobreviveu (como
tarefa 6 de C-1, `FINAL:445`).

**[medido aqui]:** nenhum `errors.csv` da árvore contém uma spec `FSM*`, `CharSequence_NotInSet`,
`ServerSocket_Backlog` ou `TreeMap_Comparable`, e **os 63 manifestos de campanha dizem
`"specification_set": "jca"`**. O conjunto nunca rodou.

Isso corta nos dois sentidos, e é importante dizer os dois. **A favor do silêncio:** nenhuma medição
publicada depende de `generic`, e adiá-lo não invalida nada. **Contra:** é precisamente por nunca ter
rodado que os defeitos acima são baratos de corrigir agora e caros depois — e o documento não adia,
ele **omite**. Quem ler o `FINAL.md` conclui que o problema das mensagens tem 23 arquivos.

#### 4.1.6 O que o plano tinha e o que o documento fez com isso

O plano dedica uma seção inteira ao assunto (`20260815_javamop_mensagens.md:475-486`, com a tabela
dos quatro conjuntos e a contagem de `addError` que reproduzi acima) e a **WS-8 inteira**
(`:805-817`), em sete passos: 8.1 decidir se `generic`/`generic_new` migram para o `ErrorCollector`
ou mantêm o log direto com formato explícito e parseável; 8.2 registrar que a migração muda as
contagens (o `HashSet` dedupa, o caminho atual não); 8.3 podar as specs que importam AWT/Swing; 8.4
corrigir as duas specs inparseáveis; 8.5 registrar `generic_new` na CLI; 8.6 tornar `@severity` real;
8.7 registrar o acoplamento com o casamento por sufixo do parser.

O `FINAL.md` menciona **`generic/` zero vezes**. As quatro ocorrências da palavra "generic" são
todas `generic_new` e todas periféricas: uma nota de deriva numérica (`:120`), uma linha de tabela
(`:177`), a tarefa 6 de C-1 (`:445`) e uma errata (`:499`). Dos sete passos da WS-8, sobrevive o
**8.5** (registrar na CLI) e, opaco, o **8.7** (as duas palavras "prose discriminator" de `:166`,
§3.6 deste documento). Os outros cinco somem. E a lista de non-goals de `FINAL:92-93` nomeia WS-4 e
WS-5.1/5.2/5.8 — **não** a WS-8.

Nenhuma das duas análises adversariais pegou isso, e a razão é estrutural: **as duas partiram do
`FINAL.md`**. Só a leitura integral do plano revela o que não está lá. Junto com a WS-8 sumiram, sem
declaração, mais dez itens de workstream (WS-1.4 derivar as continuações legais para o *"expected one
of"* da ramificação de ordem — que era o objetivo declarado da escrituração de estado; WS-5.3, 5.6,
5.7, 7.6, 7.9, 8.1–8.4, 8.6), treze dos cinquenta defeitos D01–D50 (entre eles D13/D14, as duas
pontas do erro de `KeyPairSpec.mop:38` de §4.5; D23/D24, a divergência de escopo de §4.6; D42, a
guarda de `ViolationRecorder`), e quatro decisões que o plano reservava **explicitamente** ao
pesquisador (`plan:841`: *"These are the researcher's, not the implementer's"*) — D-3 escopo de
weaving, D-5 `IncompleteOperationError`, D-7 `generic_new` na campanha, D-8 severidade e remediação —
tomadas pelo documento ou abandonadas sem registro.

**Destino.** Uma de duas, e ambas custam um parágrafo: (a) a WS-8 vira uma mudança **C-6** com os
sete passos, ou (b) entra na lista de non-goals do §3 com a razão escrita — *"o conjunto `generic`
nunca foi exercitado em campanha; seu contrato de relatório fica fora do escopo deste programa e é
registrado como dívida"*. O que não pode continuar é o silêncio: hoje o documento afirma consertar
"a camada de reportagem" e alcança 24 % dos arquivos que a compõem, sem que o leitor tenha como
saber disso.

### 4.2 O gate formal do plano é cego para a variante majoritária do defeito

#### 4.2.1 O que o invariante diz, literalmente

`INV-INS-110` é a pedra angular formal do programa: o gate **G-2** o codifica (`FINAL:370`), a §7.4
o exige do conjunto sucessor, a tarefa 2 de C-V o implementa como pytest, e foi rodando-o que a
sessão 1 produziu seu achado principal (os 18 eventos órfãos do `jca`). Texto integral, em
`openspec/changes/gh101-jca-spec-conformance/specs/instrumentation/spec.md:47`:

> **INV-INS-110**: An event that appears in a specification's event list MUST appear in that
> specification's `fsm` or `ere`. An event bound but absent from the automaton receives a transition
> row to `fail` from every state, which turns the specification into an unconditional accuser.

O invariante é sobre **presença**: o evento tem de *aparecer* no autômato. Não diz nada sobre o que
acontece depois que ele aparece. É essa distância entre *aparecer* e *ser adequado* que a variante
majoritária do defeito ocupa.

#### 4.2.2 Duas formas do mesmo defeito, e o gate só vê uma

**Forma A — o evento não tem linha nenhuma.** O gerador lhe dá uma linha para o sink a partir de todo
estado. Toda ocorrência do evento produz `@fail` e `unknown`. São os 18 órfãos em 10 specs, que o
gate pega, que a sessão 1 publicou e que a gh101 reparou em `jca_android`.

**Forma B — o evento aparece, mas só como auto-laço, e o consumidor afunda a partir do mesmo
estado.** O evento *está* no autômato, então **passa no gate**. O que sinca não é ele: é a chamada
seguinte. O traço é `getInstance` inseguro → auto-laço no estado inicial → `init`/`load`/`update`/
`doFinal` a partir daquele estado → sink → `unknown`. Ou seja: **a ramificação insegura é um beco
sem saída** — o programa pode instanciar de forma insegura quantas vezes quiser, e no instante em
que **usa** o objeto inseguro, a especificação para de saber onde está e emite um registro mudo em
vez do relatório de algoritmo inseguro que ela existe para produzir.

#### 4.2.3 A anatomia, no arquivo que quase acerta

`jca/KeyManagerFactorySpec.mop:66-84` é a forma mais completa do idioma presente no conjunto
congelado, e mostra o defeito com clareza porque **quase** o evita:

```
    fsm :
      start [
        g3 -> unsafeAlg
        g1 -> waitingInit
        g2 -> waitingInit
      ]
      unsafeAlg [
        g3 -> unsafeAlg
        g1 -> waitingInit
        g2 -> waitingInit
      ]
      waitingInit [
        init -> final
      ]
      final [ ... ]
```

O estado `unsafeAlg` existe, é dedicado, e recebe `g3` (o `getInstance` com algoritmo fora da
allowlist). O autor fez a parte difícil. Mas **`unsafeAlg` não tem linha `init`** — e `start` também
não. Logo `KeyManagerFactory.getInstance(algoritmoInseguro); kmf.init(...)` afunda. A minimização
funde `start` e `unsafeAlg` (têm saídas idênticas), e é por isso que a tabela compilada mostra `g3`
como auto-laço no estado 0 e `init` indo ao sink a partir do 0.

O mesmo em ERE, `jca/MessageDigestSpec.mop:108`:

```
ere : (g4* g1 | g4* g2 | g4* g3) (d2 | (update+ (d1 | d2 | d3)))+
```

`g4` é o `getInstance` inseguro, e ele aparece — como **prefixo** `g4*`, isto é, só é aceito *antes*
de um `getInstance` seguro. `MessageDigest.getInstance("MD5"); md.update(x)` não está na linguagem.
Afunda.

#### 4.2.4 Quem passa limpo no gate carregando o defeito

**[medido aqui]** sobre as tabelas compiladas de `results/gh56-smoke/monitors/MultiSpec_1RuntimeMonitor.java`,
com o volume medido sobre o comp162:

| spec | órfãos (Forma A) | evento com auto-laço | eventos que afundam do estado 0 | mudas | legíveis |
|---|---|---|---|---|---|
| `CipherSpec` | **0** | `g3` | `i1, i2, u1..u5, wkb1, f1, f2, f3, f5, f6, f7` | 1.461 | 12 |
| `KeyStoreSpec` | **0** | `g2` | `load, store, ge1, se1, gk1` | 1.136 | 265 |
| `KeyManagerFactorySpec` | **0** | `g3` | `init, gkm1` | 296 | 0 |
| `MacSpec` | **0** | `g3` | `i1, i2, update, f1, f2` | 145 | 4 |
| `KeyGeneratorSpec` | **0** | `g3` | `init, gk1` | 0 | 0 |
| *(subtotal invisível ao gate)* | | | | **3.038** | |
| `MessageDigestSpec` | 1 (`reset`) | `g4` | `update, d1, d2, d3` | 2.008 | 1.163 |
| **total da família** | | | | **5.046** | |

**Cinco especificações passam limpas no gate G-2 enquanto carregam o defeito: 3.038 linhas mudas,
19,3 % do corpus.** Somando o `MessageDigestSpec` — que o gate pega, mas por outro evento (`reset`),
de modo que reparar o órfão não repara a Forma B — a família responde por **5.046 mudas, 32,1 %**.
Corrigi aqui a leitura do subagente, que atribuía os 32,1 % ao conjunto invisível ao gate: os 32,1 %
são da família; o que o gate **não vê** são 19,3 %.

Dois sinais de que a leitura está certa. `KeyManagerFactorySpec`: **296 mudas, zero legíveis** — a
spec nunca consegue dizer nada, embora tenha um estado dedicado ao algoritmo inseguro. E
`CipherSpec`: **1.461 mudas contra 12 legíveis**, com os maiores sítios em `AndroidKeystoreAesGcm` e
`PrfAesCmac` — código que instancia e imediatamente usa.

#### 4.2.5 Os autores já resolveram isto duas vezes, e nenhum documento cita

**Primeira vez, dentro do conjunto congelado.** `jca/MessageDigestSpec.mop:47-52`, comentário
verbatim, imediatamente acima do evento `g4`:

> *"We no longer throw errors after unsafe instantiation events, otherwise we would throw
> InvalidSequenceOfMethodCalls in cases like (g3\* g1 | g3\* g2). Not throwing here eliminates the
> InvalidSequenceOfMethodCalls false positive in bench02.BrokenHashABPSCase1"*

e logo abaixo, `:56-57`, o `addError` de `UnsafeAlgorithm` **comentado** — a metade do reparo que
eles executaram: tirar o relatório do evento de instanciação. A outra metade — dar ao evento
inseguro um estado com o mesmo alfabeto de saída do seguro — eles fizeram só como prefixo `g4*`, e é
por isso que o defeito sobrevive na spec de maior volume legível do corpus.

**Segunda vez, na gh101, redescoberto de forma independente.**
`jca_android/SSLContextSpec.mop:95-101`:

> *"unsafe_protocol was absent from this automaton, so the generator gave it a row sending every
> state to fail. That was inert while the missing returning clause kept it out of the context's
> parameter slice; adding the clause without this would have made every protocol outside the
> allow-list an immediate InvalidSequenceOfMethodCalls at getInstance, before any sequence violation
> exists. **unsafeProtocol mirrors the unsafeAlg state KeyManagerFactorySpec uses for the same event
> shape.**"*

A última frase é o achado inteiro, escrito pelos próprios autores: existe uma **forma de evento**
recorrente — "instanciação insegura" — e ela tem um idioma de reparo. Nenhum dos onze documentos da
linhagem cita esse comentário, nomeia a forma, ou conta quantas specs a têm.

#### 4.2.6 Correção a `_lacunas.md:637-639`

O `_lacunas.md` apresenta o estado `unsafeProtocol` como *"a forma já validada do reparo que elimina
2.916 linhas mudas"* e o oferece como atalho legítimo para `jca_v2`. **[medido aqui]** nas tabelas do
`SSLContextSpecMonitor`:

| evento | `jca` congelado | `jca_android` pós-gh101 |
|---|---|---|
| `unsafe_protocol` | `{3,3,3,3}` — órfão | `{0,3,3,3}` — auto-laço no estado 0 |
| `init` | `{3,3,1,3}` | `{3,3,1,3}` — **byte-idêntica** |

O reparo da gh101 **desorfaniza `unsafe_protocol` e não toca a linha de `init`**. Isto é: ele converte
a spec da **Forma A** para a **Forma B** — sai do radar do gate e continua com o beco sem saída.
Quanto do volume sobra depende da ordem de disparo em runtime, que as tabelas não determinam;
registro como **parcial, resíduo não determinado**, e corrijo o subagente que afirmou "metade". O
que está estabelecido é que `jca_v2` terá de decidir a linha de `init` saindo do estado novo — uma
decisão de modelagem a mais na conta de D-A=(ii), e um exemplo de que copiar o reparo do
`jca_android` sem o gate certo reproduz o defeito numa forma menos visível.

#### 4.2.7 Destino

C-V precisa de um gate **G-2b** que G-2 é incapaz de expressar, e que é tão barato quanto ele:

> Para toda especificação com um evento de instanciação insegura, o **alfabeto de saída do estado
> inseguro deve conter o alfabeto de saída do estado seguro correspondente**. Uma diferença é um
> beco sem saída e deve falhar o gate.

É computável sobre as mesmas tabelas de transição que G-2 já lê, sem CrySL, sem DFA, sem oráculo.
Sem ele, o programa entrega um conjunto formalmente "validado" carregando a variante que responde
por 19,3 % do volume mudo — e, pior, o reparo dos órfãos **converte** Forma A em Forma B, de modo
que rodar só o G-2 depois de C-4 mostraria zero violações num conjunto que piorou de visibilidade
sem melhorar de comportamento.

Nota lateral com consequência: o mesmo arquivo da gh101 já traz **`INV-INS-111`** (`:49`) — *"Every
`Property` constant written by any specification MUST be read by at least one specification, or MUST
be recorded in the deliberate-omission list"*. É exatamente o gate que §4.5 deste documento pede, ele
**já está escrito**, e o `jca` o viola 18 vezes. Nenhum documento da linhagem o cita.

### 4.3 Vinte e seis eventos são despachados ao slice global, e ninguém enumerou a classe

#### 4.3.1 O mecanismo

JavaMOP fatia monitores por parâmetro de especificação, e liga um evento ao parâmetro **por nome**.
Um evento que não menciona o nome declarado na assinatura da spec — porque liga um nome diferente,
ou porque não tem `returning`, ou porque a spec não declara parâmetro nenhum — **não carrega
parâmetro**. O gerador não o rejeita nem avisa: ele o despacha para o **slice-raiz**, isto é, um
monitor único por processo, e daí o difunde a todos os monitores vivos daquela especificação. Os
monitores novos nascem como clone da raiz (`BaseMonitor.java:760-769`, `clone()` raso), herdando
estado, flags e campos declarados pelo usuário; e um `__RESET` disparado a partir da raiz reinicia
todos.

Consequência prática: para esses eventos a especificação deixa de ser "uma máquina por objeto
monitorado" e vira "uma máquina para o processo". A sequência de um objeto determina o veredito
sobre outro.

#### 4.3.2 A enumeração, por duas derivações independentes

**[medido aqui]**, por dois caminhos que não compartilham nada:

1. **Do artefato gerado** — um evento está no slice-raiz se e só se seu método `*Event` resolve
   `matchedEntry = <Spec>__Map;` em vez de um mapa de parâmetro. Sobre
   `results/gh56-smoke/monitors/MultiSpec_1RuntimeMonitor.java`.
2. **Do texto-fonte** — comparar o nome do parâmetro declarado na assinatura da spec com os nomes
   ligados nos argumentos e no `returning` de cada evento, nos 23 `.mop` do `jca`.

As duas dão **o mesmo conjunto: 26 eventos em 10 especificações.**

| spec | eventos no slice-raiz | causa, no `.mop` |
|---|---|---|
| **`KeyStoreSpec`** | **7 de 7** — `g1, g2, load, store, ge1, se1, gk1` | `:21` declara `KeyStoreSpec(KeyStore ks)`; todo evento liga `k` (`returning(KeyStore k)`, `target(k)`) |
| `CipherOutputStreamSpec` | **5 de 5** — `c1, w1, w2, fl, cl` | `:11` declara `CipherOutputStreamSpec()` — **sem parâmetro de especificação** |
| `CipherInputStreamSpec` | **4 de 4** — `c1, r1, r2, cl1` | `:11` — idem |
| `TrustManagerFactorySpec` | `g3`, `gtm1` | `:21` declara `mf`; `:44` e `:62` ligam `k` |
| `PBEKeySpecSpec` | `f1`, `f2` | `:21,:27` não têm `returning` |
| `RandomStringPasswordSpec` | `vo`, `gb` | `:9` declara `str`; `:11,:18` ligam `s` |
| `SSLContextSpec` | `unsafe_protocol` | `:46` não tem `returning` |
| `HMACParameterSpecSpec` | `c` | `:17` declara `hmacParameterSpec`; `:21` liga `s` |
| `KeyPairSpec` | `c1` | `:19` declara `keyPair`; `:23` liga `kp` |
| `MacSpec` | `f2` | `:76` usa `target(m)`, onde `m` é o parâmetro da spec e não um parâmetro do advice |
| **total** | **26 de 134 eventos (19,4 %)** | |

Note-se a natureza dos casos: **nenhum é uma decisão de modelagem**. São divergências de uma palavra
(`ks` × `k`, `str` × `s`, `keyPair` × `kp`, `mf` × `k`, `hmacParameterSpec` × `s`) e duas
especificações que simplesmente não declaram parâmetro.

#### 4.3.3 `KeyStoreSpec`: um monitor para o processo inteiro

É o caso mais grave e o mais fácil de ler. `jca/KeyStoreSpec.mop:21` declara `KeyStoreSpec(KeyStore
ks)`; o evento `g1`, três linhas abaixo, escreve `returning(KeyStore k)`. O nome `ks` não aparece em
evento algum. **Os sete eventos vão para o slice-raiz**, e a especificação inteira passa a operar
sobre um único monitor global.

Composto com a Forma B de §4.2 — `KeyStoreSpec` tem `g2` (o `getInstance` com tipo fora da
allowlist) como auto-laço e `load`/`store`/`ge1`/`se1`/`gk1` afundando a partir do mesmo estado — a
assinatura observável fecha exatamente. **[medido aqui]** no comp162: 1.401 linhas, **1.136 mudas**,
41 sítios, com os maiores sítios em código que abre `"AndroidKeyStore"` (fora da lista de cinco tipos
de `:23`) e imediatamente o usa:

| linhas mudas | sítio |
|---|---|
| 131 | `AndroidKeystoreKmsClient$Builder.<init>` — `AndroidKeystoreKmsClient.java:96` |
| 131 | `AndroidKeystoreAesGcm.<init>` — `AndroidKeystoreAesGcm.java:59` |
| 117 | `MasterKeys.keyExists` — `MasterKeys.java:157` |
| 48 | `TlsUtil.newEmptyKeyStore` — `TlsUtil.kt:111` |

`KeyStoreSpec` é o **terceiro maior produtor de linhas mudas do corpus**, e na tabela de decomposição
por spec de `_lacunas.md:355` ele aparece com **travessão nas duas colunas explicativas** (eventos
órfãos e aridade `args()`) — isto é, classificado como **não explicado**. Ele é explicado: pela
composição de §4.2 com §4.3.

O segundo caso mais nítido é `KeyPairSpec`: **[medido aqui]** 111 linhas, **111 mudas, zero
legíveis**, em 11 sítios que vêm em pares de linhas consecutivas — `TLSClientHandshake.kt:520/521`
(18 e 23), `:524/525` (18 e 23), `CryptoUtil.java:65/66` (12 e 12). São `getPublic()` e
`getPrivate()` sobre um par de chaves recém-gerado, vistos por um monitor global que nunca observou
o `c1` correspondente — porque `c1` é justamente o evento no slice-raiz. E é a mesma spec cujo
`gpr` grava no slot errado (§4.5): o defeito de fatiamento e o defeito de predicado se somam no
mesmo arquivo de 43 linhas.

#### 4.3.4 A gh101 reparou cinco casos sem nomear a classe

A comparação entre os três oráculos gerados dá a trajetória: `results/gh99_jca_android_monitors/`
(pré-gh101) tem 26 de 134 — os mesmos do `jca`; `results/gh101_group8_jca_android/` (pós-gh101) tem
**21 de 140**. A gh101 reparou cinco (`PBEKeySpec f1,f2`; `SSLContext unsafe_protocol`; `TMF
g3,gtm1`) — e o comentário de `jca_android/SSLContextSpec.mop:95-98` mostra que o autor entendeu o
mecanismo naquele caso específico (*"That was inert while the missing `returning` clause kept it out
of the context's parameter slice"*). Mas a classe não foi nomeada, não foi enumerada, e **os sete
eventos do `KeyStoreSpec` e os nove das duas specs de stream continuam no slice-raiz no conjunto que
a auditoria examinou 22/22**. (Esta contagem por conjunto vem do subagente; verifiquei o conjunto do
`jca` pelas duas derivações, não reexecutei a comparação de trajetória.)

#### 4.3.5 O que os documentos dizem

`FINAL:68` (F5) enuncia o mecanismo corretamente e nomeia **dois** exemplos — `unsafe_protocol` sem
`returning` e `g3` ligando `k` — usados anedoticamente para explicar contaminação em `SSLContextSpec`.
A sessão 1 usa o mesmo fato para argumentar sobre herança por clone (`_analise.md:208-212`). A
sessão 2 não o reabre. **Nenhum dos onze documentos enumera a classe, conta os 26, ou liga o
mecanismo ao `KeyStoreSpec` e ao `KeyPairSpec`** — que juntos são 1.247 linhas mudas, 7,9 % do
corpus, e ambos marcados como não explicados.

#### 4.3.6 Destino

Um lint **G-1b** em C-V, computável sobre o monitor gerado em uma passada, sem CrySL e sem DFA:

> Nenhum evento pode resolver `matchedEntry` para `<Spec>__Map`. Um evento sem parâmetro de
> especificação é difundido ao processo inteiro e deve falhar o gate, salvo registro explícito de
> que a difusão é intencional.

Os reparos são de C-4 e são triviais: renomear a variável ligada para o nome do parâmetro da spec
(entre 1 e 7 edições de uma palavra por arquivo) e dar parâmetro de especificação às duas specs de
stream. Nenhuma mudança semântica além do fatiamento correto — e é o tipo de reparo que precisa de
gate justamente porque não muda nada visível no texto-fonte, só no artefato gerado.

### 4.4 O censo de mensagens que mentem, que a linhagem nunca fez

O documento é sobre mensagens e nunca perguntou se o texto transportado é **verdadeiro**. Das 26
chamadas de 4 argumentos do `jca`:

- **A mensagem contradiz a condição que a dispara.** `PBEKeySpecSpec.mop:48-50` testa
  `iterationCount < 10000` e diz *"should be >= 1000"* — fator de 10, **52 linhas** no comp162.
  `PBEParameterSpecSpec.mop:46-50` repete a mesma mentira.
- **`ErrorType` incompatível com o que é testado.** `PBEParameterSpecSpec.mop:49` usa
  `UnsafeAlgorithm` para uma restrição de contagem de iterações; a checagem idêntica três arquivos
  adiante usa `UnsatisfiedConstraint`. `SecretKeySpecSpec.mop:48,55` usa `UnsatisfiedConstraint`
  para meio teste de catálogo de algoritmo — **820 linhas**, 100 % da saída legível daquela spec.
- **A mensagem descreve o conjunto aceito errado.** `MessageDigestSpec.mop:70,92` diz *"expecting
  one of {SHA-256, SHA-384, SHA-512}"* enquanto a lista em `:16` tem **seis** entradas. **1.163
  linhas** no comp162 e três das 19 mensagens do artigo. Quem agir sobre essa mensagem faz uma
  mudança que não muda nada.
- **Divergência de formatação dentro do mesmo corpus.** `KeyStoreSpec.mop:68` esquece o espaço →
  `expecting one ofJCEKS,JKS,...` — **265 linhas**, 100 % da saída legível da spec.
- **As 8.843 linhas `but found .` têm causa nomeável:** todas interpolam um **campo**
  (`currentAlgorithmInstance`, `currentProtocol`, `currentKSType`), vazio até que um evento de
  instanciação dispare no mesmo slice — o que eventos não ligados (§4.3), órfãos (§4.2) e `__RESET`
  rotineiramente impedem. O código comentado dos próprios autores em `MessageDigestSpec.mop:57-58`
  interpola o **argumento** e não teria esse modo de falha.

**Destino:** C-3, como **pré-condição e não consequência** — C-3 reescreve toda mensagem; se o fizer
sobre um `ErrorType` errado e uma constante errada, o envelope passa a carregar um `code` que
certifica uma mentira. E o gate **G-6 precisa de uma propriedade que não tem**: *os literais
numéricos da mensagem devem casar com os literais numéricos da condição que a guarda* —
sintaticamente verificável.

### 4.5 O grafo de predicados: uma aresta morta que é um erro de digitação

**[medido aqui]** no `jca`: 21 propriedades escritas (49 sítios `setProperty`), 4 lidas (27 sítios
`validate`), interseção **3**. `GENERATED_PRIVATE_KEY` é **lida uma vez e escrita zero vezes**;
`GENERATED_TRUST_MANAGERS` é removida e nunca escrita; **35 dos 49 sítios de escrita (71 %) gravam
numa propriedade que nenhum `.mop` lê**.

A leitura morta é `jca/CipherSpec.mop:72`. O produtor existe e escreve a constante errada —
`jca/KeyPairSpec.mop:35-39`:

```
event gpr after(KeyPair keyPair) returning(PrivateKey privateKey):
  call(public PrivateKey KeyPair.getPrivate()) && target(keyPair) {
    ExecutionContext.instance().setProperty(Property.GENERATED_PUBLIC_KEY, privateKey);
}
```

O evento chamado `gpr`, ligado a `getPrivate()`, retornando `PrivateKey`, grava no slot da chave
**pública**. `jca_android/KeyPairSpec.mop:58` grava `GENERATED_PRIVATE_KEY` no sítio idêntico — a
gh101 corrigiu exatamente esta palavra sem registrar como divergência.

Consequência: `Cipher.init(mode, privateKey)` depois de `KeyPair.getPrivate()` reprova a condição de
`i2`, o evento não dispara, o autômato não avança, e o `doFinal` seguinte afunda. `CipherSpec` tem
**1.461 mudas contra 12 legíveis**.

**Destino:** uma palavra em `jca/KeyPairSpec.mop:38` (C-4, sem questão de oráculo). E um gate
**G-7a** em C-V que roda hoje, sem CrySL: *toda `validate(P,…)` precisa de um `setProperty(P,…)` no
conjunto; todo `setProperty(P,…)` precisa de leitor ou de registro explícito de "inalcançável"*. O
plano agenda isso atrás de verificação de modelo limitada; é nível `grep`.

### 4.6 O escopo de instrumentação e o de cobertura discordam

**[medido aqui]** `PackageFilter.java` exclui **16** prefixos, entre eles `Landroid/`, `Landroidx/`,
`Lkotlin/`, `Lkotlinx/`, `Lcom/google/`. O aspecto gerado exclui **12 pacotes** e **nenhum** desses.
O weaver de MOP instrumenta exatamente os namespaces que o filtro de cobertura descarta, e não há
opção de CLI para escopo. Como `okhttp3.internal.platform.Platform` sozinha responde por 30,4 % das
linhas do comp162, isso contamina o denominador de todo número que C-0 vai publicar — e D-F debate
como **classificar** linhas de terceiros depois de coletadas, sem notar que a política de coleta já
é assimétrica. Era o D-23/D-24 do plano; sumiu.

### 4.7 As opções, reavaliadas sob as decisões tomadas

Quatro mudam de estado, todas com medição:

**O-1 (gerador emite `__EVENTNAME`) — PROMOVER.** O denominador declarado está errado por fator 6,4:
a escrituração de C-3 não é de "21 arquivos", é de **134 corpos de evento**, um `lastEventName` cada.
Com `st=` fora, O-1 perde metade do payload (`__PREVSTATE` morre) e **não perde nada do custo que
evita**. E o gerador **já emite exatamente esse código hoje**, atrás da flag `--internalbehavior`
(`BaseMonitor.java:410-414`), com o nome declarado do evento. A razão é 134 hunks manuais contra 2
sítios no gerador. Ressalva medida: O-1 **não** resolve a não-injetividade — `GCMParameterSpecSpec`
declara **dois eventos ambos chamados `c1`** **[medido aqui, nos dois conjuntos]**, e o gerador
emitiria `"c1"` duas vezes. Isso também derruba a justificativa de `_lacunas.md:661-666`, que afirma
que nome de evento é estável e que `ev` + `code` identificam *"sem ambiguidade"* — é a única
propriedade que sobra no gate G-6 depois da saída do `st`.

**O-3 (`fsm:` `default`) — DESCARTAR.** Três medições independentes: a sintaxe é `default <State>`,
**sem seta** (o documento escreve `default -> S`); **13 dos 18 órfãos estão em specs `ere:`**, onde a
notação não existe; e onde é aplicável é o reparo errado, porque `default` é catch-all por estado —
absorveria `unsafe_protocol` **e junto** o `init` a partir de `start`, que é a violação que a spec
existe para detectar. O idioma correto já está no conjunto congelado
(`jca/KeyManagerFactorySpec.mop:68-77`, estado dedicado). E D-A=(ii) **não** satisfaz o gatilho
declarado ("conjunto escrito do zero"): `jca_v2` = `jca` + reparos.

**O-4 (contador de suprimidos) — PROMOVER, e resolver a contradição.** Gatilho satisfeito com folga
**[medido aqui]**: 6.344 identidades distintas para 19.664 linhas, **67,74 % de repetição** dentro da
mesma corrida, máximo 49 repetições de uma identidade. O volume dirigido por reinício domina.

**O-8 (preservação de debug items) — DESCARTAR a metade principal.** Gatilho **refutado com
denominador cheio** **[medido aqui]**: **19.664 de 19.664 linhas (100,00 %)** carregam número de
linha; **zero** terminam em `:0`. Sobra um defeito real de uma linha — a guarda de
`ViolationRecorder.java:94`, que ao ver `fileName` nulo desliga o filtro inteiro em vez de pular o
quadro — e isso é correção de C-1, não opção. **Cuidado ao descartar:** a proposta do *manifesto
estático de sítios de weaving* foi soterrada em O-8, e a motivação dela nunca foi localização — é
atribuição de sítio, que é justamente o insumo do orçamento residual. Precisa ser extraída antes.

**O-9 — dividir.** A metade de re-orçamento de alfabeto disparou por D-A=(ii) e tem número:
`jca/CipherSpec.mop` está em **17/17 eventos**, exatamente o teto de `INV-INS-115`, e D-A=(ii) proíbe
herdar o re-orçamento para 14 que a gh101 fez. Reparos de linha cabem; `updateAAD` não cabe.

### 4.8 As ausências e parciais, classificadas

Os 131 itens (61 ausentes + 70 parciais) foram classificados um a um em dois recortes disjuntos.
Resultado: **14 são melhoria real não agendada**, **97 pertencem a alguma C-\* e estão fora do
escopo declarado dela**, **11 são ruído legitimamente descartado**, e 9 já estavam nas doze
trabalhadas. Quarenta e dois são de severidade alta.

Os que mais mudam trabalho, além dos já desenvolvidos acima: as duas specs `[helper]` do
`generic_new` emitem registros que o parser de produção **não consegue ler**, com mensagem vazia, e
o descarte é silencioso e não contado (viola `INV-CAN-04`, que a §7.3 não lista); os **oito
emissores truncados** que a gh100 restaurou eram precisamente os de `UnsatisfiedConstraint` — a
única classe que carrega texto de valor, o que é a validação de resultado da gh100 e o melhor
argumento de que as mensagens de C-3 vão de fato aparecer; e o critério de aceitação 4 (*"exatamente
um registro por violação"*) é **infactível como escrito**, porque a supressão é por processo e não
há canal entre processos.

---

## 5. O que fazer, em ordem

**Antes de qualquer decisão de escopo:**

1. **Decidir o destino da WS-8** (§4.1). Ou vira C-6, ou entra nos non-goals com razão escrita. É a
   única correção que muda o tamanho do programa.
2. **Acrescentar G-2b e G-1b a C-V** (§4.2.7, §4.3.6). Os dois são lints sobre o artefato gerado,
   computáveis sobre as mesmas tabelas que G-2 já lê, sem CrySL e sem DFA. Sem eles, C-V valida um
   conjunto que ainda carrega a variante majoritária do defeito — e, pior, o reparo dos órfãos
   **converte** Forma A em Forma B, de modo que rodar só o G-2 depois de C-4 mostraria zero
   violações num conjunto que perdeu visibilidade sem mudar de comportamento.
   O terceiro gate que §4.5 pede **já está escrito**: `INV-INS-111`
   (`openspec/changes/gh101-*/specs/instrumentation/spec.md:49`) exige que toda `Property` escrita
   seja lida ou registrada como omissão deliberada. O `jca` o viola 18 vezes e nenhum documento da
   linhagem o cita — basta adotá-lo.

**Nas 11 correções da §7.1, corrigir as correções:**

3. Trocar a razão escrita da decisão de ordem (§3.2), reformular o item 2 de "reintroduzir" para
   "desopacificar", e retirar a ressalva reinstalada em §8.
4. Estender o item 7 à §7.2 (o mecanismo ainda escritura o `st` removido) e o item 10 às outras três
   componentes de D-C.
5. Corrigir os três números de §3.1 e registrar as quatro decisões no §6 do alvo.
6. Acrescentar o censo de mensagens que mentem (§4.4) como pré-condição de C-3, e a propriedade de
   literais numéricos ao G-6.

**Reavaliar as opções** conforme §4.7 antes de escrever a tabela de §9 de novo.

---

## 6. Onde esta validação corrigiu a si mesma e a seus verificadores

1. **Meu primeiro censo do grafo de predicados estava errado.** Procurei `hasProperty`/`getProperty`
   e a API real de leitura é `validate(...)`; a coluna "lida" saiu zerada para tudo. Refiz com o
   denominador certo. É a mesma classe de erro que a linhagem inteira comete e que esta sessão
   existe para pegar.
2. **Corrigi o subagente A4** sobre a ausência #6: ele a classificou como falsa porque `FINAL:166`
   traz *"prose discriminator"*. É token opaco, não transporte — a consequência que muda trabalho
   continua ausente (§3.6).
3. **Corrigi o subagente B3** na quantificação do reparo de `unsafeProtocol`: ele afirma "metade";
   as tabelas estabelecem que o reparo é **parcial**, sem determinar o resíduo, que depende da ordem
   de disparo em runtime (§4.2).
4. **Corrigi a atribuição da Forma B.** O subagente creditou 5.046 mudas (32,1 %) ao conjunto
   invisível ao gate G-2. Medindo por spec: os 32,1 % são da **família**; o que o gate não vê são
   **3.038 (19,3 %)**, porque o `MessageDigestSpec` — 2.008 mudas — é pego pelo gate, mas por outro
   evento (`reset`), de modo que reparar o órfão não repara a Forma B (§4.2.4).
5. **Não arbitrei** os percentuais por spec do §4.4 nem a trajetória 26 → 21 entre os oráculos de
   `jca_android` (§4.3.4); estão registrados como do subagente. O conjunto de 26 no `jca` foi medido
   aqui por duas derivações independentes.

---

## 7. O que continua não verificado

- **Nada foi executado em device.** Vale para todo este documento.
- **A atribuição por evento continua impossível** com os dados atuais — é o defeito que o trabalho
  existe para corrigir. As 10.926 linhas "solitárias" do comp162 permanecem sem decomposição.
- **G6 e G10 da auditoria seguem INCONCLUSIVE** e nenhuma mudança C-\* os fecha, embora o critério 8
  defina prontidão pela conjunção que os contém.
- **A bateria de replay G10 existe e está nomeada** na auditoria; nenhuma mudança a agenda, de modo
  que duas afirmações permanentemente marcadas INFERRED (F11 e a evidência de runtime de D-C) não
  têm caminho de fechamento.
- **O vazamento do `ExecutionContext`** (nunca há `reset()` em código de produção; 25 escritas em
  `acceptingState` que nada lê) é estruturalmente demonstrado e **não medido**.
- **A pendência P11 do Estudo 03** (35 JSON de Phase-7 com WTG truncado) e a P12 (denominador
  degenerado em 7 de 162 artefatos) continuam abertas e atingem qualquer linha de base que C-0
  publique.

---

## 8. Referências

- Linhagem: `docs/20260815_javamop_mensagens*.md` (13 arquivos casam o glob; o `_lacunas.md:802` diz
  11) e `docs/20260815_javamop_extracao/` (4 arquivos, 581 itens)
- Datasets medidos: `/home/pedro/.../ase-journal/dataset/results/errors.csv` (97.018 linhas, 10
  colunas); `experimento-comp162/results/*/*/errors.csv` (8 arquivos, 19.664 linhas, 11 colunas)
- Oráculos de monitor: `results/{gh56-smoke,gh99_jca_android_monitors,gh101_group8_jca_android,gh101_group8_jca_frozen_control}/monitors/`
- Specs: `rvsec/rvsec-mop/src/main/resources/{jca,jca_android,generic,generic_new}/` (23/23/118/27)
- Runtime: `rvsec/rvsec-core/` (`Property.java`, `ExecutionContext.java`, `ErrorDescription.java`),
  os dois `ErrorCollector`, `rv-monitor-rt/.../ViolationRecorder.java`
- Weaver: `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` (`WrapperEmitter.java`,
  `PointcutMatcher.java`, `coverage-weaver/.../PackageFilter.java`)
- Gerador: `rv-monitor/` (`BaseMonitor.java`, `HandlerMethod.java`, `JavaFSM.java`, `FSMParser.jj`)
- Auditoria: `audit/20260808_validacao_jca_android/` (`fase0/pre_registro.md:10` = escopo;
  `global/juizglobal_relatorio.md` §10 = veredito)
- Processo: `docs/WORKFLOW.md`, `openspec/specs/instrumentation/spec.md`,
  `openspec/changes/gh10{0,1,2}-*/`
