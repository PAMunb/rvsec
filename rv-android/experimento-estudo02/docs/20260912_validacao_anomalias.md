# Validação de anomalias da `estudo02` — catálogo, achados e detectores

**Data:** 12/09/2026 · **Estado da campanha:** 75 % feita, término previsto 13/09 à noite
**Escopo:** encontrar, antes de o número virar artigo, o defeito que passa despercebido.

## Por que este documento existe

A campanha `estudo02` repete o experimento do artigo trocando um único fator, o conjunto de
especificações `jca` pelo `jca_android`. Os números vão para a tese e para campanhas seguintes.
Uma regeração anterior de resultados (`rvsec-regerar-resultados`, out/2025) encontrou dezenas de
anomalias **depois** de os números estarem publicados, e o padrão que se repetiu lá três vezes é o
que este documento procura aqui:

1. **Fonte errada com o nome certo.** Uma coluna agregada lida de um campo homônimo que carrega
   outra grandeza. Ninguém percebe porque o nome bate.
2. **Ausência de dado vestida de zero.** Arquivo que não existe, artefato que não resolveu,
   identidade que sumiu — tudo entra na média como zero medido.
3. **Oráculo sem poder aprovando produção.** Um relatório de validação que carimba 100 % sobre uma
   amostra onde o defeito não podia aparecer.

As três têm instância viva nesta campanha. Duas estão confirmadas contra a fonte.

---

## Parte I — Achados confirmados

Só entra aqui o que eu verifiquei diretamente no código ou no dado, não o que a leitura sugeriu.

### F1 — O consolidador não conta três das 47 especificações · **corrigível, não invalida o dado**

`.claude/skills/rv-experiment-compare/scripts/consolidate_compare.py:35` conta `mop_total` com:

```python
RVSEC = re.compile(r'\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$')
```

O padrão exige que o nome da spec seja **só letras** e termine em **`Spec`**. Três dos 47 `.mop` do
`jca_android` não satisfazem isso, e testei os quatro casos contra a expressão:

| Spec | Por quê | Casa? |
|---|---|---|
| `CipherSpec` | referência | sim |
| `IvChainJunction` | não termina em `Spec` | **não** |
| `MGF1ParameterSpecSpec` | dígito `1` | **não** |
| `X509EncodedKeySpecSpec` | dígitos `509` | **não** |

**Mecanismo do dano.** Toda violação dessas três specs entra em `mop_unique`, que vem do índice de
tarefas, e **não** entra em `mop_total`, que vem desta expressão. A subcontagem não é uniforme entre
APKs: concentra-se nos que usam OAEP/MGF1 e certificados X.509, ou seja, os mais criptográficos.
Numa regressão binomial negativa sobre `mop_total`, isso é erro de medida correlacionado com o
tratamento, não ruído.

**Herança direta.** É o defeito A1 de 2025, quando um padrão de busca escrito para o formato de um
experimento foi aplicado a outro, devolveu zero violações, e a validação carimbou "100 % validado"
em cima do zero.

**O que limita o estrago.** O dado da campanha está intacto: as linhas estão nos logcats. É defeito
de consolidação e se conserta sem re-executar nada. Falta medir quantas linhas são, o que exige
ler os logcats depois de 13/09 (detector **I1**).

### F2 — `mop_unique` mistura duas eras de identidade, e o estudo é exatamente o contraste entre elas · **decisão metodológica, não bug**

Este é o achado que mais pesa sobre o artigo, e ele não é um defeito de código: é uma mudança de
definição que precisa ser declarada.

`modules/rv-android-core/src/rv_android_core/domain/log.py`, propriedade `unique_msg`, constrói a
identidade de uma violação com **sete** partes:

```
class ::: method ::: spec ::: error_type ::: code ::: event ::: message
```

A chave que a tese e o artigo usam para contar *unique misuses* tem **quatro**:
`(apk, class, method, spec)`. O próprio docstring diz, sem rodeios, que `unique_errors` e a coluna
derivada dela **não são numericamente comparáveis** a uma contagem de unique-misuse, e que
"qualquer figura publicada tem de dizer a que era pertence".

