# Framework de Testes e Avaliação para LLM e Estratégias de Prompt

Este documento detalha o design e os requisitos para o framework de testes e avaliação do sistema RV-Android, focado na avaliação de diferentes modelos LLM e estratégias de prompt para teste de aplicativos Android.

## 1. Visão Geral

O framework de testes permitirá a avaliação sistemática e comparativa de diferentes configurações de modelos LLM e estratégias de prompt em vários aplicativos Android, com foco em métricas de cobertura de código e detecção de erros MOP.

### 1.1 Objetivos Principais

- Avaliar diferentes configurações de LLM (modelos, parâmetros) e estratégias de prompt
- Testar múltiplos aplicativos com cada configuração para garantir robustez
- Executar testes com diferentes timeouts para identificar plateaus de eficácia
- Coletar métricas de cobertura, erros MOP, tempo de resposta e eficiência de exploração
- Suportar tanto testes automatizados quanto manuais
- Identificar configurações ótimas para diferentes tipos de aplicativos
- Fornecer visualizações e análises dos resultados

### 1.2 Estrutura Organizacional

```
rv-android/
├─ rvandroid/           # Módulo principal (existente)
├─ test_framework/      # Novo módulo para testes e avaliações
│  ├─ executor/         # Execução de experimentos
│  ├─ collectors/       # Coleta de métricas
│  ├─ analyzers/        # Análise de resultados
│  ├─ benchmarks/       # Configurações de benchmark
│  ├─ config/           # Configurações de testes
│  ├─ visualization/    # Visualização de resultados
│  └─ utils/            # Utilitários
```

## 2. Componentes do Framework

### 2.1 Configuração de Experimentos

A configuração de experimentos será definida em um formato estruturado que especifica:

- Lista de aplicativos a serem testados
- Configurações de LLM e estratégias de prompt a serem avaliadas
- Conjunto de timeouts para identificar plateaus
- Número de repetições para análise estatística
- Métricas a serem coletadas
- Modo de execução (sequencial ou paralelo)

Exemplo de configuração:

```json
{
  "name": "experimento_01",
  "description": "Avaliação de estratégias composable vs. single_action",
  "apps": ["app_A", "app_B", "app_C"],
  "configurations": [
    {
      "name": "config_01",
      "model_type": "llama3",
      "model_name": "llama3.2:3b",
      "strategy_type": "composable_single_action",
      "parameters": {
        "temperature": 0.2,
        "max_tokens": 800
      }
    },
    {
      "name": "config_02",
      "model_type": "gemma",
      "model_name": "gemma3:4b",
      "strategy_type": "single_action",
      "parameters": {
        "temperature": 0.3,
        "max_tokens": 800
      }
    }
  ],
  "timeouts": [60, 180, 300, 600],
  "repetitions": 3,
  "metrics": ["coverage", "mop_errors", "response_time"],
  "execution": {
    "mode": "sequential",
    "max_parallel_instances": 1,
    "unload_models": true
  }
}
```

### 2.2 Executor de Experimentos

O executor será responsável por configurar e executar os testes conforme definido na configuração.

#### 2.2.1 Modos de Execução

- **Sequencial (Padrão)**: Um aplicativo, configuração e timeout por vez
- **Paralelo (Opcional)**: Múltiplas combinações executadas simultaneamente em diferentes emuladores

> **IMPORTANTE**: Cada teste SEMPRE utilizará uma instância nova e limpa de emulador para evitar interferências entre testes. A ordenação mencionada refere-se apenas à sequência de testes, não ao reuso de emuladores.

#### 2.2.2 Processo de Execução

1. Para cada combinação (app, configuração, timeout, repetição):
   - Iniciar uma nova instância de emulador limpa
   - Instalar o aplicativo de teste
   - Configurar o LLM e a estratégia de prompt
   - Executar o teste pelo tempo determinado
   - Coletar métricas
   - Encerrar e limpar o emulador
   - Salvar resultados intermediários

2. Estratégia de agrupamento para execução sequencial (apenas para otimização):
   - Agrupar testes que usam o mesmo modelo LLM para reduzir carregamentos de modelo
   - Executar diferentes timeouts do mesmo aplicativo e configuração em sequência
   - Sempre com instâncias de emulador separadas e limpas

### 2.3 Coletores de Métricas

O framework integrará com os sistemas existentes para coletar:

#### 2.3.1 Métricas de Cobertura
- Cobertura de atividades (quais activities foram visitadas)
- Cobertura de métodos (quais métodos foram executados)
- Cobertura de instruções (porcentagem de código executado)

#### 2.3.2 Métricas de Erros MOP
- Número total de erros detectados
- Tipos de erros (por categoria)
- Frequência de cada tipo de erro
- Tempo até primeira detecção de erro

#### 2.3.3 Métricas de LLM
- Tempo de resposta do modelo
- Número de tokens gerados
- Número de ações geradas
- Taxa de ações válidas vs. inválidas

#### 2.3.4 Métricas de Exploração
- Número de telas únicas visitadas
- Profundidade de exploração
- Cobertura de elementos de UI
- Padrões de navegação

### 2.4 Análise de Resultados

#### 2.4.1 Análise de Plateau

O sistema detectará automaticamente quando as métricas atingem um plateau:

