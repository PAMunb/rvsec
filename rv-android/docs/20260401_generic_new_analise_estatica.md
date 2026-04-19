# Análise: JavaMOP Specs (generic_new) vs Ferramentas de Análise Estática

**Data:** 2026-04-01  
**Objetivo:** Identificar ferramentas de análise estática que consigam capturar os mesmos tipos de erro das 27 specs JavaMOP em `rvsec-mop/src/main/resources/generic_new/`, aplicáveis a Java/Android.

---

## 1. Resumo das 27 Specs JavaMOP

| # | Categoria | Specs | Descrição |
|---|---|---|---|
| 1 | Stream/Resource (Use-After-Close) | 5 | Operações em OutputStream, Reader, InputStream, Writer após close(); close() sem efeito em ByteArrayInputStream etc. |
| 2 | Concorrência & Sincronização | 5 | Acesso não-sincronizado a coleções sincronizadas, iteração insegura, wait/notify sem monitor, modificação durante addAll() |
| 3 | Contratos de Interface | 4 | hashCode/equals, CharSequence em Sets, URLConnection.getPermission() |
| 4 | Comparable & Ordenação | 5 | compareTo(null), objetos não-Comparable em TreeMap/TreeSet/SortedSet |
| 5 | Encoding (UTF-8) | 2 | URLEncoder/URLDecoder sem UTF-8 |
| 6 | Iterator Safety | 1 | ListIterator.set() sem next()/previous() prévio |
| 7 | Network/Socket | 2 | ServerSocket timeout antes de accept(), backlog inválido |
| 8 | Validação de Input | 1 | Argumentos inválidos em Long.parseLong() |
| 9 | Serialização | 1 | Classe Serializable sem construtor no-arg na superclasse |
| 10 | Performance | 1 | Collections.newSetFromMap() desnecessário com HashMap/TreeMap |

### Detalhamento das Specs por Categoria

**Cat. 1 — Stream/Resource (Use-After-Close)**
- `OutputStream_ManipulateAfterClose.mop` — write()/flush() em OutputStream fechado
- `Reader_ManipulateAfterClose.mop` — read()/ready()/mark()/reset()/skip() em Reader fechado
- `InputStream_ManipulateAfterClose.mop` — read()/available()/reset()/skip() em InputStream fechado (exceto ByteArrayInputStream)
- `Writer_ManipulateAfterClose.mop` — write()/flush() em Writer fechado (exceto CharArrayWriter/StringWriter)
- `Closeable_MeaninglessClose.mop` — close() sem efeito em ByteArrayInputStream, ByteArrayOutputStream, CharArrayWriter, StringWriter

**Cat. 2 — Concorrência & Sincronização**
- `Collections_SynchronizedCollection.mop` — acesso sem lock em coleções sincronizadas
- `Collections_SynchronizedMap.mop` — iteração sem lock em mapas sincronizados
- `Map_UnsafeIterator.mop` — modificação do mapa durante iteração
- `Object_MonitorOwner.mop` — notify()/notifyAll()/wait() sem ser dono do monitor
- `Collection_UnsynchronizedAddAll.mop` — modificação da coleção fonte durante addAll()

**Cat. 3 — Contratos de Interface**
- `Collection_HashCode.mop` — equals() sobrescrito sem hashCode()
- `CharSequence_NotInSet.mop` — CharSequence adicionado a Sets (hashCode indefinido)
- `CharSequence_UndefinedHashCode.mop` — uso de equals()/hashCode() em CharSequence
- `URLConnection_OverrideGetPermission.mop` — subclasse de URLConnection sem sobrescrever getPermission()

**Cat. 4 — Comparable & Ordenação**
- `Comparable_CompareToNull.mop` — comparação com null
- `Comparable_CompareToNullException.mop` — compareTo(null) não lança NullPointerException
- `TreeMap_Comparable.mop` — chaves não-Comparable em TreeMap sem comparator
- `TreeSet_Comparable.mop` — elementos não-Comparable em TreeSet
- `SortedSet_Comparable.mop` — elementos não mutuamente comparáveis em SortedSet