**Por que isso é pior aqui do que em qualquer campanha anterior.** Os campos `code` e `event` vêm do
envelope de mensagem v1. Um registro produzido pelo conjunto `jca` congelado **não tem envelope** e
carrega o sentinela `UNSPECIFIED` nos dois. Um registro do `jca_android` carrega os valores reais. A
`estudo02` é precisamente o contraste `jca` → `jca_android`. Logo:

> Parte da diferença que a campanha vai medir em `mop_unique` é artefato da granularidade da chave,
> não conteúdo das especificações.

E há um segundo multiplicador na mesma chave: `message` carrega o valor observado. O docstring dá o
exemplo e o defende com razão semântica — `but found MD5` e `but found SHA-1` são dois maus usos
diferentes. Mas uma aplicação que itera sobre vários algoritmos num único ponto de mau uso gera N
identidades ali, e a dispersão da variável resposta muda.

**Consequência prática.** A comparação **dentro** da `estudo02`, entre as 11 ferramentas, é
internamente consistente: todos os braços usam `jca_android`. O que não é comparável direto é a
magnitude de `mop_unique` da `estudo02` contra a do artigo. E comparar com o artigo é o propósito
declarado do estudo. Ver o detector **I5**, que produz as duas contagens lado a lado.

### F3 — O corpus passa em três portões estruturais

Rodei três checagens baratas, todas passaram:

- **Nenhum dos 163 pacotes cai sob prefixo excluído pelo instrumentador.** O mecanismo que zerou o
  `com.google.android.stardroid` — o filtro do weaver descartando o pacote do próprio app por
  parecer biblioteca — não se repete. Ressalva: a checagem foi sobre o nome no arquivo, que é
  indício; a confirmação lê `codePackage` no artefato estático (**E3**).
- **Nenhum nome do corpus carrega sufixo de build.** `RV_STRIP_BUILD_TYPE_SUFFIX` está desligado
  nesta campanha, e o risco de a chave de escopo apontar para um identificador sob o qual nada foi
  compilado não se aplica.
- **O portão de denominador não recusou nada.** 163 APKs, 163 artefatos estáticos, zero `.refused`.

---

## Parte II — O que a leitura levantou e ainda não foi verificado

Ordenado por produto de probabilidade e dano. Nenhum destes está confirmado; cada um traz o
detector que o mata ou o confirma.

