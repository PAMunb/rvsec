# Plano de Refatoração RV-Android

**Data**: 2026-02-15
**Autor**: Pedro Henrique Teixeira Costa (com assistência de Claude Code)
**Baseado em**: Análises Gemini (`docs/analise_gemini.md`), Qwen (`docs/analise_qwen.md`), e investigação direta no código

> **Natureza deste documento**: Este é um artefato de **Phase 0 (Ideação)** conforme `docs/WORKFLOW.md` Section 1. Ele NÃO é um artefato OpenSpec — é material de referência que alimenta as changes futuras. Quando as changes forem criadas, o conteúdo relevante migra para os artefatos OpenSpec:
>
> - **Sessão 1 (R1-R4)**: Conteúdo migra para `openspec/changes/gh<N>-refactoring-cleanup/` usando schema `quick-path` (2 artefatos: `plan.md` com context, scope, file inventory, acceptance criteria + `tasks.md` com execution checklist)
> - **Sessão 2 (R5)**: Conteúdo alimenta `/opsx:ff` que gera `proposal.md`, delta specs, `design.md`, `tasks.md` usando schema `rv-sdd`
> - **Após criação das changes**: Este documento é movido para `backup/20260215_plano_refatoracao.md` (P3)
>
> As decisões D1-D8 (Seção 4) e as análises de impacto (Seção 6) permanecem relevantes como contexto histórico de Phase 0 — referenciados nas changes mas não duplicados.

---

## 1. Contexto e Metodologia

Duas LLMs externas (Gemini e Qwen) analisaram o sistema RV-Android a partir da documentação (PRD, WORKFLOW, specs, CLAUDE.md) e propuseram planos de refatoração. Este documento valida essas sugestões contra o **código real**, filtrando pelo princípio P1 (Simplicidade) para identificar o que é genuinamente benéfico vs. over-engineering.

**Metodologia**: Para cada sugestão das LLMs, exploramos o código fonte, medimos complexidade real (LOC, métodos, acoplamento), e categorizamos como:
- **Aceito**: Problema real confirmado no código, solução alinhada com P1
- **Rejeitado**: Sugestão teórica sem problema real correspondente, ou solução que violaria P1
- **Oportunidade identificada**: Problema real encontrado durante investigação que não foi sugerido pelas LLMs

Complementamos com um **audit de TODO/FIXME** (25 ocorrências em 15 arquivos) para mapear débito técnico existente.

---

## 2. Veredito: A Maioria das Sugestões é Over-Engineering

Ambas as LLMs analisaram a partir de documentação, não do código. Suas recomendações propõem, em grande parte, padrões enterprise que **aumentariam** a complexidade ao invés de reduzi-la. O codebase está **bem arquitetado** — o sistema de componentes, configuração JIT, e fronteiras de módulos são limpos e funcionais.

### 2.1. Sugestões Rejeitadas

| Sugestão | Fonte | Por que Rejeitada |
|----------|-------|-------------------|
| ConfigurationProvider / Service Locator | Gemini 2.1 | Os métodos JIT de config têm 15-20 linhas cada, são pass-through simples. Adicionar um registry introduz indireção sem benefício. ExperimentConfig tem 22 métodos, 813 linhas — adequado para a responsabilidade. |
| EventBus para coordenação de fases | Gemini 2.3 | As fases são inerentemente sequenciais (monitores → instrumentação → execução). Event-driven adiciona complexidade, não flexibilidade. O PreProcessor (325 linhas, 8 métodos) já é limpo e bem separado. |
| Novos módulos: rv-task-generator, rv-results-processor | Gemini 2.2 | Geração de tarefas = 63 linhas (produto cartesiano simples em `Platform._generate_tasks()`). Processamento de resultados = 667 linhas em um componente (`ResultProcessorComponent`). Nenhum justifica um módulo próprio. |
| Módulo rv-android-infra | Gemini 3.1 | A estrutura do core é intencional: `domain/` (modelos), `util/android/` (EmulatorManager, LogcatManager), `util/error/` (ErrorHandler). São diretórios separados dentro de core, não misturados. 48 arquivos, ~10.873 linhas — é o módulo fundação, ter ambos é sua função. |
| Facade para RVAgent | Gemini 3.3 | O construtor tem 10 dependências focadas via DI correto. Cada uma é single-responsibility. Adicionar facades intermediárias = mais indireção. O construtor é transparente e testável — exatamente o oposto de "bloated". |
| Slicing do AgentState nos nodes | Gemini 3.3 | Os nodes já acessam apenas suas fatias necessárias. parse_node retorna 7 campos (não 60). algorithm_node acessa strategy/screen, não toca em LLM fields. O LangGraph gerencia o merge corretamente. |
| Abstract Factory, Builder, Command, Chain of Responsibility, Event Sourcing, Mediator | Qwen | Pattern catalog dumping. Nenhum problema concreto que esses padrões resolveriam foi identificado no código. |
| Fundir rv-uiautomator + rv-tools | Qwen | Concerns diferentes: rv-uiautomator é interação com dispositivo (UIAutomator2 adapter); rv-tools é sistema de plugins de ferramentas de teste. |
| Fundir rv-monitor-generator + rv-instrumentation | Qwen | Lifecycle diferente: geração de monitores roda uma vez por spec set; instrumentação roda por APK. São etapas distintas no pipeline. |
| Execução paralela de tarefas | Qwen | Cada tarefa precisa de um emulador. Multi-emulador = escopo totalmente diferente (orquestração Docker já existe para isso). |
| Circuit breakers | Qwen | Padrão enterprise para microserviços em produção. RV-Android é ferramenta de pesquisa. |

### 2.2. Dados que Suportam a Rejeição

| Componente | LOC | Métodos | Avaliação |
|------------|-----|---------|-----------|
| ExperimentConfig | 813 | 22 | Métodos JIT simples, pass-through. **OK** |
| PreProcessor | 325 | 8 | Orquestração limpa, imports on-demand, fallback graceful. **OK** |
| TaskExecutor | 388 | 18 | Gerenciador de componentes bem desenhado, NÃO é god module. **OK** |
| 7 Components (Platform) | 1.858 | ~40 | Single responsibility cada, granularidade adequada. **OK** |
| Task Generation | 63 | 1 | Produto cartesiano direto. **OK** |
| Result Processing | 667 | 16 | Adequado para 5 CSVs + JSON + reconstrução logcat. **OK** |
| RVAgent constructor | 14 params | 40 linhas | DI correto, cada dep é single-responsibility. **OK** |
| AgentState | 60 campos | 11 grupos | Grande mas organizado, nodes slice corretamente. **OK** |
| rv-agent-validation | 7.858 linhas | 36 arquivos | Dependências adequadas para test harness. **OK** |