**Cat. 5 — Encoding (UTF-8)**
- `URLEncoder_EncodeUTF8.mop` — URLEncoder.encode() sem UTF-8
- `URLDecoder_DecodeUTF8.mop` — URLDecoder.decode() sem UTF-8

**Cat. 6 — Iterator Safety**
- `ListIterator_Set.mop` — set() chamado sem next()/previous() prévio, ou após remove()/add()

**Cat. 7 — Network/Socket**
- `ServerSocket_SetTimeoutBeforeBlocking.mop` — setSoTimeout() não chamado antes de accept()
- `ServerSocket_Backlog.mop` — backlog ≤ 0

**Cat. 8 — Validação de Input**
- `Long_BadParsingArgs.mop` — string null/vazia ou radix fora do range em parseLong()

**Cat. 9 — Serialização**
- `Serializable_NoArgConstructor.mop` — superclasse não-serializável sem construtor no-arg acessível

**Cat. 10 — Performance**
- `Collections_UnnecessaryNewSetFromMap.mop` — newSetFromMap() com HashMap/TreeMap (já existem HashSet/TreeSet)

---

## 2. Ferramentas de Análise Estática Avaliadas

| Ferramenta | Tipo | Licença | Integração | Suporte Android |
|---|---|---|---|---|
| **SpotBugs** (+fb-contrib) | Bytecode analyzer | Open source | Gradle/Maven plugin | Sim (bytecode) |
| **Error Prone** | Compiler plugin | Open source | javac plugin | Sim |
| **Facebook Infer** | Inter-procedural analyzer | Open source | CLI, CI pipeline | Sim |
| **SonarQube** | Quality platform | Community + Commercial | Servidor, CI/CD | Parcial (via plugins) |
| **PMD** | Source code analyzer | Open source | Gradle/Maven plugin | Sim |
| **Checker Framework** | Type system extension | Open source | Annotation processor | Sim |
| **Android Lint** | Android-specific | Open source (AOSP) | Android Studio, Gradle | Nativo |

---

## 3. Matriz de Cobertura: Specs JavaMOP vs Ferramentas

| Categoria | SpotBugs | Error Prone | Infer | SonarQube | PMD | Checker Fwk | Android Lint |
|---|---|---|---|---|---|---|---|
| 1. Use-After-Close | ◐ | ◐ | ● | ◐ | ○ | ● | ◐ |
| 2. Concorrência | ● | ● | ● | ● | ◐ | ● | ○ |
| 3. hashCode/equals | ● | ● | ○ | ● | ○ | ○ | ○ |
| 4. Comparable | ◐ | ○ | ○ | ◐ | ○ | ○ | ○ |
| 5. Encoding UTF-8 | ◐ | ● | ○ | ● | ○ | ○ | ○ |
| 6. ListIterator | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| 7. ServerSocket | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| 8. Serialização | ● | ○ | ○ | ● | ○ | ○ | ○ |
| 9. newSetFromMap | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| 10. parseLong | ○ | ◐ | ○ | ○ | ○ | ○ | ○ |

**Legenda:** ● Cobertura boa | ◐ Cobertura parcial | ○ Sem cobertura

---

## 4. Detalhamento por Ferramenta

### 4.1 SpotBugs + fb-contrib

**Categorias cobertas:** 1 (parcial), 2, 3, 4 (parcial), 5 (parcial), 8

| Categoria | Regras | Nível |
|---|---|---|
| 1. Use-After-Close | `OS_OPEN_STREAM`, `OBL_UNSATISFIED_OBLIGATION` — detecta streams não fechados, mas NÃO operações após close | Parcial |
| 2. Concorrência | `IS2_INCONSISTENT_SYNC`, `AT_OPERATION_SEQUENCE_ON_CONCURRENT_ABSTRACTION` — sincronização inconsistente | Bom |
| 3. hashCode/equals | `HE_EQUALS_NO_HASHCODE`, `HE_HASHCODE_NO_EQUALS` — violação do contrato equals/hashCode | Bom |
| 4. Comparable | Detecta compareTo com float incorreto; NÃO verifica compareTo(null) nem objetos não-Comparable em TreeMap | Parcial |
| 5. Encoding | fb-contrib detecta charset ausente em algumas APIs | Parcial |
| 8. Serialização | `SE_NO_SUITABLE_CONSTRUCTOR` — exatamente o check da spec JavaMOP | Bom |