| # | Risco | Mecanismo | Detector |
|---|---|---|---|
| **V1** | Perda silenciosa de linha por buffer de logcat | O logcat do Android é buffer circular. Com 10 emuladores concorrendo por disco e 47 specs emitindo mais que 23, o produtor pode superar o consumidor. Uma linha perdida **muda o veredito** de uma spec com ORDER: perder o `init` e ver o `doFinal` cria violação que não houve. Em todo o dossiê de 2025 não existe um único detector disso, e a política declarada dos parsers era engolir linha malformada em silêncio. | **L1, L2, L3** |
| **V2** | Zero por ausência de arquivo | `consolidate_compare.py` trata `FileNotFoundError` com `pass`, e `mop_total` fica 0. Indistinguível de "nenhuma violação". Idem `or 0` nas métricas de cobertura quando o artefato estático não resolve. | **Z1, Z3** |
| **V3** | Identidade com dois `COMPLETED` | O resume **acrescenta** registro. Se o reparo de admissibilidade não rebaixar o antigo para `ERROR`, ficam dois `COMPLETED` e o consolidador guarda o **primeiro**, que é o inadmissível. | **G2** |
| **V4** | Identidade que some da grade | Identidade sem nenhum `COMPLETED` não vira linha com valor ausente: **não gera linha**. A média da célula sai sobre menos repetições, sem sinal nenhum. | **G1** |
| **V5** | Container religado enviesa a amostra | Containers não morrem ao acaso: morrem nas tasks mais pesadas. Se as religadas forem sistematicamente as de maior `mop_total`, o viés é correlacionado com o orçamento. 34 religamentos até agora. | **M2** |
| **V6** | `unmatched_in_scope` com piso de classes geradas | O weaver instrumenta `R$*`, `BuildConfig`, `Manifest*`; o lado estático os exclui. Os eventos caem em `unmatched_in_scope` sem ser buraco de denominador. A gh111 ampliou essa exclusão. | **E1** |
| **V7** | Vazamento de frame na identidade de violação | Para todo nome de método com `$`, `-` ou espaço — isto é, toda lambda e todo sintético Kotlin — o normalizador copia o `StackTraceElement` inteiro nos dois campos, posição de fonte junto. A posição entra na chave e um mau uso conta uma vez por linha onde ocorre. | **I3** |
| **V8** | `errors.csv` sem filtro de escopo | Cobertura filtra por escopo, violação não. Com 47 specs, violações originadas em biblioteca instrumentada crescem, e `mop_unique` passa a misturar app e biblioteca. Publicar as duas lado a lado supõe o mesmo escopo. | **E2** |
| **V9** | Coluna zero por construção | Em 2025, `cov_act` e `cov_rv_method` saíram 0,0 % em toda a campanha por agregar a coluna errada, e ninguém notou até alguém comparar dois níveis do mesmo pipeline. | **Z4** |
| **V10** | Colapso de orçamentos a jusante | O consolidador pareia certo por `(apk, timeout)`. Mas em `per_task.csv` o orçamento é coluna comum, e qualquer `groupby(['apk','tool'])` intermediário funde 60/180/300 s sem erro. | **M3** |
| **V11** | Média de médias com *n* desigual | `per_apk_paired.csv` não tem coluna de número de repetições. Célula com 1 rep pesa igual a célula com 3. | **G1, R1** |
| **V12** | Falta de exposição no modelo | `mop_total` cresce com o tempo efetivo, que não é o orçamento: há boot, instalação e religamento. Sem offset de exposição, o coeficiente do orçamento absorve overhead de container. `execution_time_seconds` existe no índice e **não** é exportado. | **M1** |

---

## Parte III — Detectores

Três grupos, pela única coisa que importa agora: quando podem rodar.

### Grupo A — Rodam com a campanha no ar (leem índice e metadados, não tocam artefato)

| # | Lê | Invariante | Evidência de falha |
|---|---|---|---|
| **G1** | `tasks.json` | Grade completa: 163 × 11 × 3 × 3 = 16 137; exatamente 3 reps por `(apk, braço, orçamento)`; 11 braços; orçamentos = {60,180,300} | Célula com menos de 3 reps é média silenciosa sobre *n* menor; com mais de 3, duplicata de identidade |
| **G2** | `tasks.json` | Nenhuma identidade com dois ou mais registros em `COMPLETED` | Violação = o consolidador guardará o primeiro, que pode ser o inadmissível |
| **G3** | `summary.csv` | `classes_total` e `methods_total` constantes nas 99 identidades do mesmo APK | Variação = artefato estático trocado no meio da campanha |
| **Z4** | `per_task.csv` | Toda métrica tem mais de um valor distinto, no total e dentro de cada braço | Métrica constante = coluna zero por construção |
| **E3** | os 163 `.apk.json` | Nenhum `codePackage` sob prefixo excluído pelo weaver | Casamento = numerador estruturalmente vazio, como o stardroid |
| **M3** | meta JSON + `per_task.csv` | `rep ∈ {1,2,3}` é repetição e `timeout ∈ {60,180,300}` é orçamento, conferido contra o compose | 3 × 3 é simétrico: nenhuma contagem distingue os fatores trocados, e a binomial negativa trata orçamento como categórico |

### Grupo B — Depois de 13/09, sobre o corpus inteiro