---

## 3. Itens Aceitos para Refatoração

### Item R1: Magic Numbers de Coordenadas → Usar Utilitários Existentes

**Prioridade**: ALTA
**Track**: Quick Path (refatoração mecânica, sem decisão de design)
**Módulo**: rv-agent

**Problema**: O padrão `int(device_x * 704 / 1080)` / `int(device_y * 1248 / 1920)` está copy-pasted 8+ vezes no codebase. Enquanto isso:
- `RVAgentConstants.SCREENSHOT_TARGET_WIDTH = 704` e `SCREENSHOT_TARGET_HEIGHT = 1248` existem em `constants.py`
- `coordinate_utils.device_to_optimized()` já implementa exatamente essa conversão

**Ocorrências** (8 locais com math inline):

| Arquivo | Linhas | Contexto |
|---------|--------|----------|
| `strategies/dfs_strategy.py` | 521-522 | `_generate_action_signature()` |
| `strategies/bfs_strategy.py` | 523-524 | `_generate_action_signature()` |
| `strategies/rvagent_strategy/rvagent_strategy.py` | 829-830 | `_normalize_to_optimized_space()` fallback |
| `strategies/rvagent_strategy/ranking/scorers.py` | 213-214 | `MopScorer._convert_to_optimized()` |
| `strategies/rvagent_strategy/ranking/scorers.py` | 338-339 | `WtgScorer._convert_to_optimized()` |
| `strategies/rvagent_strategy/ranking/scorers.py` | 483-484 | `ComponentPriorityScorer._convert_to_optimized()` |
| `agent/nodes/learn_node.py` | 338-339 | Conversão em `_update_strategy_with_result()` |

**Também**: 3 locais com `1794` hardcoded (nav bar threshold) em dfs/bfs/greedy strategies.

**Solução**:
1. Adicionar a `constants.py`: `DEFAULT_DEVICE_WIDTH = 1080`, `DEFAULT_DEVICE_HEIGHT = 1920`, `NAVBAR_THRESHOLD_Y = 1794`
2. Substituir os 8 locais por chamada a `coordinate_utils.device_to_optimized()`
3. Substituir os 3 locais com `1794` pelo novo constant

**Utilitário existente** (não precisa criar): `modules/rv-agent/src/rv_agent/services/coordinate_utils.py:device_to_optimized()`

**Critério de aceite**: `grep -rn "704 / 1080\|1248 / 1920\|* 704\|* 1248" modules/rv-agent/src/` retorna 0 ocorrências (exceto constants.py e coordinate_utils.py docstrings).

---

### Item R2: Método Duplicado em ExperimentConfig

**Prioridade**: ALTA
**Track**: Quick Path (remoção de código morto, P3)
**Módulo**: rv-experiment

**Problema**: `get_rv_instrumentation_config()` está definido duas vezes:
- **Linhas 500-527**: Versão com docstring completo — chama `self.get_instrumentation_config()`
- **Linhas 733-744**: Duplicata com docstring menor — também chama `self.get_instrumentation_config()`

A segunda definição (733-744) faz shadow da primeira. Ambas fazem a mesma coisa. Violação de P3 (código morto).

**Arquivo**: `modules/rv-experiment/src/rv_experiment/config.py`

**Solução**: Deletar linhas 733-744 (a duplicata). Manter linhas 500-527 (tem docstring abrangente).

**Critério de aceite**: `grep -n "def get_rv_instrumentation_config" modules/rv-experiment/src/rv_experiment/config.py` retorna exatamente 1 resultado.

---

### Item R3: Limpeza de TODOs Obsoletos e Resolução de Pendências

**Prioridade**: MÉDIA
**Track**: Quick Path (limpeza mecânica)
**Módulos**: Vários

O audit completo encontrou 25 TODO/FIXME em 15 arquivos. A tabela abaixo classifica cada um com decisão:

#### 3.1. TODOs para DELETAR (obsoletos ou sem conteúdo)

| Arquivo | Linha | Conteúdo | Decisão |
|---------|-------|----------|---------|
| `rv-screen-parser/.../screenshot_analyzer.py` | 154 | `# TODO` (sem descrição) | **Deletar**: Comment vazio, código ao redor funciona |
| `rv-screen-parser/.../default_visitor.py` | 624 | `# TODO` (sem descrição) | **Deletar**: Comment vazio, implementação existe |
| `rv-experiment/.../pre_processor.py` | 157 | `# TODO salvar arquivo de erros json` | **Deletar**: Já resolvido — linhas 159-160 explicam que ResultManager cuida disso |

#### 3.2. TODOs para CONVERTER em GitHub Issues (trabalho futuro legítimo)

| Arquivo | Linha | Conteúdo | Issue Sugerida |
|---------|-------|----------|----------------|
| `rv-agent/.../screen_node.py` | 120 | `record_action_failure()` nunca chamada, FailedActionScorer sempre vazio | **Issue**: "Conectar detecção de falhas ao FailedActionScorer" — relaciona com Item R5 |
| `rv-agent/.../learn_node.py` | 307 | Limitações da heurística de sucesso (hash-based) | **Issue**: "Melhorar detecção de sucesso de ação além de screen hash" |
| `rv-agent/.../screen_analyzer.py` | 271 | Usa scorers simplificados em vez dos reais do rvagent_strategy | **Issue**: "Unificar scoring entre screen_analyzer e rvagent_strategy" |
| `rv-agent/.../device_interface.py` | 381 | `press_keycode()` TODO implementar | **Issue**: "Implementar press_keycode no DeviceInterface" |
| `rv-instrumentation/.../rvandroid.py` | 637, 895, 1027 | Dynamic Android JAR/min-api selection | **Issue**: "Seleção dinâmica de Android JAR baseada em target SDK do APK" |
| `rv-android-core/.../dynamic_wtg.py` | 417 | Type mismatch: `record_transition` expects List[Dict] mas recebe strings | **Issue**: "Corrigir tipo de parâmetro em DynamicWTG.record_transition()" |
| `rv-android-core/.../task.py` | 207, 209 | `skip_installation` e `export_to_csv` marcados para remoção | **Issue**: "Remover campos deprecated de TaskConfiguration" (verificar uso antes) |

