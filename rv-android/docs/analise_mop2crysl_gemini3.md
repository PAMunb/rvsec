# Relatório de Revisão Externa e Avaliação Crítica — Componente de Conformidade MOP↔CrySL

**Data:** 21 de agosto de 2026  
**Avaliador:** Antigravity (Gemini 3.7 Flash)  
**Objeto da Revisão:** `docs/20260821_conformidade_mop_crysl.md` (Plano de Engenharia de Módulo Maven, 1284 linhas)  
**Artefatos Auditados:**  
- `docs/20260821_validacoes_conformidade_mop_crysl.md` (Registro de Validações V1–V10)  
- `docs/handoff/20260821_arnes_validacoes/` (Arnês Executável V1–V10)  
- `docs/20260821_auditoria_conformidade_mop_crysl.md` (Relatório de Auditoria de Consistência)  
- `docs/handoff/20260821_arnes_auditoria/` (Arnês de Sondas A/B/C)  
- Corpora no disco: `rvsec-mop` (`jca_android`, `jca`, `generic`, `generic_new`), `MetaCrySL/generated/api30/`, `MetaCrySL/samples/jca/base/`, `rvsec-cognicrypt/CrySL-Rules/`, `br/unb/cic/mop/Property.java`, `data/jca_android/*.csv`  
**Destino do Relatório:** `docs/analise_mop2crysl_gemini3.md`  
**Declaração de Ferramental:** O servidor MCP `sequential-thinking` **não estava disponível** no ambiente de execução desta sessão; todas as etapas de síntese lógica, derivação e análise de alternativas foram executadas autonomamente com rastreamento explícito.

---

## 1. Veredito

O plano de engenharia é **conceitualmente ambicioso, tecnicamente demonstrável nas partes executadas (V1–V10) e metodologicamente indispensável** para substituir a proliferação frágil de scripts Python ad-hoc (`gh100`–`gh105`). No entanto, o plano **deve proceder com emendas substanciais**: ele padece de (1) contradições aritméticas e ausência de evidência em §10, (2) assimetrias de edição e referências órfãs entre seções (§6, §8 vs §12, §5.2), (3) conflação conceitual recorrente entre a *adaptação de plataforma* (eixo horizontal) e o *ruído de tradução* (eixo vertical) em allow-lists e classes inexistentes, e (4) cegueira do modelo estático de autômatos diante de fenômenos semânticos reais de runtime do AspectJ/JavaMOP (`guard-on-field`, co-disparo de pointcuts, retenção de estado booleano). A recomendação é **reorientar o projeto para uma arquitetura híbrida de três pilares**: promover o compilador `crysl2mop` a produto central por construção, reter o comparador M1–M4 como *Translation Validation Gate* com recusa tipada explícita (`Unknown`), e incorporar *fuzzing diferencial de traços* para blindar a semântica dinâmica contra objeções em periódicos de topo (TSE/TOSEM).

---

## 2. Método e Protocolo de Verificação

A revisão seguiu estritamente o protocolo multi-dimensional estabelecido no prompt de handoff, com segregação de tarefas e recontagem a partir de fontes primárias no disco:

1. **Leque de Subagentes:** Foram invocados 5 subagentes especializados executando em contextos paralelos:
   - **Subagente D1:** Verificação factual e recontagem quantitativa exaustiva das fontes primárias no disco.
   - **Subagente D2:** Coerência interna, conferência cruzada entre seções e revisão crítica dos 14 achados da auditoria prévia.
   - **Subagente D3/D5:** Solidez arquitetural, isolamento de dependências (Guava 33.5 vs 19.0), costura JSON e viabilidade de engenharia.
   - **Subagente D4/D8:** Validade metodológica (eixos de divergência, tetos, relações de ordem) e construção de cenários adversariais formais.
   - **Subagente D6/D7:** Enquadramento científico, estratégias de publicação (RQs/venues) e desenvolvimento formal de 5 alternativas arquiteturais radicais.
2. **Execução vs. Leitura:**
   - *Executado diretamente no disco:* Varredura e parsing de 214 specs `.mop`; censo e classificação paramétrica das 118 specs do `generic`; censo de constantes e Javadoc de `Property.java`; censo de 62/55 constraints e 92 predicados no `api30` e `CrySL-Rules`; teste de compilação dos módulos pom e sondas de aspecto em `docs/handoff/`.
   - *Análise analítica de código:* Inspeção dos fontes JavaMOP (`DumpVisitor.java`, `SpecExtractor.java`, `javamop.jj`), AST EMF do Xtext, Rascal do MetaCrySL e classes utilitárias de `rvsec-core`.