| # | Lê | Invariante | Pega |
|---|---|---|---|
| **A1** | `tasks.json` + artefatos | C1–C6 por identidade, como **colunas** e não como passo | Emulador morto gravado `COMPLETED` com erro vazio |
| **Z1** | `per_task.csv` + artefatos | Todo zero tem tipo: `medido`, `sem_logcat`, `sem_static`, `inadmissivel` | Nenhum zero que não seja `medido` pode entrar numa média |
| **Z3** | `per_task.csv` | `mop_unique > 0 ⇒ mop_total > 0` e `mop_total ≥ mop_unique` | Diagnostica F1 e V2 de uma vez, sem reprocessar nada |
| **I1** | `.logcat` | Contra-regex frouxa `RVSEC\s*:\s*[^,\s]+,` contra a do consolidador; as contagens têm de coincidir | Lista os nomes de spec ignorados. Já sei que três devem aparecer; se aparecerem outros, o alfabeto mudou |
| **I2** | registros persistidos | Todo spec observado pertence aos 47 do `jca_android` | Instrumentação com o conjunto errado |
| **I5** | registros persistidos | Recalcular a chave de 4 partes do artigo e comparar com o `mop_unique` de 7 | Não é teste: é **o número que o artigo precisa declarar** |
| **R1** | `per_task` → `per_apk_paired` | A média por `(apk, orçamento, braço)` bate exatamente, tolerância de arredondamento | Conjunto agregado ≠ conjunto escrito |
| **R2** | `per_apk_paired` → `per_tool_summary` | `n_apks` = 163 em toda linha | Menos que isso: a tabela deixa de ser pareada enquanto o teste continua sendo |
| **R3** | `errors.csv` × `per_task.csv` | `|{unique_msg}|` por task = `mop_unique` daquela task | Divergência sistemática = a identidade do CSV e a de `unique_errors` não são a mesma |
| **E1** | `summary.csv` + `.apk.json` | `unmatched_in_scope` explicável por classes geradas e `…$Log` | Sinal por APK e estável entre as 99 identidades: buraco de denominador é propriedade do artefato, não da ferramenta |
| **E2** | `summary.csv` | Não existe `cov_method ≈ 0` com `unmatched_out_of_scope` grande e `measured=true` | Chave de escopo apontando para o lugar errado |
| **I3** | `errors.csv` | Nenhum campo de classe ou método casa `\([^()]+:\d+\)$` | `StackTraceElement` inteiro no campo, inflando `mop_unique` por linha de ocorrência |
| **I4** | `coverage.csv` + `.apk.json` | `canon(x) = x.replace('$','.')` não mapeia duas grafias distintas ao mesmo canônico | Assinatura das anomalias de classe interna de 2025 |
| **L4** | registros persistidos | Taxa de `truncated` desprezível e **não crescente com o orçamento** | Taxa que cresce de 60 s para 300 s: `mop_unique` inflado proporcionalmente à atividade da ferramenta |
| **L5** | índice/diagnósticos | Os contadores que o parser já mantém estão gravados e são zero ou justificados | Contador **ausente** é pior que não-zero: o oráculo existe e não está sendo persistido |

### Grupo C — Depois de 13/09, em amostra estratificada por (braço × orçamento × presença de violação)

Amostra sorteada não serve. Em 16 137 execuções a maioria tem zero violações, e sortear arquivos
reproduz literalmente o erro de 2025, quando 20 arquivos sem violação alguma autorizaram a
conclusão "validado".

| # | Lê | Invariante | Pega |
|---|---|---|---|
| **L1** | `.logcat` | O maior intervalo entre carimbos consecutivos é pequeno em relação ao orçamento | Lacuna grande é app parado **ou** buffer transbordado; separa-se cruzando com o artefato da ferramenta. Exige carimbo com sub-segundo: preservar o cru antes de qualquer normalização |
| **L2** | `.logcat` cru | Ausência de linhas de descarte do `logd`; o cabeçalho `--------- beginning of` não reaparece no meio | Reaparição no meio é marca de rotação de buffer. É a **única prova direta** de perda que existe passivamente |
| **L3** | `.logcat` | Taxa de eventos por segundo estável entre as 3 repetições da mesma célula | Repetição muito abaixo da mediana das irmãs = perda de linha. É o oráculo interno mais barato da campanha, e 2025 nunca o usou |
| **L6** | `.logcat` × índice | Reprocessar offline e comparar com o gravado ao vivo | Divergência = linhas perdidas na captura |
| **E4** | `coverage.csv` × `.apk.json` | Toda assinatura ocorre byte a byte no artefato estático | Deve dar zero por construção; se der diferente, o defeito é no caminho de resume |

