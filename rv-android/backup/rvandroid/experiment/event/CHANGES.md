# Event System Modernization (Item 3.1)

Este documento resume as mudanças feitas como parte da tarefa de Modernização do Sistema de Eventos (Item 3.1) no plano de refatoração.

## Arquivos Modificados/Criados

- `bus.py`: Implementou novo EventBus com suporte assíncrono e canais especializados
- `handler.py`: Adicionou suporte a prioridades para handlers de eventos
- `models.py`: Atualizou para suportar IDs de tarefas baseados em UUID
- `processor.py`: Criou nova classe para capacidades avançadas de processamento de eventos
- `README.md`: Adicionou documentação abrangente sobre design e uso do sistema de eventos
- `utils.py`: Atualizou e expandiu funções utilitárias para trabalhar com eventos

## Principais Melhorias

### 1. Processamento Assíncrono de Eventos

Adicionado suporte para:
- Publicação assíncrona de eventos com enfileiramento
- Pool de threads para processamento concorrente
- Processamento baseado em callbacks
- Ordenação de eventos baseada em prioridade

```python
# Exemplo: Publicar evento assincronamente
event_bus.publish_task_event(
    event_type=EventType.TASK_STARTED,
    task_id="123e4567-e89b-12d3-a456-426614174000",
    source="TaskExecutor",
    async_mode=True
)

# Exemplo: Publicar com callback
event_bus.publish_with_callback(task_event, callback=on_event_processed)
```

### 2. Canais de Eventos

Implementou canais especializados para diferentes aspectos do sistema:
- `SYSTEM_CHANNEL`: Eventos de nível de sistema
- `LIFECYCLE_CHANNEL`: Eventos de ciclo de vida de tarefas e experimentos
- `ANALYSIS_CHANNEL`: Operações e resultados de análise
- `ERROR_CHANNEL`: Eventos relacionados a erros
- `USER_CHANNEL`: Interações do usuário
- `DEFAULT_CHANNEL`: Canal padrão (usado quando nenhum canal é especificado)

```python
# Exemplo: Subscrever em um canal específico
event_bus.subscribe(
    event_type=EventType.COVERAGE_UPDATED,
    callback=on_coverage_updated,
    channel=EventBus.ANALYSIS_CHANNEL
)
```

### 3. Tratamento de Eventos Baseado em Prioridade

Adicionou níveis de prioridade para controlar a ordem de execução:
- `HandlerPriority.CRITICAL`: Maior prioridade (20)
- `HandlerPriority.HIGH`: Alta prioridade (10)
- `HandlerPriority.NORMAL`: Prioridade normal (5)
- `HandlerPriority.LOW`: Baixa prioridade (0)

```python
# Exemplo: Subscrever com prioridade
event_bus.subscribe(
    event_type=EventType.TASK_FAILED,
    callback=handle_task_failure,
    priority=HandlerPriority.CRITICAL
)
```

### 4. Identificação de Tarefas Baseada em UUID

Atualizou os modelos de evento para usar strings UUID em vez de inteiros para IDs de tarefas:
- Modificou `TaskEvent` para usar IDs string
- Atualizou `ExperimentEvent` para usar IDs string para tarefas afetadas
- Atualizou `AnalysisEvent` para usar IDs string para tarefas relacionadas

Isso fornece melhor suporte para sistemas distribuídos e previne colisões de IDs.

### 5. Suporte a Injeção de Dependência

Melhorou o EventBus para suportar injeção de dependência com o método `create_instance()`, permitindo que componentes tenham suas próprias instâncias do event bus.

```python
# Exemplo: Criar event bus específico para serviço
class AnalysisService:
    def __init__(self):
        self.event_bus = EventBus.create_instance()
```

### 6. Documentação Abrangente

Adicionou documentação detalhada em `README.md`:
- Conceitos principais e arquitetura
- Exemplos de uso para cenários comuns
- Melhores práticas para tratamento de eventos
- Padrões de uso avançado

### 7. Remoção Completa de Código Legado

Em vez de manter compatibilidade com o código legado:
- Removeu completamente o código legado da implementação anterior
- Migrou todo o sistema para usar apenas canais de eventos
- Simplificou a API ao remover métodos e parâmetros de compatibilidade
- Tornou o canal DEFAULT_CHANNEL obrigatório em vez de opcional

## Notas de Migração

Componentes que usam o sistema de eventos devem:

1. Atualizar tipos de ID de tarefas de `int` para `str` (strings UUID)
2. Usar canais de eventos especializados apropriados
3. Definir prioridades apropriadas para ordenação de execução
4. Usar publicação assíncrona para operações não-bloqueantes
5. Adicionar hooks de desligamento para limpar recursos do event bus

## Melhorias Futuras

Planejadas para iterações futuras:
- Processamento em lote para cenários de alto volume
- Expiração de eventos baseada em tempo
- Funcionalidade de replay de eventos para testes
- Métricas de desempenho e monitoramento
- Persistência de eventos para eventos críticos