### 4.2 Error Prone

**Categorias cobertas:** 1 (parcial), 2, 3, 5, 10 (parcial)

| Categoria | Regras | Nível |
|---|---|---|
| 1. Use-After-Close | `StreamResourceLeak`, `MustBeClosedChecker` — detecta leaks, não use-after-close | Parcial |
| 2. Concorrência | `GuardedBy`, `DoubleCheckedLocking`, `SynchronizeOnNonFinalField` | Bom |
| 3. hashCode/equals | `EqualsHashCode` — equals sem hashCode | Bom |
| 5. Encoding | `DefaultCharset` — detecta uso de charset padrão do sistema em String.getBytes(), streams, etc. | Bom |
| 10. parseLong | `AlwaysThrows` — detecta chamadas estaticamente determináveis que sempre lançam exceção | Parcial |

### 4.3 Facebook Infer

**Categorias cobertas:** 1, 2

| Categoria | Checkers | Nível |
|---|---|---|
| 1. Use-After-Close | **Pulse** — análise inter-procedural profunda via lógica de separação; detecta resource leaks e use-after-free | Bom |
| 2. Concorrência | **RacerD** — detecção de race conditions comprovada em escala no Meta | Bom |

### 4.4 SonarQube

**Categorias cobertas:** 1 (parcial), 2, 3, 4 (parcial), 5, 8

| Categoria | Regras | Nível |
|---|---|---|
| 1. Use-After-Close | `S2095` (resources should be closed), `S2093` (try-with-resources) — NÃO detecta operações após close, apenas recursos não fechados | Parcial |
| 2. Concorrência | `S2273` (wait/notify com lock), `S2274` (wait em while loop), `S2276` (wait vs sleep), `S2446` (notifyAll), `S3046` (wait com múltiplos locks), `S1149` (classes sincronizadas legadas), `S3078` (volatile com operadores compostos) — NÃO detecta iteração insegura em coleções sincronizadas | Bom |
| 3. hashCode/equals | `S1206` (equals/hashCode em pares), `S1201` (métodos chamados equals) | Bom |
| 4. Comparable | `S1210` (equals com compareTo), `S2167` (compareTo não deve retornar MIN_VALUE), `S2200` (resultado de compareTo) — NÃO verifica compareTo(null) nem non-Comparable em TreeMap | Parcial |
| 5. Encoding | `S1943` (**detecta `URLEncoder.encode(s)` e `URLDecoder.decode(s)` sem charset** — melhor match com as specs), `S4719` (StandardCharsets) | Bom |
| 8. Serialização | `S2055` (superclasse sem no-arg constructor — match exato), `S2118` (writeObject em não-Serializable), `S1948` (campos transient), `S2057` (serialVersionUID) | Bom |

**Suporte Android no SonarQube:**
- Não possui regras Android-específicas nativas
- Plugins de terceiros (`sonar-android-plugin`, `sonar-android`) importam relatórios do Android Lint
- Analisador Kotlin inclui regras OWASP Mobile Top 10

### 4.5 PMD

**Categorias cobertas:** 2 (parcial)

| Categoria | Regras | Nível |
|---|---|---|
| 2. Concorrência | `DoubleCheckedLocking`, `UnsynchronizedStaticFormatter` | Parcial |

Cobertura limitada para estas categorias específicas.

### 4.6 Checker Framework

**Categorias cobertas:** 1, 2

| Categoria | Checkers | Nível |
|---|---|---|
| 1. Use-After-Close | **Resource Leak Checker** com anotações `@MustCall`, `@CalledMethods` — abordagem mais robusta (sound) | Bom |
| 2. Concorrência | **Lock Checker** com anotações `@GuardedBy` | Bom |

Requer anotações no código-fonte para funcionar plenamente.

### 4.7 Android Lint

Foco em APIs do Android SDK (lifecycle, permissions, API levels). Cobertura marginal para as categorias genéricas Java destas specs.

---

## 5. Categorias SEM Cobertura por Nenhuma Ferramenta