### Grupo D — Especificação do modelo, não detecção

| # | O quê | Por quê |
|---|---|---|
| **M1** | Exportar `execution_time_seconds` para `per_task.csv` e usar `log(tempo efetivo)` como offset | Sem exposição, o coeficiente do orçamento absorve overhead de boot, instalação e religamento |
| **M2** | Marcar cada identidade com `foi_religada` e comparar a distribuição contra as irmãs da mesma célula | Religamento por falta de memória não é aleatório: atinge as tasks mais pesadas |
| **M4** | Decidir explicitamente o tratamento de zeros estruturais em `mop_unique` | APK que não exercita criptografia produz zero por natureza, não por baixa cobertura. Uma binomial negativa sem componente de inflação atribui esses zeros à ferramenta e ao orçamento |

---

## Parte IV — Ordem de execução

**Enquanto a campanha corre.** Só o Grupo A. Nada que abra os 16 137 traços e logcats: eles moram
no mesmo disco que os dez containers estão usando para escrever, e o tempo decorrido é o
discriminador do critério C2, que mede mais alto sob contenção. O `admissibility.py` já recusa a
varredura de artefatos com container de pé, e sai com código 2.

**Assim que fechar, antes de dar `down`.** Passada de resume final, depois Grupo B. Só então a
consolidação. Admissibilidade é coluna, não etapa: se `per_task.csv` não carregar C1–C6, a média
já foi tirada sobre o que quer que tenha entrado.

**Antes de escrever o artigo.** O detector **I5** não é teste, é entregável: produz a contagem de
maus usos únicos sob a chave de quatro partes do artigo, ao lado da de sete partes da campanha. Sem
essa tabela, a comparação com os números publicados mistura mudança de conteúdo com mudança de
definição, e a diferença aparece como efeito das especificações.

## Parte V — O que **não** fazer

- **Não truncar carimbo de tempo para segundo inteiro.** Foi o que 2025 fez para zerar as inversões,
  e isso não corrigiu o dado: eliminou o detector. Com dez emuladores em contenção a janela de
  inversão aumenta, e uma spec com ORDER precisa da ordem. Se for preciso ordem total, truncar **e**
  desempatar por contador de aparição, guardando o intervalo original em coluna à parte.
- **Não excluir APK sem decisão explícita.** A regra da campanha anterior derrubava a aplicação
  quando um braço ficava sem réplica admissível, e ali eram 3 braços. Aqui são 11 × 3 orçamentos, e
  os 19 APKs sem activity de entrada permaneceram na análise do artigo com cobertura zero nesse
  braço. O `admissibility.py` calcula as candidatas e para.
- **Não confiar num detector que acusa muito.** A lição mais cara de 2025: num APK, 27 % das
  "falhas" eram do medidor, não do dado. Qualquer detector acima que acuse em massa deve ser
  confrontado contra a fonte antes de virar correção — sobretudo porque corrigir, aqui, significa
  mexer em número de artigo.

## Fontes

- Regeração de 2025: `rvsec-regerar-resultados/docs/NOVO/{01,02,03,04,05,06,07}*.md` e os
  documentos de análise e validação em `rvsec-regerar-resultados/docs/`.
- Identidade de violação: `modules/rv-android-core/src/rv_android_core/domain/log.py`, `unique_msg`.
- Consolidação: `.claude/skills/rv-experiment-compare/scripts/consolidate_compare.py`.
- Admissibilidade e reparo: `experimento-estudo02/scripts/{admissibility.py,repair.py}`.
- Plano e desenho: `docs/20260908_estudo02.md`, `experimento-estudo02/README.md`.