#### 3.3. TODOs para RESOLVER INLINE (esclarecimento rápido)

| Arquivo | Linha | Conteúdo | Ação |
|---------|-------|----------|------|
| `rv-screen-parser/.../abstract_visitor.py` | 72 | `self.device_info = {} # TODO deprecated` | Verificar se `device_info` é usado em algum lugar. Se não → deletar campo e TODO |
| `rv-screen-parser/.../default_visitor.py` | 131 | `# TODO rever` na lógica de MOP checking | Avaliar se a lógica está correta. Se sim → deletar TODO. Se não → corrigir e deletar TODO |
| `rv-screen-parser/.../visitor_factory.py` | 52 | `# TODO rever argumento` | Verificar se passagem de argumento está correta. Se sim → deletar TODO |
| `rv-static-analysis/.../gesda_parser.py` | 161 | `# TODO rever tipo` na criação de Widget | Verificar tipo correto. Se correto → deletar TODO |
| `rv-experiment/.../config.py` | 175 | `Directory structure validation # TODO` | Remover da docstring ou implementar validação |
| `rv-experiment/.../__main__.py` | 864 | `# TODO remover esses "templates"` | Verificar se templates são usados no CLI. Se não → deletar |
| `rv-android-core/.../android.py` | 10 | `# TODO logging manager` | Mudar para LoggingManager se desejado, ou deletar TODO se não prioritário |
| `rv-static-analysis/.../static_analysis.py` | 383 | `# TODO usar performance monitor` | Deletar TODO — tracking manual de tempo é adequado (P1) |
| `rv-agent/.../memory_coordinator.py` | 219 | `success=True # TODO: Track actual success` | Relacionado com Item R5 (error detection) — manter se R5 for implementado, senão converter em Issue |
| `rv-instrumentation/.../rvandroid.py` | 794 | `# TODO: Implement zipalign` | Manter como comment ou converter em Issue — é otimização de baixa prioridade |

#### 3.4. TODOs de Config do RV-Agent (investigados com evidência)

| Arquivo | Linha | Conteúdo | Evidência | Ação |
|---------|-------|----------|-----------|------|
| `agent_config.py` | 50 | `# TODO O que teremos de output?` | `results_dir` É usado pelo CLI standalone (`cli/main.py:93,101,114`) para `metrics_output_dir`. Campo funcional. | **Deletar TODO**, manter campo |
| `agent_config.py` | 124 | `# TODO qual a diferença para debug_mode?` | `debug_mode` é set pelo CLI `--debug` flag → força logging.DEBUG. `log_level` é campo separado com env var override (`RVAGENT_LOG_LEVEL`). Overlapping mas cada um tem uso. | **Deletar TODO**, adicionar comment esclarecendo: `debug_mode` é shortcut do CLI, `log_level` é config granular |
| `agent_config.py` | 128 | `# TODO não entendi... para que serve?` | `get_verbose_counters()` método existe mas **NENHUM código chama ele**. Grep por `[COUNTER]` ou `verbose_counters` fora de config = 0 resultados. Código morto. | **Deletar campo** `verbose_counters` e método `get_verbose_counters()` (P3) |
| `agent_config.py` | 140 | `# TODO está sendo usado?` | Usado em `validate()` (linha 410): `if not self.enable_coordinate_enhancement: return False, "...mandatory..."`. Ou seja, settar False **falha validação**. É efetivamente hardcoded True. | **Deletar campo** e remover check em `validate()` (P1: flag que só pode ser True não é flag) |

**Critério de aceite**: `grep -rn "TODO\|FIXME\|HACK\|XXX" modules/*/src/ --include="*.py" | wc -l` reduz de 25 para ≤5 (apenas os convertidos em Issues legítimas que merecem comment inline).

---

### Item R4: Padrão de Inicialização dos Detectors (rv-screen-parser)

**Prioridade**: BAIXA
**Track**: Quick Path
**Módulo**: rv-screen-parser

**Problema**: 4 classes detector têm init idêntico (5-6 linhas cada):
```python
def __init__(self):
    logging_manager = LoggingManager.get_instance()
    self.logger = logging_manager.get_logger("screenshot.{name}", {CONTEXT_COMPONENT: "{Name}"})
    self.geometry_utils = get_geometry_utils()
```

**Arquivos**: `button_detector.py`, `error_detector.py`, `interactive_element_detector.py`, `text_detector.py`

**Decisão**: **AVALIAR durante implementação**. P1 diz "three similar lines > premature abstraction". São 5 linhas × 4 arquivos. Uma `BaseDetector` classe adiciona indireção. Considerar se o benefício justifica a abstração, ou se o padrão inline é aceitável.

---

### Item R5: Integração do ErrorDetector no rv-agent (Oportunidade Nova)

**Prioridade**: ALTA
**Track**: FF SDD (decisão de design necessária, single module rv-agent, reqs claros)
**Módulo**: rv-agent (consumidor), rv-screen-parser (provider, sem mudanças)

**Contexto**: rv-screen-parser tem um `ErrorDetector` sofisticado (790 linhas) que detecta:
- Erros de rede ("no internet", "connection failed")
- Erros de permissão ("permission denied")
- Erros de validação ("invalid format", "required field")
- Erros de sistema ("application crashed", "system error")
- Diálogos de erro (padrões visuais + cor + texto)
- Toasts de erro, banners, snackbars

**Gap no rv-agent**: Nenhuma integração existe. O rv-agent:
- Não detecta quando o app mostra erros/crashes/ANRs
- Não usa `ScreenshotAnalyzer` ou `ErrorDetector`
- `record_action_failure()` nunca é chamada (TODO no screen_node.py:120)
- `FailedActionScorer` sempre retorna 0 (dados de falha sempre vazios)
- Stuck detection é puramente hash-based, não error-aware