---

## 3. Achados por Dimensão (D1–D8)

### D1 — Factual e Numérico

| Item | Afirmação no Plano | Valor Recontado no Disco | Veredito | Severidade | Evidência Primária |
|---|---|---|---|---|---|
| **Specs multi-parâmetro em `generic`** | 93 specs (39/28/18/7/1) (§12:1167, §13:1207) | **97 specs** (40 com 2, 30 com 3, 17 com 4, 6 com 5, 4 com 6; 21 com 1) | **REFUTED** | **HIGH** | `rvsec-mop/.../generic/*.mop` (118 arquivos analisados) |
| **Specs absorventes em `jca_android`** | 12 de 23 specs (§2:95, §13:1206) | **16 de 23 specs** absorvem uso incorreto em corpos; **7 não absorvem** | **REFUTED** | **MEDIUM** | Censo dos corpos de eventos vs `@fail` em `jca_android/` |
| **Constantes em `Property.java`** | 24 constantes; Javadoc cita cláusula correspondente (§3:114) | **26 constantes**; apenas **3 constantes** com Javadoc de cláusula + 1 da classe | **REFUTED** | **LOW** | [`Property.java:1-70`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/Property.java#L1-L70) |
| **Aritmética da Tabela de §10** | 87/92 ("4 lacunas"); 16/55 + 47/55; 67,6% + 9% (§10:744-748) | $92-87=\mathbf{5 \neq 4}$; $16+47=\mathbf{63 > 55}$; $67,6+9=\mathbf{76,6\% \neq 100\%}$ | **REFUTED** | **HIGH** | Inconsistências aritméticas internas em §10 |
| **Regras carregáveis sob Leitor Isolado** | "31 regras que carregam" usado universalmente (§5.2, §8, §10.2) | **30 de 33 regras** sob a decisão de §12 (leitor isolado); `Signature` falha | **REFUTED** | **HIGH** | [`NOTAS-BRUTAS.md:37-44`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/handoff/20260821_arnes_validacoes/NOTAS-BRUTAS.md#L37-L44) e `v3/V3.java` |
| **Teto do Oráculo: Cláusulas perdidas** | ~9 cláusulas perdidas em 3 regras base (§5.3:321-337) | **95 no original vs 62 no `api30`**; perda ocorre em **16 regras** | **CONFIRMED (Audit)** | **HIGH** | `samples/jca/base/` vs `CrySL-Rules/` vs `generated/api30/` |
| **Censo de Constraints (M3)** | 62 total, 55 pareadas, Matriz A=11, B=3, C=4, D=7, Ausente=30 (§5.3) | **62 total, 55 pareadas**, Matriz **11/3/4/7/30** exata | **CONFIRMED** | **NEUTRAL** | `constraint_table.csv` e `api30/*.cryptsl` |
| **Censo de Predicados (M4)** | 92 cláusulas (54/36/2), 32 predicados, aridade 59/33, denoms 73/54/44 (§5.4) | **92 cláusulas (54/36/2), 32 predicados, aridade 59/33**, denoms **73/54/44** | **CONFIRMED** | **NEUTRAL** | `crysl.json` e `predicate_graph.csv` |

---

### D2 — Coerência Interna

1. **Substituições Léxicas Desalinhadas:** §8:594 lista **cinco** substituições (incluindo `length(...)` $\to$ `length[...]`), enquanto a tabela-síntese de §12:1101 (que formaliza a proposta) prescreve **quatro**. **[Severidade: HIGH]**
2. **Colapso da Parcela de Fiação em §6:** §5.4:406-413 decompõe com exatidão $26 + 28 + 19 + 19 = 92$. O §6:469-474 apresenta como formulação revisor-proof: *"26 estão implementadas... As 19 restantes exigem PredicateStore; as outras 19 exigem specs que não existem"* ($26+19+19=64 \neq 92$), apagando os 28 de débito de fiação. **[Severidade: HIGH]**
3. **Frase Invertida sobre Vazamento de Escopo:** Em §9:705-706, o texto afirma que *"ler cada regra num leitor novo, ou declarar a ordem de leitura... e nesse caso Signature não carrega"*. O teste V4 provou que no leitor novo ela falha e com ordem declarada ela carrega. **[Severidade: MEDIUM]**
4. **Testemunhas Desalinhadas com Validações:** §5.2:288-305 afirma que as testemunhas de `CipherSpec` saíram idênticas a V4 (`g1 i1 f1` e `g1 i1 i1 f2`). Em V4 (`validacoes:247`), as testemunhas obtidas foram `g1 i2 doFinal()` e `g1 i2 i2 doFinal(byte[])`. O texto em prosa cita `init(Key)`, mas imprime `i1` (`init(Certificate)`). **[Severidade: MEDIUM]**
5. **Afirmações Conflitantes sobre Scala 3:** §11.5:1046 alega que o *nearest-wins* para Scala 2.13.14 foi *"verificado na árvore"*, enquanto o registro V10 em `validacoes:418` admite que não foi exercitado. **[Severidade: LOW]**

---

### D3 — Solidez Arquitetural

1. **Decomposição por Tecnologia (`core`, `mop`, `crysl`):** **CONFIRMADA como arquiteturalmente sólida.** Separar por tecnologia evita que o gerador `crysl2mop` precise acoplar `CrySLParser` e `javamop` no mesmo POM/classpath. O `core` permanece livre de dependências pesadas, garantindo testes de autômatos ultrarrápidos e determinísticos.
2. **Costura JSON em Processos Separados:** **CONFIRMADA como a melhor escolha.** O `CrySLParser 4.0.6` puxa Guava 33.5.0-jre e Guice 7; o reator `rvsec` pina Guava 19.0. Alternativas como Maven Shading falham frequentemente com Xtext/EMF (quebra de SPI e factories dinâmicas), e `URLClassLoader` customizado em Java 21 sofre com *parent-first* e encapsulamento de módulos. O intercâmbio de `SpecModel` via JSON desacopla os processos e cria artefatos intermediários auditáveis para pesquisa.
3. **Perda de Comentários no `DumpVisitor`:** A impossibilidade de reancorar comentários no JavaCC (`JavaMOPSpec` com line=0; nós internos com line=1) foi comprovada (§11.2). A decisão de descartar comentários artesanais e injetar cabeçalhos sintéticos de procedência (`regra:linha`) é pragmática e alinhada a P1.
4. **Sanity Checker Obrigatório:** O pipeline JavaMOP é cego a defeitos graves de declaração (IDs duplicados como `c1, c1` ou símbolos fantasmas no `ere` passam por `javamop`, `rv-monitor` e `javac` com 0 erros, como provado em V7). O checador sintático de 20 linhas na AST é componente mandatório.

---

### D4 — Validade Metodológica

1. **Conflação entre Adaptação de Plataforma (Horizontal) e Infidelidade (Vertical):** O plano falha em respeitar a sua própria distinção em quatro pontos:
   - *Allow-lists com `ConscryptAliasTable`:* §5.3 classifica o uso de aliases como "mais permissivo" (infidelidade), quando na verdade é a adaptação correta aos nomes de algoritmos e OIDs aceitos pelo provedor Conscrypt no Android API 30.
   - *Classes inexistentes no Android:* `HMACParameterSpecSpec` é rotulada em §9 como spec com fatiamento quebrado, quando na verdade a classe nem existe no Android — o defeito está no oráculo `api30` que gerou a regra, não na tradução manual.
   - *Regressão de constraints no template MetaCrySL:* A perda de constraints em `DHGenParameterSpec` faz a spec manual fiel parecer `MOP-SEM-BASE` frente a `api30`.
   - *Comparação histórica:* Avaliar `jca` (`S_java`) contra `api30` (`R_android`) cruza a diagonal metodológica proibida pelo diagrama de 4 artefatos.
2. **Insuficiência de Equivalência de Linguagens para Safety Monitors:** Monitores de runtime avaliam prefixos e possuem estados de rejeição explícitos. Dois autômatos podem aceitar a mesma linguagem completa de palavras ($\mathcal{L}(A_1) = \mathcal{L}(A_2)$), mas se um deles omitir o bloco `@fail`, ele silenciará violações em runtime. A métrica M2 deve ser formalizada como **Equivalência de Autômatos de Segurança Prefixo-Fechados com Preservação de Predicados**.
3. **Cegueira para `IncompleteOperationError`:** O plano reconhece, mas deve enfatizar com maior destaque no protocolo que o JavaMOP cobre estritamente propriedades de *Safety/Typestate*, sendo estruturalmente cego para violações de fim de ciclo de vida (*Liveness*) sem instrumentação de GC.

---

### D5 — Viabilidade e Risco de Engenharia

1. **Viabilidade Comprovada por Execução (V1–V10):** A geração ponta a ponta de specs (`DHGenParameterSpec`, `GCMParameterSpec`, `PBEParameterSpec`), a determinização de Glushkov, a extração de AST EMF de 33/33 regras e a compilação de monitores com `ajc` estão provadas em código.
2. **Rank de Riscos Técnicos:**
   - *Risco 1 (Alto):* Teto do oráculo distorcendo métricas M3/M4 (mitigado pela exigência de `Unknown` e declaração de denominadores).
   - *Risco 2 (Médio-Alto):* Coexistência de substratos `ExecutionContext` (aridade 1) e `PredicateStore` (aridade $N$) durante a migração gh105 (resolvido passando o substrato como parâmetro do gerador).
   - *Risco 3 (Médio):* Precedência invertida de `ORDER` (`|` vs `,`) em parsers legados (mitigado pelo parser corrigido de V2/V4).

---

### D6 — Contribuição Científica

1. **Diferenciação Crítica contra Torres et al. (TSE 2023):** O trabalho de 2023 assumiu tradução manual informal. Este trabalho desmistifica essa premissa ao provar analiticamente que a tradução humana introduziu autômatos incomparáveis (`CipherSpec`), absorção de erros em 16/23 specs e ausência de 30/55 constraints.
2. **Tese de §10.6 Defensável em Top Venues (IEEE TSE / ACM TOSEM):** Posicionar a ferramenta não como um mero "tradutor", mas como um **estudo formal e empírico dos limites fundamentais de monitorabilidade em tempo de execução** com recusa tipada (`Unknown`), sustentado por geração com corretude por construção.

---

### D7 — Alternativas Arquiteturais Radicais

Foram exploradas 5 alternativas formais de redesign (ver Seção 6 para detalhamento completo):
- **Alt 1:** Geração Formal por Construção (`crysl2mop`) com Translation Validation Gate.
- **Alt 2:** Linguagem Intermediária Unificada baseada em *Extended Guarded Automata (EGA)*.
- **Alt 3:** *Differential / Property-Based Testing com Fuzzing de Traços* contra o runtime JavaMOP.
- **Alt 4:** Refinamento Formal e Model Checking com Z3 / SMT-LIB.
- **Alt 5:** Mineração Dinâmica de Invariantes em APKs reais via Daikon / $L^*$.

---

### D8 — Análise Adversarial (Quebrando o Verificador)

Identificamos **5 cenários concretos** onde o verificador proposto emite vereditos errados:

1. **Falso Positivo de Conformidade por `guard-on-field` (`MessageDigestSpec`):**
   - Se o weaver do AspectJ compilar o advice de `g4` antes de `g1`, em `getInstance("SHA-256")` o campo `currentAlgorithmInstance` é `null`, fazendo `!matches(null) == true`. O evento `g4` dispara para algoritmo seguro e transita para `@fail`. O verificador estático M2 aplica $\epsilon$-apagamento em `g4` e emite **`EQUIVALENTES`**, cego para o falso alarme de runtime.
2. **Diagnóstico Errado por Co-disparo (`CipherSpec`):**
   - O pointcut `call(* doFinal(..))` casa `doFinal()`, disparando **ambos** `f1` e `f2` na mesma invocação. O monitor recebe a palavra $\langle f1, f2 \rangle$. O verificador M2 compara autômatos assumindo símbolos disjuntos e deriva testemunhas unárias falsas (`g1 i1 f1`), quando em runtime ocorre uma transição dupla.
3. **Falso Positivo por Contaminação de Fatiamento (`KeyStoreSpec`):**
   - A spec declara `KeyStore ks`, mas os 7 eventos usam variável livre `k`. O JavaMOP instancia um Monitor Singleton Global. Em ambiente multithreaded, `ks1.load()` silencia a violação de `ks2.getKey()` antes de `load()`. O verificador M2 compara a topologia do autômato e atesta **`EQUIVALENTES`**, validando uma spec com vazamento grave entre instâncias.
4. **Falso Negativo de Fidelidade em Allow-lists com Aliases:**
   - O verificador acusa `MOP-MAIS-PERMISSIVA` em allow-lists que usam `ConscryptAliasTable.matches()`, quando a aceitação de variantes como `"2.16.840..."` para AES é conformidade estrita com o provedor Android.
5. **Falso Positivo em Reinicializações com Retenção de Estado (`conforms`):**
   - Se uma chamada inválida seta `conforms = false` no aspecto e uma chamada válida subsequente reconfigura o objeto sem resetar o campo, o predicado `ENSURES` é suprimido indevidamente. O verificador M4 estático reporta **`FIEL`** nas arestas, incapaz de notar a retenção de estado mutável.

---

## 4. Revisão Crítica da Auditoria de Consistência

Confrontamos os achados do relatório de auditoria ([`docs/20260821_auditoria_conformidade_mop_crysl.md`](file:///home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/20260821_auditoria_conformidade_mop_crysl.md)) contra as fontes primárias:

### 4.1 Onde a Auditoria está 100% Correta
- **A3 (4 vs 5 substituições):** Confirmado que §12 omitiu `length(...)`.
- **A4 (Refutação da testemunha do Cipher):** O arnês executável provou o co-disparo de `f1`/`f2` e a falha em `s2`. A testemunha `g1 i1 wkb1 f2` é a substituta correta.
- **A6 (Aritmética de §6):** Confirmado o desaparecimento da parcela de 28 ($26+19+19=64 \neq 92$).
- **A7 (M4 não derivável dos CSVs):** Confirmado que `predicate_graph.csv` possui apenas 18 anotações de cláusulas e não publica a classificação FIEL/PROJETADO/CONFLADO/AUSENTE.
- **A8 (Contagens refutadas):** Confirmadas: `generic` multi-parâmetro é 97 (não 93); specs absorventes são 16 (não 12); `Property.java` tem 26 constantes (não 24).
- **A10, A11, A12, A13, A14:** Todos confirmados integralmente no código e no histórico.

### 4.2 Onde a Auditoria Exagerou ou Exige Nuance
- **Achado A1 (§10 inteiro sem evidência):** A auditoria foi precisa ao apontar que a tabela projetada não fecha aritmeticamente ($92-87=5 \neq 4$; $16+47=63>55$). Contudo, classificar §10 como "sem evidência alguma" é excessivo: as validações V2 e V7 geraram e compilaram 3 specs reais completas com medição M1–M4. A crítica deve recair sobre a extrapolação para as 33 regras.
- **Achado A2 (Redução para 30/33 sob leitor isolado):** A auditoria apontou corretamente que a fachada `CrySLParser` falha em `Signature.cryptsl` se isolada. Contudo, ela omitiu notar que a leitura direta via AST EMF do Xtext (validada em V5) contorna a validação da fachada e obtém **33/33 Domainmodels**, resolvendo o problema sem vazamento de escopo.

### 4.3 O que a Auditoria Deixou de Notar
1. **Aritmética de Cobertura de Specs (23 vs 22 vs 11):** O documento cita 23 specs e 22 regras cobertas sem explicar que `RandomStringPassword.mop` não tem contraparte CrySL, gerando $33 - 22 = 11$ faltantes.
2. **Conflito de Decisão Arquitetural em §13 vs §12:** §13:1263 deixa aberta a alternativa de "ordem de leitura declarada", enquanto §12:1106 fecha estritamente em "leitor isolado".
3. **Ausência de `HMACParameterSpecSpec` em `constraint_table.csv`:** A spec morta por construção sequer consta na tabela de constraints.

---

## 5. Avaliação dos 10 Vereditos Estruturais (§5 do Prompt)

| # | Afirmação Estrutural Avaliada | Veredito | Justificativa Sintética |
|---|---|---|---|
| **1** | *"A comparação é o produto; a tradução é o meio"* | **PARCIALMENTE REDIRECIONADA** | A comparação audita o legado, mas o compilador `crysl2mop` é o produto de maior impacto prático. Eles formam um componente único: o comparador atua como *Validation Gate* do compilador. |
| **2** | *Equivalência de linguagens sobre autômatos para `ORDER`* | **INSUFICIENTE** | Requer **Bissimulação Prefixo-Fechada com Preservação de Predicados**. Equivalência pura ignora transições de erro e momentos de emissão de predicados. |
| **3** | *Precedência do `ORDER` (`\|` mais forte que `,`)* | **CONFIRMADA** | A gramática Xtext oficial (`CrySL.xtext:103-134`) confirma `\|` sobre `,`. O gate `gh105_order_gate.py` e o MetaCrySL estavam invertidos. Raio de impacto: 1 regra (`Cipher`). |
| **4** | *M2-eff (monitor gerado) sobre M2-decl (texto `.mop`)* | **CORRETA, COM RESSALVA** | M2-eff reflete o código real do experimento, mas o extrator não pode depender de `RVM_eventNames` instável nem ser enganado por minimizações de estados de predicado. |
| **5** | *Normalização N1 (no máximo 1 criador por monitor)* | **CONFIRMADA EM RUNTIME** | V8 provou em traço que o JavaMOP instancia um monitor por objeto retornado em `getInstance()`. É lei geral do fatiamento paramétrico da ferramenta. |
| **6** | *`IncompleteOperationError` cego em M2* | **FRONTEIRA DE ESCOPO VÁLIDA** | Não invalida o comparador, desde que explicitamente delimitado como propriedade de *Safety/Typestate* (limite fundamental de RV). |
| **7** | *Fronteira do parâmetro único e recusa tipada* | **PRINCIPADA E CORRETA** | Custo 0/23 em JCA. No `generic` (97/118 multi-paramétricas), a recusa tipada impede que o comparador emita relatórios com falsos positivos. |
| **8** | *Costura JSON e processos separados para isolar Guava* | **ARQUITETURALMENTE ELEGANTE** | Elimina em nível de sistema operacional a colisão hostil Guava 33.5 (Xtext) vs 19.0 (Soot), preservando a pureza dos classpaths. |
| **9** | *`ExecutionContext` (aridade 1) vs `PredicateStore` (aridade $N$)* | **PARÂMETRO OBRIGATÓRIO** | O gerador não pode deduzir o substrato da regra CrySL; deve recebê-lo como parâmetro durante a migração do gh105. |
| **10** | *Enquadramento científico ("o mapa do que não se traduz")* | **ALTAMENTE PUBLICÁVEL** | Supera Torres et al. (TSE 2023) ao desconstruir a tradução manual e formalizar a taxonomia de monitorabilidade em tempo de execução. |

---

## 6. Alternativas Arquiteturais Radicais (D7)

A análise converge para uma proposta de **Arquitetura Híbrida de Três Pilares (O Triângulo de Conformidade)**, superando o modelo puramente estático:

```
                     ARQUITETURA HÍBRIDA ESTRATÉGICA
                       O "TRIÂNGULO DE CONFORMIDADE"

                                [ PILAR 1 ]
                             COMPILADOR FORMAL
                                (crysl2mop)
                             Geração Correta por
                                 Construção
                                     ▲
                                    ╱ ╲
                                   ╱   ╲
                       Validação  ╱     ╲  Oráculo
                      de Geração ╱       ╲ Dinâmico
                                ╱         ╲
                               ▼           ▼
               [ PILAR 2 ] ◄───────────────────► [ PILAR 3 ]
             VERIFICADOR ESTRUTURAL            FUZZING DIFERENCIAL
             (Canonical Model Comparator)      (Property-Based Trace Fuzzing)
               DFA / M1-M4 Gate                  Validação de Runtime
               + Recusa Tipada                   (Guard-on-field, Slicing)
```

### Detalhamento das Alternativas Exploradas

1. **Pilar 1 — Geração por Construção (`crysl2mop`):**
   - *Conceito:* Compilar diretamente `api30/*.cryptsl` $\to$ `.mop` usando a AST EMF do `CrySLParser 4.0.6`, determinizando a NFA de Glushkov em DFA minimizada e emitindo AST JavaMOP via `DumpVisitor`.
   - *Ganho:* Elimina 100% dos erros humanos de transcrição (IDs duplicados, fatiamento nulo, handlers sem `__RESET`).
   - *Custo/Risco:* Baixo; viabilidade demonstrada em V2/V7.
2. **Pilar 2 — Verificador Estrutural e Portão de Recusa Tipada (M1–M4):**
   - *Conceito:* Comparador de modelo canônico atuando como *Translation Validation Gate* do compilador e árbitro de auditoria do corpus legado.
   - *Ganho:* Emite tokens formais `Unknown` para cláusulas estáticas não-monitoráveis (`neverTypeOf`, `notHardCoded`, `IncompleteOperationError`), materializando a fronteira teórica do artigo.
3. **Pilar 3 — Validação Dinâmica via Fuzzing Diferencial de Traços (Alt 3):**
   - *Conceito:* Sintetizar traços de execução válidos e inválidos a partir da gramática CrySL (via QuickCheck/JQF) e despachá-los contra os monitores JavaMOP instrumentados com AspectJ.
   - *Ganho:* **Captura a semântica real de execução**, detectando conflitos de `guard-on-field`, precedência de advices e retenção de estado booleano que nenhum modelo estático enxerga. Blinda o paper contra revisores hostis de RV.

---

## 7. Riscos Ranqueados

| Rank | Risco de Engenharia / Pesquisa | Probabilidade | Impacto | Mitigação mais Barata e Rápida |
|---|---|---|---|---|
| **1** | **Teto do Oráculo distorcendo métricas publicadas** | Confirmada | Crítico | Declarar explicitamente os 3 tetos em §6 e carimbar denominadores. |
| **2** | **Conflitos de runtime AspectJ (`guard-on-field` e co-disparo)** | Confirmada | Alto | Adotar a política de constraints no corpo do evento e validar via Fuzzing Diferencial (Pilar 3). |
| **3** | **Coexistência de substratos de predicado durante o gh105** | Confirmada | Médio | Injetar o substrato (`ExecutionContext` vs `PredicateStore`) como parâmetro CLI do gerador. |
| **4** | **Corrupção de escopo no `CrySLModelReader`** | Confirmada | Médio | Utilizar a extração direta via AST EMF (`XtextResourceSet` isolado por arquivo) comprovada em V5. |
| **5** | **Alvo móvel por avanço contínuo do gh105** | Confirmada | Baixo | Carimbar imediatamente o commit SHA de referência em todas as tabelas de dados. |

---

## 8. Recomendações em Ordem de Retorno

### 8.1 Consertos Mecânicos (Incontestáveis / Sem Julgamento)
1. **Corrigir §12:** Mudar "4 substituições" para **"5 substituições léxicas"** (repondo `length[...]`).
2. **Corrigir §6:** Repor a parcela de **28 (débito de fiação)** na equação ($26 + 28 + 19 + 19 = 92$).
3. **Corrigir §5.2:** Substituir a testemunha refutada `g1 i1 f1` por `g1 i1 wkb1 f2` e corrigir a notação de `i1 i1` para `i2 i2`.
4. **Corrigir §9:** Desinverter a frase sobre o vazamento de escopo de `Signature.cryptsl`.
5. **Atualizar contagens refutadas:** `generic` multi-parâmetro = 97; specs absorventes = 16; constantes em `Property.java` = 26.
6. **Remover aspas da citação de Torres TSE 2023** em §10.6.
7. **Carimbar Commit SHA** nas tabelas de dados de §3, §5.4 e §7.

### 8.2 Decisões de Julgamento (Decisão do Pesquisador)
1. **Reorientação do Produto:** Aprovar o reposicionamento do módulo `rvsec-crysl` em torno do compilador `crysl2mop` com o comparador M1–M4 como portão de validação e recusa tipada.
2. **Formalização da Semântica de Plataforma:** Atualizar o protocolo para declarar que o uso de `ConscryptAliasTable` é conformidade com a semântica da plataforma Android, e não alargamento indevido.
3. **Adoção do Fuzzing Diferencial:** Incluir o módulo leve de testes baseados em propriedades para validação dinâmica dos monitores tecidos contra o AspectJ.
4. **Restauração do Oráculo MetaCrySL:** Corrigir os templates base em `samples/jca/base/` para recuperar as ~9 constraints normativas perdidas antes de congelar a baseline final.

---

## 9. Relação de Itens Não Verificados (Unverified)

1. **Comportamento dos monitores em APKs Android reais sob Dalvik/ART:** Não verificado porque o ambiente de execução é JSE e o `CLAUDE.md` do projeto proíbe o acionamento de emuladores Android. A validação limitou-se ao runtime Java SE com `ajc` e `rv-monitor-rt`.
2. **Posição exata no autômato para as 19 cláusulas com `after` além das 3 specs medidas em V2:** Não verificada exaustivamente para as outras 16 specs; classificada por polaridade e aridade.
3. **Análise de autômato das falhas de gate em `SSLContextSpec` e `TrustManagerFactorySpec`:** Não executada por ausência de mapeamento formal em `order_alphabet_map.csv`.

---
*Relatório concluído e fundamentado estritamente nas evidências primárias do repositório RVSec.*