| Categoria | Specs | Motivo |
|---|---|---|
| **6. ListIterator.set()** | `ListIterator_Set.mop` | Requer rastreamento de estado do iterador — naturalmente um problema de runtime |
| **7. ServerSocket config** | `ServerSocket_SetTimeoutBeforeBlocking.mop`, `ServerSocket_Backlog.mop` | Verificação de ordenação temporal de chamadas — difícil estaticamente |
| **9. newSetFromMap** | `Collections_UnnecessaryNewSetFromMap.mop` | Verificação de padrão de uso muito específica |

Essas 4 specs (de 27) representam verificações que **só o JavaMOP consegue fazer** via monitoramento em runtime, demonstrando o valor complementar da abordagem de Runtime Verification.

---

## 6. Gaps Específicos Importantes

Mesmo nas categorias com cobertura, há gaps relevantes entre o que as specs JavaMOP verificam e o que as ferramentas estáticas conseguem detectar:

| Spec JavaMOP | Gap na Análise Estática |
|---|---|
| `*_ManipulateAfterClose.mop` (4 specs) | Ferramentas detectam "recurso não fechado" mas NÃO "operação após close" — o cenário inverso |
| `CharSequence_NotInSet.mop` | Nenhuma ferramenta verifica CharSequence em Sets |
| `CharSequence_UndefinedHashCode.mop` | Nenhuma ferramenta alerta sobre hashCode() em CharSequence |
| `URLConnection_OverrideGetPermission.mop` | Nenhuma ferramenta verifica se subclasses sobrescrevem getPermission() |
| `Comparable_CompareToNullException.mop` | Nenhuma ferramenta verifica se compareTo(null) lança NPE |
| `TreeMap_Comparable.mop`, `TreeSet_Comparable.mop`, `SortedSet_Comparable.mop` | Nenhuma ferramenta verifica se elementos implementam Comparable ao inserir |
| `Collection_UnsynchronizedAddAll.mop` | Nenhuma ferramenta verifica modificação da fonte durante addAll() |
| `Collections_SynchronizedCollection.mop` | SonarQube NÃO detecta iteração insegura em coleções sincronizadas |

---

## 7. Stack Recomendado para Máxima Cobertura Estática

| Prioridade | Ferramenta | Integração | Categorias |
|---|---|---|---|
| 1 | **SpotBugs + fb-contrib** | Gradle plugin | 1, 2, 3, 4*, 5*, 8 |
| 2 | **Error Prone** | Compiler plugin (javac) | 1, 2, 3, 5 |
| 3 | **Infer** | CI pipeline | 1, 2 (análise profunda) |
| 4 | **SonarQube** | Servidor / quality gate | 1, 2, 3, 4*, 5, 8 |

Com esse stack combinado, **~23 de 27 specs** teriam algum nível de cobertura estática (parcial ou total).  
**4 specs permanecem exclusivas do JavaMOP** (categorias 6, 7, 9), além de diversos gaps específicos dentro das categorias cobertas.

---

## 8. Plano de Execução: Análise Estática nos 349 APKs

### 8.1 Escopo e Dataset

- **Specs**: Apenas 27 generic_new
- **APKs**: **349** com `exp01_generic_new=True`
- **Entrada**: Código-fonte (NÃO dex2jar)
- **Ferramentas**: Múltiplas (PMD, SonarQube, SpotBugs)
- **Automação**: Totalmente automatizada, relatórios parseáveis (XML/CSV/JSON)
- **Branch**: Criar branch específica para esta análise

#### Números do Dataset

| Métrica | Valor |
|---|---|
| APKs com `exp01_generic_new=True` | **349** |
| Fontes já baixados (`rvsec-testes-jca/sources/`) | **185** (de 349) |
| Fontes faltantes para download | **164** |
| APKs com URL de sourceCode | **349** (todos) |
| Total APKs F-Droid | 4.162 |
| APKs no dataset completo (`apks_complete.csv`) | 354 |

### 8.2 Caminhos Absolutos

#### Dataset e Resultados do Experimento RV (ase-journal)