**Infraestrutura existente** (90% pronta, só precisa conectar):
- `ScreenNode.record_action_failure()` — existe mas não é chamada
- `FailedActionScorer` — scorer com -9999 para ações falhadas, mas set vazio
- `StuckRecovery` — backtrack BFS já implementado
- `ErrorDetector` — completo em rv-screen-parser

**Benefício principal**: No modo pure_algorithm, o agente atualmente desperdiça iterações repetindo ações que causam erros. Com error detection:
1. Detectaria erros após ações → marcaria ação como falhada
2. `FailedActionScorer` atribuiria -9999 → ação nunca mais selecionada
3. Recovery automático: BACK para sair do estado de erro
4. Melhoria direta em cobertura e eficiência de exploração

#### 5.1. Análise do Pipeline Antigo (rvsmart)

A ferramenta descontinuada `rvsmart` (backup em `backup/rvsmart-tool/`) tinha integração funcional com o ErrorDetector. Análise do pipeline para informar o design do rv-agent:

**Pipeline do rvsmart (6 etapas):**
```
Screenshot → ScreenshotAnalyzer → ErrorDetector → ScreenshotActionComplementor → StateEnricher → Prompt (LLM)
```

| Etapa | Arquivo (backup/rvsmart-tool/) | O que fazia |
|-------|-------------------------------|-------------|
| 1. Análise visual | `analysis/screenshot/screenshot_action_complementor.py:396-399` | `ScreenshotAnalyzer.extract_information()` executa ErrorDetector internamente (3 estratégias: cor HSV, texto regex, padrões visuais) |
| 2. Associação UI | `analysis/screenshot/screenshot_action_complementor.py:542-611` | `ErrorAssociationStrategy` associa cada erro visual ao elemento UI mais próximo. Prioriza EditTexts (1.2x boost), detecta erros de validação abaixo de campos (heurística posicional) |
| 3. Marcação | `analysis/screenshot/screenshot_action_complementor.py:583-591` | `item.complement["has_error"] = True`, adiciona `[ERR]` na descrição de elementos com confiança ≥ 0.8 |
| 4. Enriquecimento | `llm/service/state_enricher.py:152-208` | `StateEnricher` integra erros no state dict: `STRUCTURED_SCREEN` (ScreenDescription com `[ERR]`), `SCREENSHOT_INFO` (visual mapping com error_indicators) |
| 5. Prompt LLM | `llm/prompt/fragments/screenshot_fragment.py:138-160` | Contagem de erros e anotações `[ERR]` incluídas no prompt para guiar o LLM |
| 6. Tracking | `llm/service/action_service.py:604-637` | MOP errors rastreados via EventBus (último 5 erros mantidos para contexto) |

**O que o rvsmart NÃO fazia** (gap que o rv-agent pode preencher):
- Nenhuma lógica de **recovery** (não pressionava BACK ao detectar erro)
- Nenhuma **blacklist** de ações falhadas (não evitava repetir ações que causam erros)
- A detecção era puramente **informativa para o LLM** (passiva), não **reativa para o algoritmo**

#### 5.2. Comparação Direta: rvsmart vs rv-agent

| Aspecto | rvsmart (antigo) | rv-agent (atual) |
|---------|-----------------|-----------------|
| **Quem detecta erros** | `ScreenshotAnalyzer` + `ErrorDetector` (CV) | Ninguém |
| **Quando detecta** | Cada iteração, no `StateEnricher` | — |
| **O que faz com erros** | Marca `[ERR]` no prompt do LLM | — |
| **Associa erro a elemento?** | Sim, `ErrorAssociationStrategy` com bounding box | — |
| **Recovery automático?** | Não | Não (mas infra existe: `StuckRecovery`) |
| **Blacklist de ações?** | Não | Infra existe (`FailedActionScorer`) mas dados vazios |
| **Custo computacional** | Alto (Tesseract OCR + OpenCV por frame) | Zero |

**Conclusão**: O rv-agent pode fazer **mais** que o rvsmart fazia, porque possui infraestrutura algorítmica que o rvsmart não tinha (FailedActionScorer, StuckRecovery com Backtrack BFS). A diferença é que rvsmart usava error detection como **informação contextual para o LLM** (passivo), enquanto o rv-agent pode usar como **trigger para decisões algorítmicas** (ativo: blacklist + recovery).

#### 5.3. Dependências de Sistema — BLOCKER SIGNIFICATIVO

O `ErrorDetector` depende de `cv2` (OpenCV) e o `ScreenshotAnalyzer` completo depende também de `pytesseract` (Tesseract OCR). Essas são dependências **pesadas** com requisitos de sistema:

**Dependências Python** (já instaladas via rv-screen-parser, que é dep do rv-agent):
```toml
# rv-screen-parser/pyproject.toml
"pytesseract>=0.3.0"     # Bindings Python para Tesseract
"opencv-python>=4.10.0"  # OpenCV
"numpy>=2.1.0"           # Dependência do OpenCV
```

**Dependências de sistema (apt) — NÃO instaladas nas imagens Docker atuais**:
```bash
sudo apt-get install -y tesseract-ocr libtesseract-dev libopencv-dev python3-opencv
```

**Status nas imagens Docker**:
| Imagem | Base | Tem tesseract/opencv? |
|--------|------|----------------------|
| `docker/base/Dockerfile` | `python:3.12.12-slim-trixie` | **NÃO** — instala apenas Java, Maven, AspectJ, uv, Docker CLI |
| `docker/tools/Dockerfile` | `phtcosta/rvsec_android:0.8.0` | **NÃO** — apenas instala DroidBot |
| `docker/rvandroid/Dockerfile` | `phtcosta/rvandroid_tools:0.8.0` | **NÃO** — clone + uv sync + entrypoint |
| `docker/rvandroid_dev/Dockerfile` | Precisa verificar | Provavelmente **NÃO** |

**Impacto**: Usar ErrorDetector no rv-agent implica:
1. Adicionar `apt-get install tesseract-ocr libtesseract-dev` no Dockerfile base ou tools
2. As libs Python (`pytesseract`, `opencv-python`) já são transitivas via `rv-screen-parser` (uv sync já instala)
3. Reconstruir **todas** as imagens Docker da chain (base → android → tools → rvandroid)
4. Testar que a chain Docker funciona corretamente com as novas deps
5. Aumento no tamanho das imagens (~150-300MB para tesseract + modelos OCR)

