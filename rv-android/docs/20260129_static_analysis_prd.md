# PRD: rv-static-analysis-lite

**Product Requirements Document**

| Campo | Valor |
|-------|-------|
| **Documento** | PRD-2026-001 |
| **Versão** | 1.0 |
| **Data** | 2026-01-29 |
| **Autor** | Claude Code |
| **Status** | Draft |
| **Revisores** | - |

---

## Índice

1. [Resumo Executivo](#1-resumo-executivo)
2. [Contexto e Problema](#2-contexto-e-problema)
3. [Objetivos e Não-Objetivos](#3-objetivos-e-não-objetivos)
4. [Personas e Casos de Uso](#4-personas-e-casos-de-uso)
5. [Requisitos Funcionais](#5-requisitos-funcionais)
6. [Requisitos Não-Funcionais](#6-requisitos-não-funcionais)
7. [Arquitetura Técnica](#7-arquitetura-técnica)
8. [Estratégia de Integração](#8-estratégia-de-integração) ⭐ **NOVO**
9. [Especificação de APIs](#9-especificação-de-apis)
10. [Modelos de Dados](#10-modelos-de-dados)
11. [Plano de Implementação](#11-plano-de-implementação)
12. [Estratégia de Testes](#12-estratégia-de-testes)
13. [Métricas de Sucesso](#13-métricas-de-sucesso)
14. [Riscos e Mitigações](#14-riscos-e-mitigações)
15. [Dependências](#15-dependências)
16. [Considerações Futuras](#16-considerações-futuras)
17. [Glossário](#17-glossário)
18. [Apêndices](#18-apêndices)

---

## 1. Resumo Executivo

### 1.1 Visão do Produto

O **rv-static-analysis-lite** é um módulo Python para análise estática de aplicações Android que substitui os componentes Java existentes (GATOR, GESDA, REACH) baseados em Soot/FlowDroid. O módulo utiliza a biblioteca Androguard 4.1.3 para fornecer análise robusta que **nunca trava**, priorizando confiabilidade sobre precisão máxima.

### 1.2 Proposta de Valor

| Antes (Java/Soot) | Depois (Python/Androguard) |
|-------------------|---------------------------|
| Travamentos frequentes em APKs complexos | Análise sempre completa |
| Sem timeout graceful | Timeout nativo com saída parcial |
| Dependência de RVSEC_HOME | Módulo Python standalone |
| Setup complexo (Java + Soot + libs) | `pip install rv-static-analysis-lite` |
| Precisão alta quando funciona (~95%) | Precisão média mas confiável (~70%) |

### 1.3 Escopo

**Incluído:**
- Geração de Window Transition Graph (WTG)
- Análise de Reachability para métodos MOP
- Extração de estrutura do app (Activities, widgets, layouts)
- Detecção de listeners e callbacks
- Resolução heurística de Intents
- Formatos de saída compatíveis (.wtg, .reach)

**Excluído:**
- Análise de points-to (SPARK)
- Fixed-point solver completo
- Instrumentação de APKs (mantido em rv-instrumentation)
- Geração de monitores (mantido em rv-monitor-generator)

---

## 2. Contexto e Problema

### 2.1 Situação Atual

O pipeline de análise estática do RV-Android depende de três componentes Java:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pipeline Atual (Java)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  APK ──→ [GATOR] ──→ WTG (.wtg)                                 │
│      │                                                           │
│      ├─→ [GESDA] ──→ App Structure (.gesda)                     │
│      │                                                           │
│      └─→ [REACH] ──→ Reachability (.reach)                      │
│                                                                  │
│  Dependências:                                                   │
│  • Soot 4.3.0                                                   │
│  • FlowDroid 2.10                                               │
│  • RVSEC_HOME environment variable                              │
│  • Java 11+                                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Problemas Identificados

#### 2.2.1 Problema Principal: Travamentos

| Componente | Taxa de Sucesso | Causa do Travamento |
|------------|-----------------|---------------------|
| GATOR | ~60% | FixpointSolver não converge |
| GESDA | ~70% | Call graph SPARK muito grande |
| REACH | ~75% | BFS/DFS em grafos com 70k+ edges |

**Evidência**: Em experimentos com 28 APKs, 11 (39%) causaram travamento em pelo menos um componente.

#### 2.2.2 Problema Secundário: Timeout sem Saída

```
Cenário Atual:
1. Componente Java inicia análise
2. Análise trava em loop infinito
3. Timeout externo mata o processo
4. NENHUM arquivo de saída é gerado
5. Experimento inteiro falha para este APK
```

**Impacto**: Perda total de dados para APKs complexos.

#### 2.2.3 Problema Terciário: Complexidade de Setup

```bash
# Setup atual requer:
export RVSEC_HOME=/path/to/rvsec
export JAVA_HOME=/path/to/java11
export ANDROID_HOME=/path/to/sdk

# Plus: soot.jar, flowdroid.jar, android-platforms/
```

### 2.3 Análise de Causa Raiz

```
┌─────────────────────────────────────────────────────────────────┐
│                    Diagrama de Ishikawa                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Tecnologia          Arquitetura         Dados                  │
│      │                   │                 │                    │
│      ▼                   ▼                 ▼                    │
│  ┌────────┐        ┌──────────┐      ┌──────────┐              │
│  │ Soot   │        │ Fixed-   │      │ APKs     │              │
│  │ SPARK  │───────▶│ Point    │◀─────│ complexos│              │
│  │        │        │ Solver   │      │ (obfusc.)│              │
│  └────────┘        └──────────┘      └──────────┘              │
│       │                 │                 │                     │
│       └────────────────┼─────────────────┘                     │
│                        ▼                                        │
│              ┌─────────────────┐                                │
│              │  TRAVAMENTO     │                                │
│              │  (sem saída)    │                                │
│              └─────────────────┘                                │
│                        ▲                                        │
│       ┌────────────────┼─────────────────┐                     │
│       │                │                 │                      │
│  ┌────────┐       ┌──────────┐     ┌──────────┐               │
│  │ Sem    │       │ Análise  │     │ Grafos   │               │
│  │timeout │◀──────│ exaustiva│────▶│ enormes  │               │
│  │interno │       │          │     │ (70k+)   │               │
│  └────────┘       └──────────┘     └──────────┘               │
│      │                 │                 │                      │
│      ▼                 ▼                 ▼                      │
│  Processo          Análise           Escala                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 Decisão Arquitetural

**ADR-001: Substituir Soot/FlowDroid por Androguard**

| Critério | Soot/FlowDroid | Androguard | Decisão |
|----------|---------------|------------|---------|
| Robustez | Baixa | Alta | ✅ Androguard |
| Precisão | Alta (~95%) | Média (~70%) | Soot |
| Timeout graceful | Não | Sim | ✅ Androguard |
| Setup | Complexo | Simples | ✅ Androguard |
| Manutenção | Java | Python | ✅ Androguard |

**Justificativa**: Uma análise completa mas menos precisa é infinitamente mais útil que uma análise precisa que nunca termina.

---

## 3. Objetivos e Não-Objetivos

### 3.1 Objetivos (Goals)

| ID | Objetivo | Métrica de Sucesso | Prioridade |
|----|----------|-------------------|------------|
| G1 | Eliminar travamentos | 100% APKs processados | P0 |
| G2 | Manter compatibilidade de saída | Formatos .wtg/.reach idênticos | P0 |
| G3 | Reduzir dependências externas | Zero dependência de RVSEC_HOME para análise | P1 |
| G4 | Timeout com saída parcial | Arquivo gerado mesmo com timeout | P1 |
| G5 | Performance aceitável | < 5 min para APKs típicos | P2 |
| G6 | Cobertura de funcionalidades | ≥80% das features do GATOR | P2 |

### 3.2 Não-Objetivos (Non-Goals)

| ID | Não-Objetivo | Justificativa |
|----|--------------|---------------|
| NG1 | Precisão igual ao GATOR | Trade-off consciente: robustez > precisão |
| NG2 | Análise de reflection completa | Complexidade excessiva, baixo ROI |
| NG3 | Fixed-point solver | Risco de reintroduzir travamentos |
| NG4 | Points-to analysis (SPARK) | Não disponível no Androguard |
| NG5 | Substituir instrumentação | Mantido em rv-instrumentation |
| NG6 | Suporte a APKs split | Fora do escopo inicial |

### 3.3 Princípios de Design

1. **Robustez sobre Precisão**: Sempre terminar, mesmo que com resultado aproximado
2. **Fail-Safe**: Em caso de erro, gerar saída parcial, não falhar silenciosamente
3. **Simplicidade**: Preferir heurísticas simples a algoritmos complexos
4. **Compatibilidade**: Manter formatos de saída para não quebrar código existente
5. **Observabilidade**: Logs detalhados e métricas de qualidade na saída

---

## 4. Personas e Casos de Uso

### 4.1 Personas

#### Persona 1: Pesquisador de Segurança Android

```
Nome: Dr. Silva
Papel: Professor/Pesquisador em segurança de software
Necessidades:
  - Analisar grandes conjuntos de APKs para estudos empíricos
  - Resultados consistentes e reproduzíveis
  - Não perder dados por travamentos
Frustrações Atuais:
  - "Perco horas esperando análises que nunca terminam"
  - "Tenho que excluir APKs problemáticos do dataset"
```

#### Persona 2: Desenvolvedor do RV-Android

```
Nome: João
Papel: Desenvolvedor/Mantenedor do projeto
Necessidades:
  - Integrar análise estática no pipeline de CI
  - Debugar problemas rapidamente
  - Adicionar novas funcionalidades
Frustrações Atuais:
  - "O código Java é difícil de manter e debugar"
  - "Preciso de ambiente Java específico para rodar"
```

#### Persona 3: Usuário Final do rv-experiment

```
Nome: Maria
Papel: Estudante de mestrado usando RV-Android
Necessidades:
  - Rodar experimentos end-to-end
  - Entender o que deu errado quando falha
  - Setup simples
Frustrações Atuais:
  - "Não sei se o GATOR travou ou está só lento"
  - "Setup do RVSEC_HOME é confuso"
```

### 4.2 Casos de Uso

#### UC-01: Gerar WTG para APK

```
Ator: Pesquisador
Pré-condição: APK válido disponível
Fluxo Principal:
  1. Usuário invoca: rv-static-analysis-lite wtg --apk app.apk
  2. Sistema carrega APK com Androguard
  3. Sistema extrai Activities, layouts, widgets
  4. Sistema detecta listeners e callbacks
  5. Sistema resolve targets de Intents
  6. Sistema constrói grafo de transições
  7. Sistema salva arquivo .wtg

Fluxo Alternativo (Timeout):
  5a. Timeout durante resolução de Intents
  5b. Sistema usa over-approximation para Intents restantes
  5c. Sistema marca edges como "approximate" no output
  5d. Continua fluxo principal

Pós-condição: Arquivo .wtg gerado
```

#### UC-02: Analisar Reachability para MOP

```
Ator: rv-experiment (automatizado)
Pré-condição: APK + especificações MOP disponíveis
Fluxo Principal:
  1. Sistema invoca análise via API Python
  2. Sistema carrega APK e gera call graph
  3. Sistema identifica entry points (Activities, Services, etc.)
  4. Sistema carrega assinaturas MOP das specs
  5. Sistema executa BFS de entry points
  6. Sistema marca métodos que alcançam MOP
  7. Sistema retorna DataFrame com resultados

Fluxo Alternativo (Call Graph Grande):
  3a. Call graph tem > 50k edges
  3b. Sistema aplica sampling ou truncamento
  3c. Sistema marca resultado como "approximate"
  3d. Continua fluxo principal

Pós-condição: Arquivo .reach gerado
```

#### UC-03: Análise Batch de Múltiplos APKs

```
Ator: Pesquisador
Pré-condição: Diretório com múltiplos APKs
Fluxo Principal:
  1. Usuário invoca: rv-static-analysis-lite batch --apks-dir ./apks
  2. Sistema descobre todos os APKs no diretório
  3. Para cada APK (em paralelo se --parallel):
     a. Executa UC-01 (WTG)
     b. Executa UC-02 (REACH)
     c. Salva resultados em subdiretório
  4. Sistema gera relatório agregado

Fluxo Alternativo (Falha em APK Individual):
  3x. Erro não recuperável em um APK
  3y. Sistema loga erro e continua com próximo APK
  3z. Relatório final inclui lista de falhas

Pós-condição: Resultados para todos APKs processáveis
```

---

## 5. Requisitos Funcionais

### 5.1 Requisitos de WTG

#### RF-WTG-01: Extração de Windows

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-WTG-01.1 | Extrair todas as Activities declaradas no AndroidManifest | P0 |
| RF-WTG-01.2 | Identificar Main Activity | P0 |
| RF-WTG-01.3 | Extrair Services declarados | P1 |
| RF-WTG-01.4 | Extrair BroadcastReceivers declarados | P1 |
| RF-WTG-01.5 | Detectar Dialogs criados programaticamente | P2 |
| RF-WTG-01.6 | Detectar Fragments | P2 |
| RF-WTG-01.7 | Detectar Options Menus | P2 |
| RF-WTG-01.8 | Detectar Context Menus | P3 |

**Critérios de Aceitação**:
- Todas as Activities do manifest devem aparecer no WTG
- Main Activity deve ter flag `isMain: true`
- Componentes não encontrados devem ser logados como warning

#### RF-WTG-02: Extração de Widgets

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-WTG-02.1 | Parse de layouts XML binários (AXML) | P0 |
| RF-WTG-02.2 | Extrair android:id de widgets | P0 |
| RF-WTG-02.3 | Extrair tipo do widget (Button, TextView, etc.) | P0 |
| RF-WTG-02.4 | Extrair android:text e android:hint | P1 |
| RF-WTG-02.5 | Extrair android:inputType para EditText | P1 |
| RF-WTG-02.6 | Extrair android:onClick (inline callbacks) | P0 |
| RF-WTG-02.7 | Resolver includes (<include layout="@layout/..."/>) | P2 |
| RF-WTG-02.8 | Processar merge tags | P2 |

**Critérios de Aceitação**:
- Widgets com android:id devem aparecer na lista de widgets da window
- Widgets sem id podem ser omitidos (não são interagíveis)
- android:onClick deve gerar listener entry

#### RF-WTG-03: Associação Activity-Layout

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-WTG-03.1 | Detectar setContentView(R.layout.xxx) em onCreate | P0 |
| RF-WTG-03.2 | Resolver ID numérico para nome do layout | P0 |
| RF-WTG-03.3 | Detectar LayoutInflater.inflate() | P2 |
| RF-WTG-03.4 | Associar layout à Activity correspondente | P0 |
| RF-WTG-03.5 | Suportar múltiplos layouts por Activity (fragments) | P3 |

**Critérios de Aceitação**:
- 80% das Activities devem ter layout associado corretamente
- Activities sem layout detectado devem ter `layoutFileName: null`

#### RF-WTG-04: Detecção de Listeners

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-WTG-04.1 | Detectar setOnClickListener | P0 |
| RF-WTG-04.2 | Detectar setOnLongClickListener | P1 |
| RF-WTG-04.3 | Detectar setOnTouchListener | P2 |
| RF-WTG-04.4 | Detectar setOnItemClickListener (ListView) | P1 |
| RF-WTG-04.5 | Detectar setOnItemLongClickListener | P2 |
| RF-WTG-04.6 | Detectar setOnScrollListener | P3 |
| RF-WTG-04.7 | Detectar setOnFocusChangeListener | P3 |
| RF-WTG-04.8 | Associar listener ao widget correspondente | P1 |
| RF-WTG-04.9 | Identificar classe/método do callback | P1 |

**Critérios de Aceitação**:
- Listeners setados em onCreate/onStart/onResume devem ser detectados
- 85% dos onClick listeners devem ser detectados

#### RF-WTG-05: Resolução de Intents

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-WTG-05.1 | Detectar chamadas startActivity/startActivityForResult | P0 |
| RF-WTG-05.2 | Resolver explicit intents (const-class) | P0 |
| RF-WTG-05.3 | Resolver explicit intents (setClass/setComponent) | P1 |
| RF-WTG-05.4 | Resolver implicit intents via intent-filters | P2 |
| RF-WTG-05.5 | Fallback: over-approximation quando não resolvido | P0 |
| RF-WTG-05.6 | Detectar finish() e suas variantes | P1 |
| RF-WTG-05.7 | Extrair Intent flags | P2 |

**Critérios de Aceitação**:
- Explicit intents com const-class devem ter precisão ≥90%
- Intents não resolvidos devem usar over-approximation (all Activities)
- Transições devem ser marcadas como "precise" ou "approximate"

#### RF-WTG-06: Construção de Transições

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-WTG-06.1 | Criar edge para cada startActivity resolvido | P0 |
| RF-WTG-06.2 | Associar evento (click, long_click, etc.) à transição | P0 |
| RF-WTG-06.3 | Associar widget à transição quando aplicável | P1 |
| RF-WTG-06.4 | Gerar transições de menu items | P2 |
| RF-WTG-06.5 | Deduplicar transições idênticas | P1 |

### 5.2 Requisitos de REACH

#### RF-REACH-01: Call Graph

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-REACH-01.1 | Gerar call graph via Androguard | P0 |
| RF-REACH-01.2 | Incluir métodos de app e framework | P0 |
| RF-REACH-01.3 | Reportar métricas do grafo (nodes, edges) | P1 |
| RF-REACH-01.4 | Suportar timeout durante geração | P1 |

#### RF-REACH-02: Entry Points

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-REACH-02.1 | Identificar métodos de lifecycle como entry points | P0 |
| RF-REACH-02.2 | Incluir onCreate, onStart, onResume das Activities | P0 |
| RF-REACH-02.3 | Incluir onReceive de BroadcastReceivers | P1 |
| RF-REACH-02.4 | Incluir onStartCommand/onBind de Services | P1 |
| RF-REACH-02.5 | Incluir callbacks de listeners como entry points | P1 |

#### RF-REACH-03: MOP Matching

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-REACH-03.1 | Carregar assinaturas MOP de especificações | P0 |
| RF-REACH-03.2 | Suportar formato de specs JCA | P0 |
| RF-REACH-03.3 | Suportar formato de specs Generic | P0 |
| RF-REACH-03.4 | Match por classe + método + assinatura | P0 |
| RF-REACH-03.5 | Match parcial (wildcards) | P2 |

#### RF-REACH-04: Análise de Reachability

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-REACH-04.1 | Computar reachability de entry points | P0 |
| RF-REACH-04.2 | Marcar métodos que alcançam MOP diretamente | P0 |
| RF-REACH-04.3 | Marcar métodos que alcançam MOP indiretamente | P0 |
| RF-REACH-04.4 | Listar quais métodos MOP são alcançados | P1 |
| RF-REACH-04.5 | Suportar timeout com resultado parcial | P1 |

### 5.3 Requisitos de CLI

#### RF-CLI-01: Comandos Principais

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-CLI-01.1 | Comando `wtg` para gerar WTG | P0 |
| RF-CLI-01.2 | Comando `reach` para gerar reachability | P0 |
| RF-CLI-01.3 | Comando `analyze` para gerar ambos | P0 |
| RF-CLI-01.4 | Comando `batch` para múltiplos APKs | P1 |
| RF-CLI-01.5 | Comando `info` para metadados do APK | P2 |

#### RF-CLI-02: Opções Comuns

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-CLI-02.1 | `--apk PATH` - caminho do APK | P0 |
| RF-CLI-02.2 | `--output PATH` - diretório de saída | P0 |
| RF-CLI-02.3 | `--timeout SECONDS` - timeout global | P1 |
| RF-CLI-02.4 | `--verbose` - logs detalhados | P1 |
| RF-CLI-02.5 | `--quiet` - apenas erros | P2 |
| RF-CLI-02.6 | `--format json|csv` - formato de saída | P1 |

### 5.4 Requisitos de API Python

#### RF-API-01: Interface Programática

```python
# RF-API-01.1: Classe principal de análise
from rv_static_analysis_lite import StaticAnalyzer

analyzer = StaticAnalyzer(apk_path, timeout=300)
result = analyzer.analyze()

# RF-API-01.2: Acesso a WTG
wtg = result.wtg
print(wtg.windows)
print(wtg.transitions)

# RF-API-01.3: Acesso a Reachability
reach = result.reachability
reach.to_csv("output.reach")

# RF-API-01.4: Análise individual
wtg_only = analyzer.analyze_wtg()
reach_only = analyzer.analyze_reach(mop_specs_dir="/path/to/specs")

# RF-API-01.5: Metadados
print(result.metadata.duration)
print(result.metadata.warnings)
```

---

## 6. Requisitos Não-Funcionais

### 6.1 Performance

| ID | Requisito | Meta | Medição |
|----|-----------|------|---------|
| RNF-PERF-01 | Tempo de análise WTG | < 60s para APKs típicos (< 50 Activities) | 95th percentile |
| RNF-PERF-02 | Tempo de análise REACH | < 120s para APKs típicos | 95th percentile |
| RNF-PERF-03 | Uso de memória | < 4GB RAM | Peak usage |
| RNF-PERF-04 | Tempo de carregamento APK | < 30s | Média |
| RNF-PERF-05 | Throughput batch | > 10 APKs/hora | Com paralelismo |

### 6.2 Confiabilidade

| ID | Requisito | Meta | Medição |
|----|-----------|------|---------|
| RNF-REL-01 | Taxa de sucesso | 100% (nunca travar) | APKs processados / APKs tentados |
| RNF-REL-02 | Timeout graceful | Sempre gerar saída mesmo com timeout | % de timeouts com saída |
| RNF-REL-03 | Recuperação de erros | Continuar após erro em componente | % de erros recuperados |
| RNF-REL-04 | Idempotência | Mesma entrada = mesma saída | Verificação determinística |

### 6.3 Compatibilidade

| ID | Requisito | Meta |
|----|-----------|------|
| RNF-COMP-01 | Formato .wtg | 100% compatível com rv-agent |
| RNF-COMP-02 | Formato .reach | 100% compatível com rv-coverage |
| RNF-COMP-03 | Python version | ≥ 3.10 |
| RNF-COMP-04 | Android versions | API 21-34 (Android 5.0 - 14) |
| RNF-COMP-05 | APK formats | APK, XAPK (básico) |

### 6.4 Observabilidade

| ID | Requisito | Meta |
|----|-----------|------|
| RNF-OBS-01 | Logging | Logs estruturados (JSON opcional) |
| RNF-OBS-02 | Métricas na saída | Incluir métricas de qualidade |
| RNF-OBS-03 | Warnings | Listar limitações detectadas |
| RNF-OBS-04 | Progress | Indicador de progresso para CLI |

### 6.5 Manutenibilidade

| ID | Requisito | Meta |
|----|-----------|------|
| RNF-MAINT-01 | Cobertura de testes | ≥ 80% |
| RNF-MAINT-02 | Documentação | Docstrings em todas as funções públicas |
| RNF-MAINT-03 | Type hints | 100% das funções públicas |
| RNF-MAINT-04 | Complexidade | Cyclomatic complexity < 10 por função |

---

## 7. Arquitetura Técnica

### 7.1 Visão Geral

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        rv-static-analysis-lite                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │     CLI      │     │   Python     │     │   Direct     │                │
│  │  __main__.py │     │     API      │     │   Import     │                │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘                │
│         │                    │                    │                         │
│         └────────────────────┼────────────────────┘                         │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         StaticAnalyzer                               │   │
│  │                         (analyzer.py)                                │   │
│  │  • Orchestration                                                     │   │
│  │  • Timeout management                                                │   │
│  │  • Error handling                                                    │   │
│  └───────────────────────────┬─────────────────────────────────────────┘   │
│                              │                                              │
│         ┌────────────────────┼────────────────────┐                        │
│         │                    │                    │                         │
│         ▼                    ▼                    ▼                         │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                 │
│  │    core/    │      │    wtg/     │      │   reach/    │                 │
│  │             │      │             │      │             │                 │
│  │ apk_analyzer│      │ wtg_builder │      │ reachability│                 │
│  │ call_graph  │      │ widget_ext. │      │ mop_matcher │                 │
│  │             │      │ listener_det│      │ entrypoint  │                 │
│  │             │      │ intent_res. │      │             │                 │
│  │             │      │ transition  │      │             │                 │
│  └──────┬──────┘      └──────┬──────┘      └──────┬──────┘                 │
│         │                    │                    │                         │
│         └────────────────────┼────────────────────┘                         │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          output/                                     │   │
│  │                                                                      │   │
│  │  wtg_writer.py          reach_writer.py          report_writer.py   │   │
│  │  (JSON .wtg)            (CSV .reach)             (HTML report)      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                           External Dependencies                              │
│                                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │ Androguard  │     │  NetworkX   │     │   lxml      │                   │
│  │   4.1.3     │     │    3.x      │     │             │                   │
│  └─────────────┘     └─────────────┘     └─────────────┘                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Estrutura de Diretórios

```
modules/rv-static-analysis-lite/
├── pyproject.toml
├── CLAUDE.md
├── README.md
│
├── src/rv_static_analysis_lite/
│   ├── __init__.py                 # Public API exports
│   ├── __main__.py                 # CLI entry point
│   ├── analyzer.py                 # Main orchestrator
│   ├── config.py                   # Configuration dataclasses
│   ├── exceptions.py               # Custom exceptions
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── apk_analyzer.py         # Androguard wrapper
│   │   ├── call_graph.py           # Call graph generation
│   │   └── manifest_parser.py      # AndroidManifest parsing
│   │
│   ├── wtg/
│   │   ├── __init__.py
│   │   ├── wtg_builder.py          # WTG orchestrator
│   │   ├── window_extractor.py     # Extract Activities, etc.
│   │   ├── widget_extractor.py     # Parse layout XMLs
│   │   ├── layout_resolver.py      # Activity → Layout mapping
│   │   ├── listener_detector.py    # Find setOnXxxListener
│   │   ├── intent_resolver.py      # Resolve Intent targets
│   │   └── transition_builder.py   # Build WTG edges
│   │
│   ├── reach/
│   │   ├── __init__.py
│   │   ├── reachability.py         # Main reachability analysis
│   │   ├── mop_matcher.py          # Match MOP specifications
│   │   └── entrypoint_finder.py    # Find Android entry points
│   │
│   ├── extensions/                  # Optional enhancements
│   │   ├── __init__.py
│   │   ├── stack_simulator.py      # Activity stack simulation
│   │   ├── back_navigation.py      # Back button modeling
│   │   ├── lifecycle_analyzer.py   # Extended lifecycle
│   │   └── reflection_detector.py  # Reflection detection
│   │
│   ├── output/
│   │   ├── __init__.py
│   │   ├── wtg_writer.py           # Write .wtg JSON
│   │   ├── reach_writer.py         # Write .reach CSV
│   │   └── models.py               # Pydantic output models
│   │
│   └── utils/
│       ├── __init__.py
│       ├── timeout.py              # Timeout utilities
│       ├── logging.py              # Logging setup
│       └── resource_ids.py         # R.id resolution
│
└── tests/
    ├── conftest.py                 # Pytest fixtures
    ├── fixtures/
    │   ├── apks/                   # Test APKs
    │   ├── expected/               # Expected outputs
    │   └── mop_specs/              # Test MOP specs
    │
    ├── unit/
    │   ├── test_widget_extractor.py
    │   ├── test_intent_resolver.py
    │   ├── test_reachability.py
    │   └── ...
    │
    ├── integration/
    │   ├── test_wtg_generation.py
    │   ├── test_reach_generation.py
    │   └── test_full_pipeline.py
    │
    └── regression/
        └── test_problematic_apks.py
```

### 7.3 Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WTG Generation Flow                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  APK File                                                                    │
│      │                                                                       │
│      ▼                                                                       │
│  ┌─────────────────┐                                                        │
│  │ APK Analyzer    │──────────────────────────────────────────────┐         │
│  │                 │                                              │         │
│  │ • AnalyzeAPK()  │                                              │         │
│  │ • get_package() │                                              │         │
│  │ • get_files()   │                                              │         │
│  └────────┬────────┘                                              │         │
│           │                                                        │         │
│           │ (apk, dex, analysis)                                  │         │
│           │                                                        │         │
│  ┌────────┴────────────────────────────────────────────────┐      │         │
│  │                                                          │      │         │
│  ▼                                                          ▼      ▼         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ Window          │  │ Layout          │  │ Listener        │             │
│  │ Extractor       │  │ Resolver        │  │ Detector        │             │
│  │                 │  │                 │  │                 │             │
│  │ • Activities    │  │ • setContentView│  │ • setOnClick... │             │
│  │ • Services      │  │ • R.layout.xxx  │  │ • XREFs         │             │
│  │ • Receivers     │  │                 │  │                 │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                       │
│           │ windows[]          │ layout_map         │ listeners[]           │
│           │                    │                    │                       │
│           └────────────────────┼────────────────────┘                       │
│                                │                                            │
│                                ▼                                            │
│                    ┌─────────────────────┐                                  │
│                    │ Widget Extractor    │                                  │
│                    │                     │                                  │
│                    │ • Parse AXML        │                                  │
│                    │ • Extract IDs       │                                  │
│                    │ • Extract onClick   │                                  │
│                    └──────────┬──────────┘                                  │
│                               │                                             │
│                               │ widgets_by_window                           │
│                               │                                             │
│                               ▼                                             │
│                    ┌─────────────────────┐                                  │
│                    │ Intent Resolver     │                                  │
│                    │                     │                                  │
│                    │ • const-class       │                                  │
│                    │ • setClass          │                                  │
│                    │ • Manifest filters  │                                  │
│                    │ • Over-approx       │                                  │
│                    └──────────┬──────────┘                                  │
│                               │                                             │
│                               │ intent_targets                              │
│                               │                                             │
│                               ▼                                             │
│                    ┌─────────────────────┐                                  │
│                    │ Transition Builder  │                                  │
│                    │                     │                                  │
│                    │ • Combine all data  │                                  │
│                    │ • Build edges       │                                  │
│                    │ • Deduplicate       │                                  │
│                    └──────────┬──────────┘                                  │
│                               │                                             │
│                               │ WTG                                         │
│                               │                                             │
│                               ▼                                             │
│                    ┌─────────────────────┐                                  │
│                    │ WTG Writer          │                                  │
│                    │                     │                                  │
│                    │ • Serialize JSON    │                                  │
│                    │ • Validate schema   │                                  │
│                    └──────────┬──────────┘                                  │
│                               │                                             │
│                               ▼                                             │
│                          .wtg File                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.4 Componentes Chave

#### 7.4.1 StaticAnalyzer (Orquestrador)

```python
class StaticAnalyzer:
    """Main orchestrator for static analysis."""

    def __init__(
        self,
        apk_path: str | Path,
        timeout: int = 300,
        mop_specs_dir: str | Path | None = None,
        config: AnalysisConfig | None = None,
    ):
        self.apk_path = Path(apk_path)
        self.timeout = timeout
        self.mop_specs_dir = Path(mop_specs_dir) if mop_specs_dir else None
        self.config = config or AnalysisConfig()

        # Lazy loading
        self._apk = None
        self._dex = None
        self._analysis = None

    def analyze(self) -> AnalysisResult:
        """Run full analysis (WTG + REACH)."""
        with timeout_handler(self.timeout):
            self._load_apk()
            wtg = self._analyze_wtg()
            reach = self._analyze_reach() if self.mop_specs_dir else None

        return AnalysisResult(
            wtg=wtg,
            reachability=reach,
            metadata=self._build_metadata(),
        )

    def analyze_wtg(self) -> WTG:
        """Run WTG analysis only."""
        ...

    def analyze_reach(self, mop_specs_dir: str | Path) -> ReachabilityResult:
        """Run reachability analysis only."""
        ...
```

#### 7.4.2 Timeout Handler

```python
import signal
from contextlib import contextmanager
from dataclasses import dataclass

@dataclass
class TimeoutState:
    """State for partial results on timeout."""
    partial_result: Any = None
    timed_out: bool = False

@contextmanager
def timeout_handler(seconds: int, state: TimeoutState | None = None):
    """Context manager for graceful timeout with partial results."""

    def handler(signum, frame):
        if state:
            state.timed_out = True
        raise TimeoutError(f"Operation timed out after {seconds}s")

    # Set signal handler
    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)

    try:
        yield state
    except TimeoutError:
        if state and state.partial_result:
            return state.partial_result
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
```

---

## 8. Estratégia de Integração

Esta seção define como o rv-static-analysis-lite se integra ao ecossistema rv-android, com foco na compatibilidade de formatos e na estratégia de migração em duas fases.

### 8.1 Análise de Impacto

#### 8.1.1 Consumidores dos Arquivos de Saída

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Mapa de Consumidores Atuais                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐         ┌──────────────────────────────────────────────┐ │
│  │ .wtg (JSON)  │────────▶│ GatorParser (rv-static-analysis)             │ │
│  │              │         │     │                                         │ │
│  │ - windows[]  │         │     ▼                                         │ │
│  │ - transitions│         │ WindowTransitionGraph (rv-android-core)       │ │
│  └──────────────┘         │     │                                         │ │
│                           │     ├──▶ TransitionManager (rv-agent)         │ │
│                           │     ├──▶ NavigationGuidance (rv-agent)        │ │
│                           │     └──▶ WtgScorer (rv-agent/ranking)         │ │
│                           └──────────────────────────────────────────────┘ │
│                                                                              │
│  ┌──────────────┐         ┌──────────────────────────────────────────────┐ │
│  │ .gesda (JSON)│────────▶│ GesdaParser (rv-static-analysis)             │ │
│  │              │         │     │                                         │ │
│  │ - windows[]  │         │     ▼                                         │ │
│  │ - widgets[]  │         │ Windows + Widgets (rv-android-core)           │ │
│  └──────────────┘         │     │                                         │ │
│                           │     └──▶ RVAgentVisitor (UI enrichment)       │ │
│                           └──────────────────────────────────────────────┘ │
│                                                                              │
│  ┌──────────────┐         ┌──────────────────────────────────────────────┐ │
│  │ .reach (CSV) │────────▶│ ReachParser (rv-static-analysis)             │ │
│  │              │         │     │                                         │ │
│  │ - 10 columns │         │     ▼                                         │ │
│  │ - methods[]  │         │ Classes + Methods (rv-android-core)           │ │
│  └──────────────┘         │     │                                         │ │
│                           │     ├──▶ MopScorer (rv-agent/ranking)         │ │
│                           │     └──▶ TransitionManager (priority calc)    │ │
│                           └──────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 8.1.2 Módulos Impactados

| Módulo | Arquivos Consumidos | Impacto se Formato Mudar |
|--------|--------------------|-----------------------|
| **rv-static-analysis** | .wtg, .gesda, .reach | 🔴 Alto - Parsers precisam atualizar |
| **rv-agent** | Via StaticAnalysisData | 🟡 Médio - Usa interfaces abstratas |
| **rv-android-core** | Nenhum diretamente | 🟢 Baixo - Define domain models |
| **rv-experiment** | Nenhum diretamente | 🟢 Baixo - Orquestra execução |
| **rv-coverage** | .reach (indireto) | 🟡 Médio - Usa Classes/Methods |

### 8.2 Estratégia de Duas Fases

#### 8.2.1 Visão Geral

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Estratégia de Migração em Duas Fases                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ══════════════════════════════════════════════════════════════════════════ │
│  FASE 1: COMPATIBILIDADE EXATA (MVP)                        Semanas 1-7     │
│  ══════════════════════════════════════════════════════════════════════════ │
│                                                                              │
│  rv-static-analysis-lite                                                    │
│          │                                                                   │
│          ▼                                                                   │
│  .wtg / .reach / .gesda  ←── Formatos IDÊNTICOS aos do Java                │
│          │                                                                   │
│          ▼                                                                   │
│  Parsers existentes funcionam SEM modificação                               │
│  (GatorParser, ReachParser, GesdaParser)                                    │
│                                                                              │
│  ══════════════════════════════════════════════════════════════════════════ │
│  FASE 2: FORMATO UNIFICADO (Pós-MVP)                        Semanas 8-12    │
│  ══════════════════════════════════════════════════════════════════════════ │
│                                                                              │
│  rv-android-core/domain/                                                    │
│  ├── static_output.py  ←── NOVOS modelos Pydantic canônicos                │
│  │   ├── WTGOutput                                                         │
│  │   ├── ReachOutput                                                       │
│  │   └── StaticAnalysisOutput                                              │
│  │                                                                          │
│  rv-static-analysis-lite                                                    │
│          │                                                                   │
│          ▼                                                                   │
│  Gera formato unificado (versão 2.0)                                        │
│          │                                                                   │
│          ▼                                                                   │
│  Parsers atualizados usam novos modelos                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 8.2.2 Fase 1: Compatibilidade Exata (MVP)

**Objetivo**: Integração imediata sem modificar consumidores existentes.

**Princípio**: Os arquivos gerados pelo Python devem ser **byte-a-byte compatíveis** com os esperados pelos parsers Java.

**Formatos a Manter**:

**WTG (.wtg)** - Formato JSON do GATOR:
```json
{
  "windows": [
    {
      "id": 1,
      "name": "com.example.MainActivity",
      "isMain": true,
      "type": "ACT",
      "layoutFileName": "activity_main",
      "widgets": [
        {
          "widgetId": "2131034187",
          "type": "BUTTON",
          "name": "btnSubmit",
          "text": "Submit",
          "listeners": [{"type": "OnClickListener", ...}]
        }
      ]
    }
  ],
  "transitions": [
    {
      "sourceId": 1,
      "targetId": 2,
      "events": [
        {
          "type": "click",
          "handler": "<com.example.MainActivity$1: void onClick(android.view.View)>",
          "widgetId": "2131034187",
          "widgetClass": "android.widget.Button",
          "widgetName": "btnSubmit"
        }
      ]
    }
  ]
}
```

**REACH (.reach)** - Formato CSV:
```csv
class,is_activity,is_main_activity,method,params,reachable,reaches_mop,directly_reaches_mop,signature,mop_methods_reached
com.example.MainActivity,true,true,onCreate,[android.os.Bundle],true,true,false,"<com.example.MainActivity: void onCreate(android.os.Bundle)>","[]"
```

**Notas importantes para Fase 1**:
- `params` usa `;` como separador (não `,`)
- `is_activity` e `is_main_activity` são lowercase (`true`/`false`)
- `mop_methods_reached` é uma string de lista: `"[<sig1>;<sig2>]"`
- `handler` usa formato Soot: `<class: return_type method(params)>`

**Critérios de Aceite Fase 1**:
- [ ] GatorParser consegue ler .wtg gerado pelo Python
- [ ] ReachParser consegue ler .reach gerado pelo Python
- [ ] GesdaParser consegue ler .gesda gerado pelo Python (se separado)
- [ ] TransitionManager funciona com dados do Python
- [ ] MopScorer funciona com dados do Python
- [ ] Zero mudanças em rv-agent, rv-static-analysis (parsers)

#### 8.2.3 Fase 2: Formato Unificado (Pós-MVP)

**Objetivo**: Criar formato "owned" pelo projeto Python com validação Pydantic.

**Motivação**:
- Formato atual é legado do GATOR (projeto externo)
- Sem validação de schema
- Difícil de evoluir (dois "donos")
- Metadados inconsistentes

**Novos Modelos em rv-android-core**:

```python
# rv-android-core/domain/static_output.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class OutputVersion(str, Enum):
    V1_LEGACY = "1.0"  # Compatível com GATOR
    V2_UNIFIED = "2.0"  # Novo formato unificado


class OutputMetadata(BaseModel):
    """Metadados padronizados para todos os outputs."""
    version: OutputVersion
    tool: str = "rv-static-analysis-lite"
    tool_version: str
    generated_at: datetime
    apk_path: str
    package_name: str
    analysis_duration_seconds: float
    warnings: List[str] = Field(default_factory=list)
    is_approximate: bool = False  # True se usou heurísticas/over-approximation


class WindowOutput(BaseModel):
    """Modelo unificado para Window."""
    id: str  # String, não int (mais flexível)
    name: str
    type: str  # ACT, DIALOG, OPTIONSMENU, etc.
    is_main: bool = False
    layout_file: Optional[str] = None
    widgets: List["WidgetOutput"] = Field(default_factory=list)

    class Config:
        # Permite serializar para formato legado
        json_encoders = {
            "id": lambda v: int(v) if v.isdigit() else v
        }


class TransitionOutput(BaseModel):
    """Modelo unificado para Transition."""
    id: str
    source_id: str
    target_id: str
    is_precise: bool = True  # False se over-approximation
    events: List["TransitionEventOutput"] = Field(default_factory=list)


class WTGOutput(BaseModel):
    """Modelo unificado para WTG completo."""
    metadata: OutputMetadata
    windows: List[WindowOutput]
    transitions: List[TransitionOutput]

    def to_legacy_format(self) -> dict:
        """Converte para formato GATOR v1 (compatibilidade)."""
        return {
            "windows": [
                {
                    "id": int(w.id) if w.id.isdigit() else w.id,
                    "name": w.name,
                    "isMain": w.is_main,
                    "type": w.type,
                    "layoutFileName": w.layout_file,
                    "widgets": [widget.to_legacy_format() for widget in w.widgets]
                }
                for w in self.windows
            ],
            "transitions": [
                {
                    "sourceId": int(t.source_id) if t.source_id.isdigit() else t.source_id,
                    "targetId": int(t.target_id) if t.target_id.isdigit() else t.target_id,
                    "events": [e.to_legacy_format() for e in t.events]
                }
                for t in self.transitions
            ]
        }

    def save(self, path: str, format_version: OutputVersion = OutputVersion.V2_UNIFIED):
        """Salva WTG no formato especificado."""
        if format_version == OutputVersion.V1_LEGACY:
            data = self.to_legacy_format()
        else:
            data = self.model_dump()

        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)


class ReachOutput(BaseModel):
    """Modelo unificado para Reachability."""
    metadata: OutputMetadata
    methods: List["MethodReachabilityOutput"]

    def to_legacy_csv(self, path: str):
        """Exporta para formato CSV legado."""
        # ... implementação
```

**Migração de Parsers**:

```python
# rv-static-analysis/parser/static/unified_parser.py

class UnifiedStaticAnalysisParser:
    """Parser que suporta ambos os formatos (legado e unificado)."""

    def parse_wtg(self, path: str) -> WTGOutput:
        data = json.load(open(path))

        # Detectar versão do formato
        if "metadata" in data and data.get("metadata", {}).get("version") == "2.0":
            return WTGOutput.model_validate(data)
        else:
            # Formato legado - converter para modelo unificado
            return self._parse_legacy_wtg(data)

    def _parse_legacy_wtg(self, data: dict) -> WTGOutput:
        """Converte formato GATOR legado para modelo unificado."""
        # ... implementação
```

**Critérios de Aceite Fase 2**:
- [ ] Novos modelos definidos em rv-android-core
- [ ] rv-static-analysis-lite gera formato v2.0 por padrão
- [ ] Parsers atualizados suportam ambos os formatos
- [ ] TransitionManager usa interface unificada
- [ ] Testes de compatibilidade com formato legado

### 8.3 Plano de Transição

#### 8.3.1 Timeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Timeline de Migração                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Semana 1-7: FASE 1 (MVP)                                                   │
│  ├── Implementar rv-static-analysis-lite                                    │
│  ├── Gerar formatos legados compatíveis                                     │
│  └── Validar integração com parsers existentes                              │
│                                                                              │
│  Semana 8: TRANSIÇÃO                                                        │
│  ├── Definir modelos unificados em rv-android-core                          │
│  ├── Criar UnifiedStaticAnalysisParser                                      │
│  └── Manter suporte a formato legado                                        │
│                                                                              │
│  Semana 9-10: FASE 2                                                        │
│  ├── rv-static-analysis-lite gera v2.0 por padrão                          │
│  ├── Atualizar consumidores para usar novos modelos                         │
│  └── Deprecar formato v1.0 (warning logs)                                   │
│                                                                              │
│  Semana 11-12: ESTABILIZAÇÃO                                                │
│  ├── Testes de regressão completos                                          │
│  ├── Documentação atualizada                                                │
│  └── Remover código de compatibilidade (opcional)                           │
│                                                                              │
│  Mês 4+: DEPRECIAÇÃO JAVA                                                   │
│  ├── GATOR/GESDA/REACH marcados como deprecated                             │
│  ├── Remover dependência de RVSEC_HOME para análise                         │
│  └── (Manter RVSEC_HOME apenas para instrumentação)                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 8.3.2 Estratégia de Rollback

Em caso de problemas na Fase 2:

1. **Rollback Imediato**: rv-static-analysis-lite pode gerar formato v1.0
2. **Fallback para Java**: GATOR/GESDA/REACH continuam disponíveis
3. **Flag de Configuração**: `--output-format=v1|v2` no CLI

```python
# Exemplo de flag de rollback
rv-static-analysis-lite analyze \
    --apk app.apk \
    --output-format v1  # Força formato legado
```

### 8.4 Testes de Compatibilidade

#### 9.4.1 Matriz de Compatibilidade

| Gerador | Formato | Parser | Status |
|---------|---------|--------|--------|
| GATOR (Java) | v1.0 | GatorParser | ✅ Baseline |
| rv-static-analysis-lite | v1.0 | GatorParser | ✅ Deve funcionar |
| rv-static-analysis-lite | v2.0 | UnifiedParser | ✅ Novo |
| rv-static-analysis-lite | v2.0 | GatorParser (legacy) | ⚠️ Via conversão |

#### 9.4.2 Testes de Integração

```python
# tests/integration/test_format_compatibility.py

class TestFormatCompatibility:
    """Testes de compatibilidade de formato entre Java e Python."""

    def test_python_wtg_parsed_by_gator_parser(self, python_wtg_file):
        """WTG gerado pelo Python deve ser parseável pelo GatorParser."""
        parser = GatorParser()
        wtg = parser.parse_file(python_wtg_file, package, classes, windows)

        assert wtg is not None
        assert len(wtg.transitions) > 0

    def test_python_reach_parsed_by_reach_parser(self, python_reach_file):
        """REACH gerado pelo Python deve ser parseável pelo ReachParser."""
        parser = ReachParser()
        classes = parser.parse_file(python_reach_file, None, None, None)

        assert classes is not None
        assert len(classes.methods) > 0

    def test_transition_manager_with_python_data(self, python_static_data):
        """TransitionManager deve funcionar com dados do Python."""
        manager = TransitionManager(python_static_data, DynamicStateGraph())

        guidance = manager.get_navigation_guidance(
            "com.example.MainActivity",
            mock_screen_desc
        )

        assert guidance is not None

    def test_mop_scorer_with_python_data(self, python_static_data):
        """MopScorer deve funcionar com dados do Python."""
        scorer = MopScorer(python_static_data)

        score = scorer.score(mock_action, mock_context)

        assert score >= 0
```

---

## 9. Especificação de APIs

### 9.1 API Pública (Python)

```python
# rv_static_analysis_lite/__init__.py

from .analyzer import StaticAnalyzer
from .config import AnalysisConfig
from .output.models import WTG, Window, Widget, Transition, ReachabilityResult

__all__ = [
    "StaticAnalyzer",
    "AnalysisConfig",
    "WTG",
    "Window",
    "Widget",
    "Transition",
    "ReachabilityResult",
]
```

### 9.2 Assinatura de Funções Principais

```python
class StaticAnalyzer:
    def __init__(
        self,
        apk_path: str | Path,
        timeout: int = 300,
        mop_specs_dir: str | Path | None = None,
        config: AnalysisConfig | None = None,
    ) -> None: ...

    def analyze(self) -> AnalysisResult: ...
    def analyze_wtg(self) -> WTG: ...
    def analyze_reach(self, mop_specs_dir: str | Path | None = None) -> ReachabilityResult: ...

    @property
    def apk_info(self) -> APKInfo: ...


@dataclass
class AnalysisConfig:
    # WTG options
    extract_dialogs: bool = True
    extract_fragments: bool = False
    extract_menus: bool = True
    resolve_includes: bool = True

    # REACH options
    include_framework_methods: bool = False
    max_call_graph_edges: int = 100_000

    # General options
    verbose: bool = False
    parallel: bool = False
    workers: int = 4


@dataclass
class AnalysisResult:
    wtg: WTG | None
    reachability: ReachabilityResult | None
    metadata: AnalysisMetadata

    def save(self, output_dir: str | Path) -> None: ...
    def to_dict(self) -> dict: ...
```

### 9.3 CLI Interface

```bash
# Comando principal
rv-static-analysis-lite [OPTIONS] COMMAND [ARGS]

# Comandos disponíveis
Commands:
  analyze   Run full analysis (WTG + REACH)
  wtg       Generate Window Transition Graph only
  reach     Generate reachability analysis only
  batch     Analyze multiple APKs
  info      Show APK information

# Opções globais
Options:
  --version          Show version
  --verbose, -v      Enable verbose output
  --quiet, -q        Suppress non-error output
  --help             Show help message

# Exemplo: analyze
rv-static-analysis-lite analyze \
  --apk /path/to/app.apk \
  --output /path/to/output \
  --mop-specs /path/to/specs \
  --timeout 300 \
  --format json

# Exemplo: batch
rv-static-analysis-lite batch \
  --apks-dir /path/to/apks \
  --output /path/to/results \
  --parallel \
  --workers 4 \
  --continue-on-error
```

### 9.4 Formatos de Saída

#### 9.4.1 Formato WTG (.wtg)

```json
{
  "$schema": "rv-static-analysis-lite/wtg-v1.json",
  "version": "1.0",
  "metadata": {
    "tool": "rv-static-analysis-lite",
    "tool_version": "0.1.0",
    "analysis_date": "2026-01-29T10:30:00Z",
    "duration_seconds": 45.2,
    "warnings": ["Intent resolution used over-approximation for 3 targets"]
  },
  "apk": {
    "fileName": "app.apk",
    "packageName": "com.example.app",
    "versionCode": 10,
    "versionName": "1.0.0",
    "minSdkVersion": 21,
    "targetSdkVersion": 33
  },
  "windows": [
    {
      "id": 1,
      "name": "com.example.app.MainActivity",
      "type": "ACT",
      "isMain": true,
      "layoutFileName": "activity_main",
      "widgets": [
        {
          "widgetId": "2131034187",
          "type": "BUTTON",
          "name": "btnLogin",
          "text": "Login",
          "listeners": [
            {
              "type": "OnClickListener",
              "callbackClass": "com.example.app.MainActivity$1",
              "callbackMethod": "onClick"
            }
          ]
        }
      ],
      "optionsMenu": {
        "id": 2,
        "name": "com.example.app.MainActivity",
        "type": "OPTIONSMENU",
        "widgets": [...]
      }
    }
  ],
  "transitions": [
    {
      "id": 1,
      "sourceId": 1,
      "targetId": 3,
      "precise": true,
      "events": [
        {
          "windowId": 1,
          "widgetId": "2131034187",
          "eventType": "click"
        }
      ]
    }
  ],
  "statistics": {
    "windowCount": 5,
    "activityCount": 4,
    "dialogCount": 1,
    "widgetCount": 23,
    "transitionCount": 12,
    "preciseTransitions": 10,
    "approximateTransitions": 2
  }
}
```

#### 9.4.2 Formato REACH (.reach)

```csv
class,is_activity,is_main_activity,method,params,reachable,reaches_mop,directly_reaches_mop,signature,mop_methods_reached
com.example.MainActivity,true,true,onCreate,"[android.os.Bundle]",true,true,false,"<com.example.MainActivity: void onCreate(android.os.Bundle)>","[]"
com.example.MainActivity,true,true,encrypt,"[byte[];java.lang.String]",true,true,true,"<com.example.MainActivity: byte[] encrypt(byte[],java.lang.String)>","[<java.security.MessageDigest: void update(byte[])>;<java.security.MessageDigest: byte[] digest()>]"
```

---

## 10. Modelos de Dados

### 10.1 Modelos Pydantic

```python
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class Widget(BaseModel):
    """Represents a UI widget in a window."""
    widgetId: str
    type: str  # BUTTON, TEXT_VIEW, EDIT_TEXT, etc.
    name: str | None = None
    text: str | None = None
    hint: str | None = None
    inputType: str | None = None
    listeners: list["Listener"] = Field(default_factory=list)

class Listener(BaseModel):
    """Represents a listener attached to a widget."""
    type: str  # OnClickListener, OnLongClickListener, etc.
    callbackClass: str | None = None
    callbackMethod: str | None = None

class Window(BaseModel):
    """Represents a window (Activity, Dialog, Menu) in the WTG."""
    id: int
    name: str
    type: Literal["ACT", "DIALOG", "OPTIONSMENU", "CONTEXTMENU", "FRAGMENT"]
    isMain: bool = False
    layoutFileName: str | None = None
    widgets: list[Widget] = Field(default_factory=list)
    optionsMenu: "Window | None" = None

class TransitionEvent(BaseModel):
    """Represents an event that triggers a transition."""
    windowId: int
    widgetId: str | None = None
    eventType: str  # click, long_click, menu_click, etc.

class Transition(BaseModel):
    """Represents a transition between windows."""
    id: int
    sourceId: int
    targetId: int
    precise: bool = True  # False if over-approximation was used
    events: list[TransitionEvent] = Field(default_factory=list)

class WTGMetadata(BaseModel):
    """Metadata about the WTG analysis."""
    tool: str = "rv-static-analysis-lite"
    tool_version: str
    analysis_date: datetime
    duration_seconds: float
    warnings: list[str] = Field(default_factory=list)

class APKInfo(BaseModel):
    """Basic information about the analyzed APK."""
    fileName: str
    packageName: str
    versionCode: int | None = None
    versionName: str | None = None
    minSdkVersion: int | None = None
    targetSdkVersion: int | None = None

class WTGStatistics(BaseModel):
    """Statistics about the generated WTG."""
    windowCount: int
    activityCount: int
    dialogCount: int = 0
    widgetCount: int
    transitionCount: int
    preciseTransitions: int
    approximateTransitions: int

class WTG(BaseModel):
    """Complete Window Transition Graph."""
    version: str = "1.0"
    metadata: WTGMetadata
    apk: APKInfo
    windows: list[Window]
    transitions: list[Transition]
    statistics: WTGStatistics

    def to_json(self, path: str | Path) -> None:
        """Serialize WTG to JSON file."""
        ...

    @classmethod
    def from_json(cls, path: str | Path) -> "WTG":
        """Deserialize WTG from JSON file."""
        ...


class MethodReachability(BaseModel):
    """Reachability information for a single method."""
    class_name: str = Field(alias="class")
    is_activity: bool
    is_main_activity: bool
    method: str
    params: list[str]
    reachable: bool
    reaches_mop: bool
    directly_reaches_mop: bool
    signature: str
    mop_methods_reached: list[str]

class ReachabilityResult(BaseModel):
    """Complete reachability analysis result."""
    methods: list[MethodReachability]
    metadata: dict

    def to_csv(self, path: str | Path) -> None:
        """Serialize to CSV file."""
        ...

    def to_dataframe(self) -> "pd.DataFrame":
        """Convert to pandas DataFrame."""
        ...
```

### 10.2 Diagrama de Classes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Domain Model                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐           │
│  │AnalysisResult│◆───────│    WTG      │◆────────│  Window     │           │
│  │             │         │             │    *    │             │           │
│  │ +wtg        │         │ +version    │         │ +id         │           │
│  │ +reach      │         │ +metadata   │         │ +name       │           │
│  │ +metadata   │         │ +apk        │         │ +type       │           │
│  └─────────────┘         │ +windows    │         │ +isMain     │           │
│         │                │ +transitions│         │ +layout     │           │
│         │                │ +statistics │         │ +widgets    │           │
│         │                └─────────────┘         └──────┬──────┘           │
│         │                       │                       │                   │
│         │                       │                       │ *                 │
│         │                       │                ┌──────┴──────┐           │
│         ▼                       │                │   Widget    │           │
│  ┌─────────────┐               │                │             │           │
│  │Reachability │               │                │ +widgetId   │           │
│  │   Result    │               │                │ +type       │           │
│  │             │               │                │ +name       │           │
│  │ +methods[]  │               │                │ +text       │           │
│  │ +metadata   │               │                │ +listeners  │           │
│  └─────────────┘               │                └──────┬──────┘           │
│         │                       │                       │                   │
│         │ *                     │                       │ *                 │
│         ▼                       │                ┌──────┴──────┐           │
│  ┌─────────────┐               │                │  Listener   │           │
│  │ Method      │               │                │             │           │
│  │ Reachability│               │                │ +type       │           │
│  │             │               │                │ +callback   │           │
│  │ +class      │               │                └─────────────┘           │
│  │ +method     │               │                                          │
│  │ +reachable  │               │ *                                        │
│  │ +reaches_mop│         ┌─────┴─────┐                                    │
│  └─────────────┘         │ Transition│                                    │
│                          │           │                                    │
│                          │ +id       │                                    │
│                          │ +sourceId │                                    │
│                          │ +targetId │                                    │
│                          │ +precise  │                                    │
│                          │ +events   │                                    │
│                          └───────────┘                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Plano de Implementação

### 11.1 Fases e Milestones

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Implementation Timeline                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 1: Foundation        Phase 2: REACH         Phase 3: WTG Basic       │
│  ────────────────────       ─────────────────      ──────────────────       │
│  [███████████]              [███████████████]      [████████████████████]   │
│  Week 1                     Week 2                 Week 3-4                  │
│                                                                              │
│  Phase 4: WTG Intents       Phase 5: Integration   Phase 6: Validation      │
│  ───────────────────        ──────────────────     ─────────────────        │
│  [█████████████]            [███████████]          [█████████████]          │
│  Week 5                     Week 6                 Week 7                    │
│                                                                              │
│  Extensions (Optional):                                                      │
│  ──────────────────────────────────────────────────────────────────         │
│  [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]         │
│  Week 8+                                                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Detalhamento por Fase

#### Fase 1: Foundation (Semana 1)

| Task | Descrição | Entregável | Critério de Aceite |
|------|-----------|------------|-------------------|
| F1.1 | Estrutura do módulo | Diretórios + pyproject.toml | `poetry install` funciona |
| F1.2 | Core/apk_analyzer | Wrapper Androguard | Carrega APK, retorna análise |
| F1.3 | Core/call_graph | Geração de CG | CG gerado como NetworkX |
| F1.4 | Config e exceptions | Dataclasses | Tipos definidos |
| F1.5 | Logging setup | Estrutura de logs | Logs JSON funcionais |
| F1.6 | Timeout handler | Context manager | Timeout funciona em 100% |

#### Fase 2: REACH (Semana 2)

| Task | Descrição | Entregável | Critério de Aceite |
|------|-----------|------------|-------------------|
| R2.1 | Entrypoint finder | Detecção de entry points | Todas Activities + lifecycle |
| R2.2 | MOP matcher | Carregamento de specs | JCA + Generic specs |
| R2.3 | Reachability BFS | Algoritmo de reachability | Detecta métodos alcançáveis |
| R2.4 | Reach writer | Output CSV | Formato compatível |
| R2.5 | Testes REACH | Cobertura | 80% cobertura reach/ |

#### Fase 3: WTG Basic (Semanas 3-4)

| Task | Descrição | Entregável | Critério de Aceite |
|------|-----------|------------|-------------------|
| W3.1 | Window extractor | Extração Activities | Todas Activities do manifest |
| W3.2 | Widget extractor | Parse AXML | Widgets extraídos de layouts |
| W3.3 | Layout resolver | Activity → Layout | 80% associações corretas |
| W3.4 | Listener detector | setOnXxxListener | onClick detectado |
| W3.5 | WTG writer | Output JSON | Formato compatível |
| W3.6 | Testes WTG básico | Cobertura | 80% cobertura wtg/ |

#### Fase 4: WTG Intents (Semana 5)

| Task | Descrição | Entregável | Critério de Aceite |
|------|-----------|------------|-------------------|
| I4.1 | Intent resolver (explicit) | const-class + setClass | 90% explicit resolvidos |
| I4.2 | Intent resolver (implicit) | Manifest filters | Fallback funciona |
| I4.3 | Transition builder | Construção de edges | Transições geradas |
| I4.4 | Over-approximation | Fallback seguro | Nunca falha |
| I4.5 | Testes Intents | Casos de teste | Regressão OK |

#### Fase 5: Integration (Semana 6)

| Task | Descrição | Entregável | Critério de Aceite |
|------|-----------|------------|-------------------|
| N5.1 | CLI completo | Todos os comandos | CLI funcional |
| N5.2 | API pública | Exports corretos | Import funciona |
| N5.3 | Integração rv-static-analysis | Substituição | Pipeline funciona |
| N5.4 | Documentação | README + CLAUDE.md | Docs completos |
| N5.5 | Batch mode | Múltiplos APKs | Paralelo funciona |

#### Fase 6: Validation (Semana 7)

| Task | Descrição | Entregável | Critério de Aceite |
|------|-----------|------------|-------------------|
| V6.1 | Testes com APKs problemáticos | Resultados | 100% terminam |
| V6.2 | Comparação com GATOR | Relatório | Diferenças documentadas |
| V6.3 | Performance benchmarks | Métricas | < 5min para APKs típicos |
| V6.4 | Testes de integração e2e | rv-experiment | Pipeline completo funciona |
| V6.5 | Bug fixes | Correções | Zero bugs críticos |

### 11.3 Definition of Done

Cada task é considerada "Done" quando:

1. ✅ Código implementado e revisado
2. ✅ Testes unitários passando (≥80% cobertura)
3. ✅ Type hints completos
4. ✅ Docstrings presentes
5. ✅ Linting passa (ruff/black)
6. ✅ Documentação atualizada (se necessário)

---

## 12. Estratégia de Testes

### 12.1 Pirâmide de Testes

```
                    ┌───────────────┐
                   ╱                 ╲
                  ╱     E2E Tests     ╲         5%
                 ╱   (rv-experiment)   ╲
                ╱─────────────────────────╲
               ╱                           ╲
              ╱     Integration Tests       ╲    15%
             ╱   (Full WTG/REACH pipeline)   ╲
            ╱─────────────────────────────────────╲
           ╱                                       ╲
          ╱            Unit Tests                   ╲   80%
         ╱   (Individual extractors, resolvers)      ╲
        ╱─────────────────────────────────────────────────╲
```

### 12.2 Test Cases por Categoria

#### Unit Tests

```python
# test_widget_extractor.py
class TestWidgetExtractor:
    def test_extract_button_with_id(self, layout_xml):
        """Should extract Button with android:id."""

    def test_extract_onclick_attribute(self, layout_xml):
        """Should extract android:onClick as listener."""

    def test_ignore_widget_without_id(self, layout_xml):
        """Should not include widgets without android:id."""

    def test_resolve_include_tag(self, layout_with_include):
        """Should recursively resolve <include> tags."""


# test_intent_resolver.py
class TestIntentResolver:
    def test_resolve_explicit_const_class(self, bytecode_with_const_class):
        """Should resolve new Intent(this, Target.class)."""

    def test_resolve_explicit_set_class(self, bytecode_with_set_class):
        """Should resolve intent.setClass(Target.class)."""

    def test_fallback_to_over_approximation(self, bytecode_unresolvable):
        """Should return all Activities when target unknown."""

    def test_timeout_returns_partial(self, slow_analysis):
        """Should return partial results on timeout."""
```

#### Integration Tests

```python
# test_wtg_generation.py
class TestWTGGeneration:
    def test_full_wtg_generation(self, test_apk):
        """Should generate complete WTG for test APK."""

    def test_wtg_format_compatibility(self, test_apk, expected_wtg):
        """Should produce format compatible with rv-agent."""

    def test_wtg_with_timeout(self, slow_apk):
        """Should complete with partial results within timeout."""


# test_reach_generation.py
class TestReachGeneration:
    def test_full_reach_analysis(self, test_apk, mop_specs):
        """Should detect all methods reaching MOP APIs."""

    def test_reach_format_compatibility(self, test_apk, expected_reach):
        """Should produce CSV compatible with rv-coverage."""
```

#### Regression Tests

```python
# test_problematic_apks.py
class TestProblematicAPKs:
    """Tests for APKs that caused GATOR to hang."""

    @pytest.mark.parametrize("apk_name", [
        "li.klass.fhem_141.apk",
        "com.sam.hex_16.apk",
        # ... other problematic APKs
    ])
    def test_never_hangs(self, apk_name, tmp_path):
        """All APKs must complete within timeout."""
        analyzer = StaticAnalyzer(apk_name, timeout=120)
        result = analyzer.analyze()  # Must not hang
        assert result is not None
```

### 12.3 Test Data

```
tests/fixtures/
├── apks/
│   ├── minimal.apk              # Single activity, no transitions
│   ├── two_activities.apk       # Simple A → B transition
│   ├── crypto_app.apk           # Uses crypto APIs (for REACH)
│   ├── complex_navigation.apk   # Multiple transitions, fragments
│   └── obfuscated.apk           # ProGuard obfuscated
│
├── expected/
│   ├── minimal.wtg              # Expected WTG output
│   ├── two_activities.wtg
│   ├── crypto_app.reach         # Expected REACH output
│   └── ...
│
└── mop_specs/
    ├── jca/                     # JCA crypto specs
    └── generic/                 # Generic API specs
```

### 12.4 Métricas de Qualidade

| Métrica | Meta | Ferramenta |
|---------|------|-----------|
| Line Coverage | ≥ 80% | pytest-cov |
| Branch Coverage | ≥ 70% | pytest-cov |
| Mutation Score | ≥ 60% | mutmut |
| Cyclomatic Complexity | < 10 | radon |

---

## 13. Métricas de Sucesso

### 13.1 KPIs Principais

| KPI | Meta | Medição |
|-----|------|---------|
| **Taxa de Sucesso** | 100% | APKs processados / APKs tentados |
| **Tempo Médio de Análise** | < 120s | Média em dataset de 28 APKs |
| **Timeout Graceful** | 100% | Timeouts com saída / Total timeouts |
| **Compatibilidade de Saída** | 100% | Arquivos aceitos pelo sistema existente |

### 13.2 KPIs de Qualidade

| KPI | Meta | Baseline (GATOR) |
|-----|------|------------------|
| **Precisão WTG - Windows** | ≥ 95% | ~99% |
| **Precisão WTG - Transitions** | ≥ 70% | ~90% |
| **Recall REACH - MOP methods** | ≥ 85% | ~95% |
| **False Positive Rate** | < 30% | ~5% |

### 13.3 Critérios de Aceitação do Projeto

O projeto é considerado **SUCESSO** quando:

1. ✅ 100% dos APKs do dataset terminam sem travamento
2. ✅ Formato de saída aceito por rv-agent e rv-coverage
3. ✅ rv-experiment funciona sem RVSEC_HOME (para análise)
4. ✅ Documentação completa (README, CLAUDE.md, API docs)
5. ✅ Testes com cobertura ≥ 80%

O projeto é considerado **EXCELENTE** quando também:

6. ✅ Precisão de transitions ≥ 80%
7. ✅ Extensões opcionais implementadas (stack, back navigation)
8. ✅ Performance < 60s para APKs típicos

---

## 14. Riscos e Mitigações

### 14.1 Matriz de Riscos

| ID | Risco | Probabilidade | Impacto | Score | Mitigação |
|----|-------|---------------|---------|-------|-----------|
| R1 | Androguard não suporta feature crítica | Baixa | Alto | 6 | Validação prévia, fallback manual |
| R2 | Performance muito pior que esperada | Média | Médio | 6 | Profiling, otimização lazy loading |
| R3 | Formato de saída incompatível | Baixa | Alto | 6 | Testes de integração desde início |
| R4 | Precisão muito baixa para uso prático | Média | Alto | 9 | Métricas contínuas, ajuste heurísticas |
| R5 | Escopo cresce além do planejado | Alta | Médio | 8 | Priorização rigorosa, fases claras |
| R6 | Dependência de versão específica Androguard | Média | Baixo | 4 | Pin version, testes de compatibilidade |

### 14.2 Planos de Contingência

#### R4: Precisão muito baixa

```
Se precisão de transitions < 50%:
1. Implementar heurísticas adicionais para Intent resolution
2. Considerar análise multi-pass (seção 12.6 do plano)
3. Documentar limitações claramente para usuários
4. Oferecer modo "GATOR fallback" para APKs simples
```

#### R5: Scope creep

```
Se novas features forem solicitadas:
1. Avaliar contra prioridades existentes
2. Adicionar em fase "Extensions" (não core)
3. Criar issue para tracking separado
4. Manter foco em confiabilidade primeiro
```

---

## 15. Dependências

### 15.1 Dependências de Software

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.10"
androguard = "^4.1.3"      # Core analysis
networkx = "^3.0"          # Graph operations
lxml = "^5.0"              # XML parsing
pydantic = "^2.0"          # Data models
click = "^8.0"             # CLI
rich = "^13.0"             # CLI output formatting

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
pytest-cov = "^4.0"
ruff = "^0.1"
mypy = "^1.0"
```

### 15.2 Dependências de Projeto

| Dependência | Tipo | Descrição |
|-------------|------|-----------|
| rv-android-core | Runtime | Tipos base, logging, eventos |
| rv-static-analysis | Integration | Ponto de integração existente |
| rv-experiment | Consumer | Orquestrador de experimentos |
| RVSEC MOP specs | Data | Especificações MOP para REACH |

### 15.3 Dependências de Infraestrutura

| Item | Requisito |
|------|-----------|
| Python | ≥ 3.10 |
| RAM | ≥ 8GB (recomendado 16GB) |
| Disk | ≥ 1GB para cache de análise |
| OS | Linux, macOS (Windows não testado) |

---

## 16. Considerações Futuras

### 16.1 Roadmap Pós-MVP

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Future Roadmap                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  v1.0 (MVP)           v1.1                 v1.2                 v2.0        │
│  ───────────          ─────                ─────                ─────       │
│  • WTG básico         • Stack sim          • Reflection         • ML-based  │
│  • REACH              • Back nav           • Fragments          • Intent    │
│  • CLI/API            • Lifecycle+         • Better perf        • resolution│
│  • Compatibilidade    • Dialogs            • Parallel           •           │
│                                                                              │
│  [Semanas 1-7]        [Semanas 8-10]       [Semanas 11-14]      [Futuro]   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 16.2 Possíveis Extensões

| Extensão | Descrição | Complexidade |
|----------|-----------|--------------|
| ML-based Intent Resolution | Usar embeddings para resolver intents | Alta |
| Incremental Analysis | Analisar apenas mudanças no APK | Média |
| Web UI | Dashboard para visualização de WTG | Média |
| IDE Plugin | Integração com Android Studio | Alta |
| Cloud Service | API REST para análise remota | Média |

### 16.3 Depreciação de Componentes Java

Uma vez validado o rv-static-analysis-lite:

1. **Fase 1**: Manter ambos em paralelo (3 meses)
2. **Fase 2**: Default para Python, Java como fallback
3. **Fase 3**: Deprecar componentes Java
4. **Fase 4**: Remover dependência de RVSEC_HOME completamente

---

## 17. Glossário

| Termo | Definição |
|-------|-----------|
| **WTG** | Window Transition Graph - grafo que modela navegação entre telas |
| **REACH** | Análise de reachability de métodos a partir de entry points |
| **MOP** | Monitored Operation - operação sendo monitorada por runtime verification |
| **Entry Point** | Método que pode ser chamado pelo framework Android (lifecycle, callbacks) |
| **Over-approximation** | Análise conservadora que pode incluir falsos positivos |
| **GATOR** | Ferramenta original em Java para geração de WTG |
| **Androguard** | Biblioteca Python para análise de aplicações Android |
| **CHA** | Class Hierarchy Analysis - análise de call graph baseada em hierarquia |
| **SPARK** | Points-to analysis do Soot (mais preciso que CHA) |
| **Intent** | Mecanismo Android para comunicação entre componentes |
| **Explicit Intent** | Intent que especifica diretamente o componente alvo |
| **Implicit Intent** | Intent resolvido via intent-filters do manifest |

---

## 18. Apêndices

### Apêndice A: Referências

1. [GATOR Paper - ASE 2015](https://web.cse.ohio-state.edu/presto/pubs/ase15.pdf)
2. [Androguard Documentation](https://androguard.readthedocs.io/)
3. [FlowDroid Paper - PLDI 2014](https://pp.info.uni-karlsruhe.de/uploads/publikationen/2014_pldi_flowdroid.pdf)
4. [Android Activity Lifecycle](https://developer.android.com/guide/components/activities/activity-lifecycle)

### Apêndice B: Documento de Análise

Ver: `docs/20260129_static_analysis.md`

### Apêndice C: Validação do Androguard

Testes realizados em `/tmp/androguard_test/`:
- `test_callgraph.py`: Validação de geração de call graph
- `test_xrefs.py`: Validação de detecção de APIs crypto via XREFs

Resultados: 38k nodes, 74k edges em 26s para cryptoapp.apk

### Apêndice D: Changelog

| Versão | Data | Mudanças |
|--------|------|----------|
| 1.0 | 2026-01-29 | Versão inicial do PRD |

---

**Fim do Documento**

*Este PRD deve ser revisado e aprovado antes do início da implementação.*