- Detecção baseada em taxa de mudança (ex: menos de 2% de aumento em cobertura em intervalos consecutivos)
- Identificação do tempo necessário para atingir determinados percentuais da cobertura máxima (50%, 75%, 90%)
- Comparação de velocidade de progresso entre diferentes configurações

#### 2.4.2 Análise Comparativa

- Ranqueamento de configurações baseado em múltiplas métricas
- Identificação de pontos fortes e fracos de cada configuração
- Análise de variância entre repetições para medir consistência

#### 2.4.3 Análise de Aplicativo-Específica

- Classificação de aplicativos por características (complexidade, tipo de UI, recursos)
- Correlação entre características de apps e desempenho de configurações
- Recomendação de configurações ideais para tipos específicos de aplicativos

### 2.5 Gerenciamento de Recursos

Para lidar com restrições de recursos:

#### 2.5.1 Monitoramento de Recursos
- Acompanhamento de uso de memória e CPU durante testes
- Alertas para uso excessivo de recursos

#### 2.5.2 Estratégias para Máquinas Limitadas
- Opção para descarregar modelos LLM da memória entre testes
- Modo econômico para máquinas com recursos limitados (8GB RAM)
- Limitação automática do número de instâncias paralelas baseado em recursos disponíveis

#### 2.5.3 Checkpoints e Recuperação
- Salvar estado periodicamente durante execuções longas
- Capacidade de retomar testes interrompidos
- Registro de resultados incrementais

### 2.6 Visualização de Resultados

#### 2.6.1 Dashboard Interativo
- Visão geral de resultados
- Filtros por aplicativo, configuração, métrica
- Comparação lado a lado

#### 2.6.2 Gráficos e Visualizações
- Progressão temporal de métricas
- Comparação entre configurações
- Análise de plateau
- Heatmaps de cobertura

#### 2.6.3 Relatórios Exportáveis
- Sumários em formato PDF/HTML
- Dados brutos em CSV para análises externas
- Gráficos e visualizações

## 3. Fluxo de Trabalho

### 3.1 Definição de Experimento
1. Criar arquivo de configuração de experimento
2. Selecionar aplicativos de teste
3. Definir configurações a serem avaliadas
4. Configurar timeouts e repetições

### 3.2 Execução
1. Validar configuração
2. Preparar ambiente (download de modelos se necessário)
3. Executar combinações (app, configuração, timeout)
4. Monitorar progresso e recursos
5. Salvar resultados intermediários

### 3.3 Análise
1. Processar dados coletados
2. Detectar plateaus
3. Comparar configurações
4. Gerar visualizações
5. Produzir recomendações

### 3.4 Iteração
1. Ajustar configurações baseado em resultados
2. Refinar estratégias de prompt
3. Executar novos experimentos
4. Comparar resultados com experimentos anteriores

## 4. Considerações Técnicas

### 4.1 Integrações com Sistema Existente

O framework aproveitará componentes existentes:

- **Sistema de Configuração**: Utilizará o sistema de configuração refatorado
- **Gerenciamento de Emulador**: Integrará com o controle de emulador existente
- **Análise de Cobertura**: Aproveitará os analisadores de cobertura existentes
- **Detecção de Erros MOP**: Utilizará o sistema de monitoramento JavaMOP
- **Eventos e Métricas**: Integrará com o sistema de eventos para coleta de dados

### 4.2 Armazenamento de Dados

- Resultados armazenados em formato padronizado (JSON/SQLite)
- Histórico de experimentos preservado para comparações
- Dados brutos e processados mantidos para análises posteriores

### 4.3 Extensibilidade

- Suporte para adicionar novos modelos LLM
- Interface para novas estratégias de prompt
- Sistema de plugins para métricas adicionais
- API para integração com ferramentas externas

## 5. Implementação e Priorização

### 5.1 Fases de Implementação

1. **Fase 1**: Estrutura básica, configuração e executor sequencial
2. **Fase 2**: Coletores de métricas e análise de plateau
3. **Fase 3**: Visualizações e dashboard
4. **Fase 4**: Execução paralela e gerenciamento avançado de recursos

### 5.2 Componentes Prioritários

1. Framework de configuração de experimentos
2. Executor sequencial com suporte a múltiplos timeouts
3. Integração com sistema de métricas existente
4. Detecção de plateau e análise temporal
5. Visualizações básicas de resultados comparativos

### 5.3 Componentes Secundários

1. Execução paralela
2. Dashboard interativo avançado
3. Análise preditiva para configurações ótimas
4. Otimização automática de parâmetros

## 6. Considerações Finais

O framework de testes fornecerá uma plataforma abrangente para avaliação sistemática de configurações LLM e estratégias de prompt no contexto de testes de aplicativos Android. Ele permitirá identificar as melhores abordagens para diferentes cenários, otimizar o tempo de execução baseado em análise de plateau, e produzir insights acionáveis para melhorar o sistema como um todo.

As decisões de design priorizam:
- Isolamento entre testes (emuladores limpos para cada teste)
- Compatibilidade com recursos limitados (modo sequencial como padrão)
- Análise abrangente (múltiplos apps, configurações e timeouts)
- Reprodutibilidade e consistência nos resultados
- Flexibilidade para evoluir com novos modelos e estratégias