#### 5.4. Alternativas para Mitigar o Custo de Dependências

| Alternativa | Descrição | Prós | Contras |
|-------------|-----------|------|---------|
| **A. ErrorDetector completo** | Usar `ScreenshotAnalyzer` com todas as 3 estratégias | Detecção mais precisa | Requer tesseract + opencv no Docker, ~300ms por frame |
| **B. Só color-based** | Usar apenas `ErrorDetector._detect_color_errors()` | Só precisa de OpenCV (sem tesseract), ~50ms | Perde detecção textual, sem OCR |
| **C. Text-based via UI hierarchy** | Analisar textos do UIAutomator dump com os mesmos regexes do ErrorDetector | **Zero dependências novas**, ~5ms | Não detecta erros visuais (cor, ícones), só texto |
| **D. Detecção condicional** | Analisar screenshot só quando hash não mudou (possível dialog de erro) | Reduz chamadas (só em stuck), custo amortizado | Pode perder erros em telas novas |

**Recomendação para design doc**: Avaliar **Alternativa C** como opção P1-compliant — extrair os regex patterns do ErrorDetector e aplicá-los nos textos já extraídos pelo UIAutomator dump, sem nenhuma dependência nova. Se insuficiente, escalar para **Alternativa B** (OpenCV only) ou **A** (completo).

#### 5.5. Complexidade e Decisões de Design

**Complexidade estimada**: Média a Alta (depende da alternativa escolhida)

Para qualquer alternativa, precisa de:
1. Decidir **onde** no workflow detectar erros (parse_node? learn_node? novo node?)
2. Decidir **como** propagar erros para `record_action_failure()`
3. Decidir **quando** acionar recovery (BACK imediato? threshold de erros?)
4. Se alternativas A/B: atualizar Docker (rebuild chain, testar)

**Este item requer design doc e deve seguir FF SDD**. Criar GitHub Issue, rodar `/opsx:ff`, implementar via `/opsx:apply`.

---

## 4. Decisões Técnicas Documentadas

### Decisão D1: Não criar novos módulos para extrair funcionalidade existente

**Contexto**: Gemini sugeriu rv-task-generator, rv-results-processor, rv-android-infra.
**Decisão**: Rejeitar. Princípio P1 — a complexidade atual é adequada ao propósito.
**Fundamentação**: Task generation = 63 LOC, result processing = 667 LOC em componente único, core separa domain/ de util/ por diretórios. Extrair para módulos separados criaria overhead de pyproject.toml, __init__.py, imports cruzados, sem ganho de clareza.

### Decisão D2: Não adotar Service Locator ou EventBus

**Contexto**: Gemini sugeriu ConfigurationProvider e EventBus para fases do experimento.
**Decisão**: Rejeitar. Princípio P1 — "a direct function call is better than an event-driven indirection when only one subscriber exists."
**Fundamentação**: Os métodos JIT são chamadas diretas de 15-20 linhas. As fases do experimento são inerentemente sequenciais (não se pode instrumentar antes de gerar monitores). Service Locator e EventBus resolveriam problemas que não existem.

### Decisão D3: Não fundir módulos

**Contexto**: Qwen sugeriu fundir rv-uiautomator+rv-tools, rv-monitor-generator+rv-instrumentation.
**Decisão**: Rejeitar. Módulos têm responsabilidades e lifecycles distintos.
**Fundamentação**: rv-uiautomator = adapter de dispositivo, rv-tools = sistema de plugins. rv-monitor-generator = gerar monitores (1x por spec set), rv-instrumentation = instrumentar APKs (1x por APK). Fundir misturaria concerns.

### Decisão D4: Usar coordinate_utils existente em vez de criar nova abstração

**Contexto**: 8+ locais com math inline de conversão de coordenadas.
**Decisão**: Usar `device_to_optimized()` de `coordinate_utils.py` que já existe.
**Fundamentação**: Não criar nova utilidade — a função já existe, é testada, e faz exatamente o que os 8 locais fazem manualmente. P1: usar o que existe.

### Decisão D5: Error detection no rv-agent segue FF SDD

**Contexto**: Integrar ErrorDetector do rv-screen-parser no rv-agent é uma capability nova.
**Decisão**: Seguir FF SDD track por ser decisão de design em single module (rv-agent).
**Fundamentação**: A integração requer decisões sobre onde no workflow colocar a detecção (parse_node? learn_node?), como propagar para FailedActionScorer, e como triggerar recovery. Essas são decisões de design que se beneficiam de um design doc, mesmo que breve.

### Decisão D6: Avaliar alternativa text-based (sem dependências novas) antes de usar ScreenshotAnalyzer

> Ver análise completa em Seção 6.1.

**Contexto**: O `ErrorDetector` completo (via `ScreenshotAnalyzer`) depende de OpenCV (`cv2`) e Tesseract OCR (`pytesseract`). Embora as libs Python sejam transitivas via rv-screen-parser, os pacotes de sistema (`tesseract-ocr`, `libtesseract-dev`) **não estão instalados** em nenhuma imagem Docker da chain (base → android → tools → rvandroid). Usar o ErrorDetector completo implica: (1) adicionar deps no Dockerfile, (2) rebuild de todas as imagens, (3) aumento de ~150-300MB no tamanho, (4) tempo de OCR (~300ms por frame).
**Decisão**: O design doc (FF SDD) deve avaliar primeiro a **Alternativa C** (text-based via UI hierarchy) — aplicar os mesmos regex patterns do ErrorDetector nos textos já extraídos pelo UIAutomator dump. Se insuficiente, escalar para Alternativa B (OpenCV only, sem Tesseract) ou A (completo). A escolha será documentada no design doc com trade-offs.
**Fundamentação**: P1 (Simplicidade) — a alternativa mais simples (regex em texto existente) pode resolver 80% dos casos (erros textuais como "permission denied", "connection failed", "invalid format") sem nenhuma dependência nova e com custo ~5ms. Erros puramente visuais (cor sem texto) são menos frequentes em apps reais. O pipeline antigo do rvsmart (analisado em `backup/rvsmart-tool/src/rvsmart_tool/`) usava o ScreenshotAnalyzer completo, mas no contexto de um tool LLM-driven onde screenshots já eram capturados. O rv-agent em `pure_algorithm` mode não captura screenshots regularmente.