| Recurso | Caminho |
|---|---|
| Dataset master (354 APKs) | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/apks/apks_complete.csv` |
| F-Droid completo (4.162) | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/apks/fdroid.csv` |
| Summary generic_new (exp01) | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/summary/exp01_generic_new_summary.csv` |
| Summary generic_new (exp02) | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/summary/exp02_generic_new_summary.csv` |
| Errors (zipped) | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.zip` |
| Data analysis scripts | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/data-analysis/` |
| Paper LaTeX | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/main-icst.tex` |

#### Fontes dos Apps

| Recurso | Caminho |
|---|---|
| 187 fontes já baixados | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-testes-jca/sources/` |
| Script download (base) | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-testes-jca/download_sources.py` |
| Script download 188 | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-testes-jca/download_188_sources.py` |
| Config centralizada | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-testes-jca/config.py` |

#### Specs JavaMOP

| Recurso | Caminho |
|---|---|
| 27 specs generic_new | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/generic_new/` |

#### Projetos de Referência

| Recurso | Caminho |
|---|---|
| CogniCrypt batch script | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-cognicrypt/run_batch_analysis.py` |
| CogniCrypt output (154 CSVs) | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-cognicrypt/output/` |
| APKs compilados (557) | `/home/pedro/desenvolvimento/RV_ANDROID/NOVO/APKS/` |
| Repo rvsec (branch atual: modules) | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/` |

### 8.3 Fases de Execução

#### Fase 0: Setup do Projeto

1. Criar branch a partir de `modules`:
   ```bash
   git checkout -b generic-new-static-analysis modules
   ```

2. Criar estrutura do novo projeto (ao lado de `rvsec-cognicrypt/`):
   ```
   rvsec-static-generic/
   ├── scripts/
   │   ├── download_sources.py       # Adaptado de rvsec-testes-jca
   │   ├── run_pmd.py                # Batch PMD
   │   ├── run_sonarqube.py          # Batch SonarQube
   │   ├── run_spotbugs.py           # Batch SpotBugs (se compilação viável)
   │   ├── parse_results.py          # Parser unificado → CSV
   │   ├── compare_tools.py          # Comparação entre ferramentas
   │   └── config.py                 # Configuração centralizada
   ├── sources/                      # Código-fonte dos 349 apps
   ├── output/
   │   ├── pmd/                      # Relatórios PMD (XML)
   │   ├── sonarqube/                # Relatórios SonarQube (JSON)
   │   ├── spotbugs/                 # Relatórios SpotBugs (XML)
   │   └── unified/                  # CSV unificado para comparação
   ├── results/
   │   ├── metrics.csv               # Métricas de execução
   │   ├── coverage_matrix.csv       # Ferramenta × Categoria × Detecção
   │   └── comparison_report.md      # Relatório final
   └── rules/
       ├── pmd_ruleset.xml           # Ruleset customizado
       ├── spotbugs_filter.xml       # Filtro SpotBugs
       └── sonarqube_profile.json    # Quality profile customizado
   ```

#### Fase 1: Download de Fontes Faltantes

1. Adaptar `download_sources.py` de `rvsec-testes-jca/` para:
   - Ler `apks_complete.csv` de `ase-journal/dataset/results/apks/`
   - Filtrar `exp01_generic_new=True`
   - Copiar/linkar os 185 que já existem em `rvsec-testes-jca/sources/`
   - Baixar os 164 faltantes via URLs do F-Droid
2. Validar download (taxa de sucesso esperada ~99%)
3. Catalogar APKs com/sem fonte disponível

#### Fase 2: Configuração e Execução das Ferramentas

**Prioridade 1 — PMD (sem compilação)**
- Instalação: Download PMD CLI
- Entrada: Código-fonte Java direto
- Ruleset customizado (`rules/pmd_ruleset.xml`):
  - `java-multithreading`: DoubleCheckedLocking, NonThreadSafeSingleton, UnsynchronizedStaticFormatter
  - `java-errorprone`: CloseResource
- Comando: `pmd check -d <source> -R pmd_ruleset.xml -f xml -r output/pmd/<apk>.xml`
- Saída: XML parseável

**Prioridade 2 — SonarQube (sem compilação obrigatória)**
- Instalação: `docker run -d sonarqube:community`
- Scanner: `sonar-scanner-cli`
- Quality Profile customizado com regras:
  - S1206 (hashCode/equals), S2273 (wait/notify), S1943 (URLEncoder charset)
  - S2055 (serialization), S2095 (resources), S1210 (compareTo)
  - S2274, S2276, S2446, S4719, S1201
- Automação: `sonar-scanner -Dsonar.projectKey=<apk> -Dsonar.sources=<dir>`
- Saída: JSON via REST API (`/api/issues/search`)

**Prioridade 3 — SpotBugs + fb-contrib (precisa compilar)**
- Desafio: Precisa de bytecode (.class), requer compilação via Gradle
- Múltiplas versões Java/Gradle (como em rvsec-testes-jca)
- Filtro XML para bug patterns relevantes:
  - `HE_EQUALS_NO_HASHCODE`, `SE_NO_SUITABLE_CONSTRUCTOR`
  - `IS2_INCONSISTENT_SYNC`, `OS_OPEN_STREAM`, `OBL_*`
- Saída: XML (`-xml:withMessages`)

**Opcional — Infer (precisa compilar)**
- `infer capture -- gradle build` + `infer analyze`
- Checkers: THREAD_SAFETY (RacerD), PULSE_RESOURCE_LEAK
- Saída: JSON (`infer-out/report.json`)

#### Fase 3: Execução em Batch

Script Python seguindo o padrão de `rvsec-cognicrypt/run_batch_analysis.py`:
- ProcessPoolExecutor com MAX_WORKERS
- Timeout por app
- Resume capability (pular já analisados)
- Métricas: tempo, status, contagem de erros
- Log de progresso

#### Fase 4: Parsing e Unificação

Formato CSV unificado:
```csv
tool,apk,category,rule_id,rule_name,class,method,line,message,severity
```

Mapeamento regras → 10 categorias:

| Categoria | PMD | SpotBugs | SonarQube |
|---|---|---|---|
| 1. Use-After-Close | CloseResource | OS_OPEN_STREAM, OBL_* | S2095, S2093 |
| 2. Concorrência | DoubleCheckedLocking, NonThreadSafeSingleton | IS2_*, AT_* | S2273, S2274, S2276, S2446 |
| 3. hashCode/equals | — | HE_EQUALS_NO_HASHCODE, HE_* | S1206, S1201 |
| 4. Comparable | — | — | S1210, S2167, S2200 |
| 5. Encoding UTF-8 | — | (fb-contrib) | S1943, S4719 |
| 6. ListIterator | — | — | — |
| 7. ServerSocket | — | — | — |
| 8. Serialização | — | SE_NO_SUITABLE_CONSTRUCTOR | S2055, S2118 |
| 9. newSetFromMap | — | — | — |
| 10. parseLong | — | — | — |

#### Fase 5: Análise e Relatório

1. Matriz de cobertura: Ferramenta × Categoria × APKs com detecção
2. Estatísticas: violações por ferramenta, categoria, app
3. Overlap: violações detectadas por múltiplas ferramentas
4. Gaps: categorias sem cobertura (6, 7, 9, 10)
5. Comparação com RV generic_new (`exp01_generic_new_summary.csv`)

### 8.4 Verificação

1. Executar cada ferramenta em 1 app primeiro para validar pipeline
2. Verificar que relatórios são parseáveis (XML/JSON → CSV unificado)
3. Validar mapeamento de regras: conferir manualmente 5-10 detecções
4. Validar automação end-to-end antes de rodar batch completo
5. Comparar resultados com `exp01_generic_new_summary.csv` (RV)

---

## 9. Conclusão

A análise estática cobre bem **concorrência**, **hashCode/equals**, **encoding** e **serialização**, mas tem limitações significativas em verificações que dependem de **estado temporal** (use-after-close, ordenação de chamadas, estado do iterador). Isso reforça o valor da **Runtime Verification via JavaMOP** como abordagem complementar: enquanto ferramentas estáticas detectam padrões estruturais no código, o JavaMOP monitora comportamentos em tempo de execução que são inerentemente difíceis de capturar estaticamente.