### Decisão D7: R5 é implementado após gh9-docker-calibration completo

**Contexto**: R5 (ErrorDetector integration) pode exigir mudanças em imagens Docker (se Alt A ou B for escolhida). A campanha de calibração gh9 (~308h, 6 fases) usa a imagem congelada `phtcosta/rvandroid:0.8.0` e não pode ter mudanças na imagem entre fases.
**Decisão**: R5 é implementado APÓS gh9 Phase E (validação) completa. A Alternativa C (text-based, zero deps Docker) é preferida por não causar nenhum conflito. Se Alt A/B for eventualmente necessária, o rebuild Docker acontece como change separada, com re-calibração parcial (Phases D+E only).
**Fundamentação**: A calibração é o gargalo (~13 dias contínuos). Atrasar para incluir error detection não compensa — o error detection pode ser adicionado e re-calibrado incrementalmente depois. Se Alt C (text-based) provar ser suficiente, não há nenhuma interferência com gh9 e nenhum rebuild Docker.

### Decisão D8: Sessão 1 (R1-R4) só inicia após gh16 committed

**Contexto**: gh16-unify-toolconfig modifica 4 dos mesmos módulos que R2 e R3 tocam (rv-experiment/config.py, rv-android-core/domain/task.py, rv-experiment/__main__.py). O gh16 está 95% completo (apenas E2E tests pendentes).
**Decisão**: Aguardar gh16 ser commited antes de iniciar Sessão 1, para evitar conflitos de merge e garantir line numbers estáveis.
**Fundamentação**: R2 e R3 são mudanças pontuais (deletar linhas, limpar TODOs) — conflitos com gh16 seriam triviais mas desnecessários. P1: fazer as coisas na ordem certa é mais simples que resolver conflitos depois.

---

## 5. Plano de Execução

### Sessão 1: Quick Path — Refatorações Mecânicas (Items R1, R2, R3, R4)

**Track**: Quick Path (conforme `docs/WORKFLOW.md` Section 8)
**Pré-condição**: gh16-unify-toolconfig committed (Decisão D8)

#### Fase 1: Analyze

1. **Criar GitHub Issue** usando template "Refactoring" em `PAMunb/rvsec`:
   - Título: "Refactoring: magic numbers, duplicate methods, dead config code, TODO cleanup"
   - Domínios afetados: rv-agent, rv-experiment, rv-screen-parser, rv-android-core, rv-static-analysis
   - FRs/NFRs: Não afeta comportamento (refatoração interna)
   - Mover card no Kanban para "In Progress"

2. **Criar change dir** (via `openspec new change "gh<N>-refactoring-cleanup" --schema quick-path`):
   ```
   openspec/changes/gh<N>-refactoring-cleanup/
   ├── .openspec.yaml   # schema: quick-path
   ├── plan.md          # Context, scope, file inventory, acceptance criteria
   └── tasks.md         # Execution checklist extracted from plan
   ```

3. **Criar plan.md** seguindo o template do schema `quick-path` (`openspec/schemas/quick-path/templates/plan.md`). O conteúdo deve ser **autocontido** (não referências ao doc de ideação):

   **Header** (conforme template):
   - Change Name, Date, Track (Quick Path), Priority, GitHub Issue (#N), PRD Reference, Domains

   **Seções** (conforme template):
   - **Context**: Por que esta refatoração (magic numbers, método duplicado, TODOs obsoletos, código morto em configs)
   - **Scope**: Items R1-R4 organizados por módulo/grupo
   - **File Inventory**: Tabela com caminhos exatos, ação (Edit/Delete), e detalhes — atualizar line numbers pós-gh16
   - **Execution Order**: Grupos por independência para subagent dispatch (R1=rv-agent, R2+R3.3=rv-experiment, R3.1=rv-screen-parser, R3.4=rv-agent config, R3.2=GitHub Issues)
   - **Acceptance Criteria**: Checkboxes verificáveis (greps, test counts)

4. **Criar tasks.md** extraindo tarefas do plan.md. Checkboxes agrupadas por dependência, com grupo final de verificação.

   **Após criar os artefatos**: Este documento (`docs/20260215_plano_refatoracao.md`) é movido para `backup/` — os artefatos da change passam a ser a fonte da verdade.

#### Fase 2: Execute

Trabalhar os tasks de `tasks.md` usando `/opsx:apply`. Para cada grupo, usar skill apropriado:
- `/rv-refactor-constants` para R1 (magic numbers → constantes)
- `/rv-cleanup` para R2 e R3.4 (código morto)
- Edição direta para R3.1 e R3.3 (TODOs simples)
- Criar Issues via MCP GitHub para R3.2

| Passo | Item | Ação | Skill |
|-------|------|------|-------|
| 1 | R2 | Deletar método duplicado `get_rv_instrumentation_config()` (linha 731) | `/rv-cleanup` ou edição direta |
| 2 | R3.4 | Deletar `verbose_counters` + `get_verbose_counters()` + `enable_coordinate_enhancement` + check em `validate()` | `/rv-cleanup` |
| 3 | R1 | Adicionar constantes + substituir 8 magic numbers por `device_to_optimized()` + 3 locais de `1794` | `/rv-refactor-constants` |
| 4 | R3.1 | Deletar 3 TODOs obsoletos (vazios/resolvidos) | Edição direta |
| 5 | R3.3 | Investigar e resolver ~10 TODOs inline | Edição direta |
| 6 | R3.2 | Criar ~7 GitHub Issues para TODOs legítimos | MCP `issue_write` |
| 7 | R4 | Avaliar BaseDetector — provavelmente skip per P1 | Decisão inline |

Commits intermediários com `refs #N`. Subagent dispatch se task groups forem independentes (R1 toca rv-agent, R2 toca rv-experiment — paralelizável).

#### Fase 3: Verify

1. Rodar testes dos módulos afetados:
   ```bash
   uv run pytest modules/rv-agent/tests/unit/ -v
   uv run pytest modules/rv-experiment/tests/ -v
   uv run pytest modules/rv-screen-parser/tests/ -v
   ```
2. Verificar acceptance criteria:
   - `grep -rn "704 / 1080\|1248 / 1920\|* 704\|* 1248" modules/rv-agent/src/` → 0 hits (exceto constants.py/coordinate_utils.py)
   - `grep -n "def get_rv_instrumentation_config" modules/rv-experiment/src/rv_experiment/config.py` → exatamente 1 resultado
   - `grep -rn "TODO\|FIXME" modules/*/src/ --include="*.py" | wc -l` → reduz de 25 para ≤5
3. `/rv-verify` nos módulos afetados (tests + lint)
4. Commit final com `closes #N`
5. `/opsx:archive gh<N>-refactoring-cleanup` (Quick Path — no delta specs, archive only)
6. Mover card no Kanban para "Done"

### Sessão 2 (futura): FF SDD — Error Detection no rv-agent (Item R5)

**Track**: Fast-Forward SDD (conforme `docs/WORKFLOW.md` Section 7)
**Pré-condição**: Sessão 1 completa + gh9-docker-calibration completo (Decisão D7)

#### Fase 1: Explore

1. **Criar GitHub Issue** usando template "Enhancement" em `PAMunb/rvsec`:
   - Título: "Integrate error detection from rv-screen-parser into rv-agent"
   - Domínio: rv-agent (consumidor), rv-screen-parser (provider, sem mudanças)
   - FRs: FR21 (RVAgent exploration), FR23 (error detection)
   - Mover card no Kanban para "In Progress"

2. **Análise do ErrorDetector e pontos de integração**:
   ```
   /opsx:explore
   ```
   Focar em: parse_node vs learn_node como ponto de integração, viabilidade da Alt C (text-based), impacto em FailedActionScorer e StuckRecovery.

#### Fase 2: Fast-Forward

3. **Gerar todos os artifacts de uma vez** (usa schema `rv-sdd`, o default):
   ```
   /opsx:ff gh<N>-error-detection
   ```
   Produz (conforme schema `rv-sdd` em `openspec/schemas/rv-sdd/`):
   - `proposal.md` — Why/What/Impact (motivação, mudanças, capabilities, impacto)
   - Delta specs em `specs/agent/` — invariantes (INV-XX-NN) e cenários (WHEN/THEN/AND) para error detection
   - `design.md` — Decisões de implementação, arquitetura da integração, mapping spec→implementation→test
   - `tasks.md` — Tarefas com checkboxes agrupadas por fase

   O conteúdo do Item R5 deste doc (seções 5.1-5.5: análise do rvsmart, comparação, alternativas, deps) alimenta o `/opsx:ff` como contexto. Após criação dos artifacts, a fonte da verdade são os arquivos da change.

   **Decisão chave no design doc**: Avaliar as 4 alternativas (ver Item R5, seção 5.4):
   - **Alt. C (text-based, sem deps novas)**: Primeira opção a avaliar per D6. Regex nos textos do UIAutomator dump.
   - **Alt. B (color-based, OpenCV only)**: Se Alt. C insuficiente. Requer opencv no Docker.
   - **Alt. A (completo, OCR + CV)**: Máxima detecção. Requer tesseract + opencv no Docker.
   - **Alt. D (condicional)**: Complemento a qualquer alternativa. Só analisa quando hash não mudou.

#### Fase 3: Implement

4. **Executar tasks**:
   ```
   /opsx:apply
   ```
   Usar `/rv-tdd` para cada task (test-first). Commits intermediários com `refs #N`.

   **Nota**: R5 conecta com TODOs existentes — `record_action_failure()` não chamada (screen_node.py:120), `FailedActionScorer` sempre vazio, `success=True` hardcoded (memory_coordinator.py:219). A implementação resolveria esses TODOs como efeito colateral.

#### Fase 4: Close

5. **Verificar, sync specs, arquivar**:
   ```
   /rv-verify rv-agent
   /opsx:verify gh<N>-error-detection
   /opsx:archive gh<N>-error-detection
   ```
   Commit final com `closes #N`. Mover card no Kanban para "Done".

**Se alternativa A ou B for escolhida — impacto Docker**:
1. Adicionar `apt-get install tesseract-ocr libtesseract-dev` (Alt. A) ou apenas `libopencv-dev` (Alt. B) no `docker/base/Dockerfile` ou `docker/tools/Dockerfile`
2. Rebuild da chain completa: base → android → tools → rvandroid
3. Testar imagens com experimento simples (monkey + rvagent:pure_algorithm)
4. Atualizar tags das imagens no Docker Hub (`phtcosta/rvsec_base`, `phtcosta/rvsec_android`, `phtcosta/rvandroid_tools`)
5. Atualizar `FROM` nos Dockerfiles downstream para usar novas tags
6. Se gh9 já executou fases B-C com imagem antiga: re-calibrar Phases D+E com nova imagem

**Referência do pipeline antigo**: Analisado em `backup/rvsmart-tool/src/rvsmart_tool/` — ver seções 5.1-5.2 do Item R5 para detalhes do pipeline de 6 etapas do rvsmart e comparação com rv-agent.

---

## 6. Análise de Impacto de Changes Ativas

### 6.1. gh9-docker-calibration (Campanha de Calibração ~308h)

**Change**: `openspec/changes/gh9-docker-calibration/`
**Status**: Infraestrutura completa (Tasks 1-12), campanha de execução (Tasks 15-27) pendente

**Impacto do R5 sobre gh9**:

A campanha inteira (6 fases, ~308h) roda sobre a imagem Docker congelada `phtcosta/rvandroid:0.8.0`. O impacto depende da alternativa escolhida para R5:

| Alternativa R5 | Impacto em gh9 | Docker Image | Campanha de Calibração |
|----------------|-----------------|--------------|------------------------|
| **Alt C (text-based)** | **ZERO** | Sem mudança na imagem | Sem interferência |
| **Alt D (conditional)** | **ZERO** | Sem mudança na imagem | Sem interferência |
| **Alt B (color-only)** | **ALTO** | Rebuild obrigatório | Pode invalidar resultados entre fases |
| **Alt A (full ScreenshotAnalyzer)** | **ALTO** | Rebuild obrigatório | Pode invalidar resultados entre fases |

**Risco principal**: Se Alt A/B for escolhida e implementada DURANTE gh9, os resultados das fases B-C (baseline + macro) seriam com imagem diferente das fases D-E, invalidando a comparação estatística.

**Decisão D7**: R5 é implementado APÓS gh9 completo. Ver Seção 4.

### 6.2. gh16-unify-toolconfig (Unificação de ToolConfig)

**Change**: `openspec/changes/gh16-unify-toolconfig/`
**Status**: Implementação core completa (Tasks 1-5, 7), E2E tests pendentes (Task 6)

**O que gh16 faz**: Unifica dois `ToolConfig` separados (rv-android-core e rv-platform) em uma única classe em rv-android-core. Campos renomeados (`tool_name`→`name`, `variants`→`variant`, `additional_params`→`parameters`). Expansão de variants movida do Platform para o CLI parser. Auto-save de `experiment_config.json` adicionado.

**Impacto nos itens do plano**:

| Item | Arquivo Afetado | Impacto | Ajuste Necessário |
|------|-----------------|---------|-------------------|
| R1 | rv-agent (não tocado) | **Nenhum** | — |
| R2 | `rv-experiment/config.py` | **Linhas deslocaram** | Duplicata agora em 498/731 (era 500/733). Ainda existe, confirmar antes de deletar |
| R3 (task.py TODOs) | `rv-android-core/domain/task.py` | **Linhas deslocaram** | `skip_installation` agora linha 174 (era 207), `export_to_csv` linha 176 (era 209). Ainda existem |
| R3 (__main__.py TODO) | `rv-experiment/__main__.py` | **Linha deslocou** | Template TODO agora linha 867 (era 864). Ainda existe |
| R4 | rv-screen-parser (não tocado) | **Nenhum** | — |
| R5 | rv-agent (não tocado) | **Nenhum** | — |

**Efeitos colaterais positivos do gh16**:
- Deletou dead code `if tool_name == "rvandroid"` em ToolFactory (P3) — menos cleanup para R3
- ToolConfig agora usa `@validated_model` + `BaseValidatedModel` — parcialmente endereça sugestão Gemini 3.1

**Nota sobre gh9**: O gh16 muda o formato serializado de ToolConfig em `tasks.json` e `experiment_config.json`. A imagem `phtcosta/rvandroid:0.8.0` tem código antigo, mas gh9 faz `uv sync` dentro dos containers a partir do branch `modules` — portanto gh16 será incorporado automaticamente. Os scripts de calibração devem ser compatíveis com o novo formato (verificar `baseline_docker.py` e `calibration_orchestrator.py`).

**Pré-condição para Sessão 1**: gh16 deve estar commited/merged ANTES de iniciar R1-R4, para que as line numbers e estrutura de código estejam estáveis.

---

## 7. Fora de Escopo

Os seguintes temas foram identificados mas NÃO fazem parte deste plano:

- **Parallel task execution** — requer arquitetura multi-emulador (escopo de pesquisa separado)
- **Dynamic Android JAR selection** (rv-instrumentation TODOs) — enhancement separado, criar Issue
- **Performance monitoring** — tracking manual de tempo é suficiente para pesquisa (P1)
- **DeviceState canônico** (sugestão Gemini) — StateConverter é adapter pragmático que funciona
- **Task como BaseValidatedModel** (sugestão Gemini) — Task funciona como está, mudança sem benefício claro. Nota: ToolConfig JÁ foi migrado para BaseValidatedModel pelo gh16-unify-toolconfig

---

## 8. Referências

| Documento | Propósito |
|-----------|-----------|
| `docs/analise_gemini.md` | Análise original do Gemini |
| `docs/analise_qwen.md` | Análise original do Qwen |
| `docs/WORKFLOW.md` | Workflow SDD (tracks, fases, skills) |
| `CLAUDE.md` | Princípios P1-P4, arquitetura, convenções |
| `openspec/schemas/quick-path/` | Schema Quick Path (plan.md → tasks.md) — usado pela Sessão 1 |
| `openspec/schemas/rv-sdd/` | Schema rv-sdd (proposal → specs → design → tasks) — usado pela Sessão 2 |
| `openspec/config.yaml` | Config OpenSpec (default schema: rv-sdd) |
| `modules/rv-agent/src/rv_agent/constants.py` | Constantes existentes do rv-agent |
| `modules/rv-agent/src/rv_agent/services/coordinate_utils.py` | Utilitário de conversão de coordenadas existente |
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/detectors/error_detector.py` | ErrorDetector (790 linhas, 3 estratégias) |
| `modules/rv-screen-parser/src/rv_screen_parser/screenshot/screenshot_analyzer.py` | ScreenshotAnalyzer (orquestrador dos detectors) |
| `modules/rv-agent/src/rv_agent/domain/screen_node.py` | ScreenNode com `record_action_failure()` (nunca chamada) |
| `modules/rv-agent/src/rv_agent/agent/nodes/learn_node.py` | Stuck detection (hash-based, não error-aware) |
| `modules/rv-agent/src/rv_agent/agent/nodes/parse_node.py` | Parse UI (UIAutomator only, sem screenshot analysis) |
| `modules/rv-agent/src/rv_agent/agent/nodes/execute_node.py` | Execução de ações + UI coverage recording |
| `modules/rv-agent/src/rv_agent/services/screen_analyzer.py` | ScreenProcessor (parse + format, sem error detection) |
| `backup/rvsmart-tool/src/rvsmart_tool/llm/service/action_service.py` | Pipeline antigo do rvsmart (referência histórica) |
| `backup/rvsmart-tool/src/rvsmart_tool/analysis/screenshot/screenshot_action_complementor.py` | Integração ErrorDetector↔UI no rvsmart (referência) |
| `backup/rvsmart-tool/src/rvsmart_tool/llm/service/state_enricher.py` | Enriquecimento de estado com erros no rvsmart |
| `docker/base/Dockerfile` | Imagem base — NÃO tem tesseract/opencv |
| `docker/tools/Dockerfile` | Imagem tools — NÃO tem tesseract/opencv |
| `docker/rvandroid/Dockerfile` | Imagem final — NÃO tem tesseract/opencv |
| `openspec/changes/gh9-docker-calibration/proposal.md` | Proposta calibração Docker (~308h, imagem congelada 0.8.0) |
| `openspec/changes/gh9-docker-calibration/design.md` | Runbook de execução — 6 fases (A-E) + aplicação de parâmetros |
| `openspec/changes/gh16-unify-toolconfig/` | Unificação de ToolConfig — modifica config.py, task.py, __main__.py |
