# DFS vs BFS: Estratégias de Exploração do RVAgent

## Resumo Executivo

**DFS (Depth-First Search)**: Aprofunda primeiro, explora caminhos até o fim antes de retroceder.
**BFS (Breadth-First Search)**: Esgota nível atual antes de avançar, exploração mais ampla e uniforme.

---

## Diferença Fundamental

### Estrutura de Dados

```
DFS: STACK (LIFO - Last In First Out)
  [State A] → [State B] → [State C]  ← Top (próximo)
  ↑ Aprofunda até C, depois retorna

BFS: QUEUE (FIFO - First In First Out)
  [State A] → [State B] → [State C]  ← Front (próximo)
  ↑ Esgota A completamente, depois B, depois C
```

### Algoritmo

**DFS - DEEPEN (Aprofundar)**:
```
1. Encontrou ação não testada no estado atual?
   SIM → Execute e vá para próximo estado (aprofunda)
   NÃO → Retroceda para estado anterior (backtrack)

2. Mantém pilha de estados para backtracking
3. Sempre tenta ir mais fundo primeiro
```

**BFS - BREADTH (Amplitude)**:
```
1. Encontrou ação não testada no estado atual?
   SIM → Execute mas PERMANEÇA no mesmo estado
   NÃO → Mova para próximo estado na fila

2. Mantém fila de estados para exploração
3. Esgota completamente cada estado antes de avançar
```

---

## Comportamento na Prática

### Exemplo: App com 3 telas

```
Tela A: 4 ações (a1, a2, a3, a4)
  a1 → Tela B
  a2 → Tela C
  a3 → (permanece em A)
  a4 → (permanece em A)

Tela B: 2 ações (b1, b2)
Tela C: 3 ações (c1, c2, c3)
```

### Ordem de Execução DFS:
```
1. A: a1 (vai para B) ← APROFUNDA
2. B: b1 (ação em B)
3. B: b2 (ação em B, B esgotado)
4. A: a2 (retorna a A, vai para C) ← BACKTRACK + APROFUNDA
5. C: c1 (ação em C)
6. C: c2 (ação em C)
7. C: c3 (ação em C, C esgotado)
8. A: a3 (retorna a A) ← BACKTRACK
9. A: a4 (A esgotado)

Caminho: A→B (esgota B)→A→C (esgota C)→A (esgota A)
```

### Ordem de Execução BFS:
```
1. A: a1 (vai para B, mas volta para A)
2. A: a2 (vai para C, mas volta para A)
3. A: a3 (permanece em A)
4. A: a4 (permanece em A, A esgotado) ← ESGOTOU NÍVEL 0
5. B: b1 (ação em B)
6. B: b2 (ação em B, B esgotado) ← ESGOTOU NÍVEL 1
7. C: c1 (ação em C)
8. C: c2 (ação em C)
9. C: c3 (ação em C, C esgotado) ← ESGOTOU NÍVEL 1

Caminho: A (esgota A)→B (esgota B)→C (esgota C)
```

---

## Características de Cada Estratégia

### DFS (Depth-First Search)

**Vantagens**:
- ✅ Encontra caminhos profundos rapidamente
- ✅ Usa menos memória (pilha linear)
- ✅ Bom para explorar fluxos completos (ex: cadastro → confirmação → sucesso)
- ✅ Pode encontrar bugs em estados profundos mais cedo

**Desvantagens**:
- ❌ Pode ficar preso em caminhos muito profundos
- ❌ Cobertura inicial mais lenta (explora tudo em um caminho antes de outros)
- ❌ Pode demorar para descobrir todos os estados no nível superior

**Quando usar**:
- Aplicativos com fluxos lineares profundos (wizards, onboarding)
- Busca por bugs em funcionalidades específicas
- Testes focados em cenários completos
- Quando memória é limitada

---

### BFS (Breadth-First Search)

**Vantagens**:
- ✅ Cobertura uniforme e sistemática
- ✅ Descobre todos os estados próximos primeiro
- ✅ Bom para mapear a estrutura da app
- ✅ Encontra o caminho mais curto até um estado
- ✅ Melhor para calcular métricas de cobertura progressiva

**Desvantagens**:
- ❌ Usa mais memória (fila pode crescer exponencialmente)
- ❌ Pode demorar para alcançar estados profundos
- ❌ Menos eficiente para explorar fluxos lineares completos

**Quando usar**:
- Aplicativos com muitas telas no mesmo nível (dashboards, menus)
- Análise de cobertura de UI
- Testes de navegação e acessibilidade
- Quando quer garantir exploração uniforme

---

## Implementação no RVAgent

### Código-Chave

#### DFS - Usa Pilha:
```python
self.state_stack: List[DFSState] = []  # LIFO

def select_next_action(...):
    if untested_actions:
        # DEEPEN: aprofunda imediatamente
        self.current_depth += 1
        return selected_action
    else:
        # Backtrack: retorna para estado anterior na pilha
        return None
```

#### BFS - Usa Fila:
```python
self.state_queue: deque = deque()  # FIFO

def select_next_action(...):
    if untested_actions:
        # BREADTH: continua no mesmo estado
        return selected_action
    else:
        # Move para próximo estado na fila
        self.state_queue.popleft()
        return None
```

### Métodos Compartilhados:
- `_filter_actions()`: Remove system actions e nav bar
- `_get_untested_actions()`: Coordinate-based tracking
- `_select_priority_action()`: MOP prioritization
- `_convert_signature_to_optimized()`: Coordinate conversion

---

## Métricas Esperadas

### DFS:
```
Estados descobertos: Crescimento irregular (saltos quando completa um caminho)
Transições: Mais transições entre níveis (backtracking)
Profundidade máxima: Alcançada rapidamente
Tempo por estado: Variável (depende da profundidade)
```

### BFS:
```
Estados descobertos: Crescimento linear e uniforme
Transições: Menos transições entre níveis (navegação planejada)
Profundidade máxima: Alcançada gradualmente
Tempo por estado: Mais consistente (explora por nível)
```

---

## Recomendações

### Use DFS quando:
- ✅ Testar fluxos específicos e profundos
- ✅ Procurar bugs em funcionalidades completas
- ✅ Memória é limitada
- ✅ App tem poucos estados por nível mas muitos níveis

### Use BFS quando:
- ✅ Mapear a estrutura completa da app
- ✅ Análise de cobertura uniforme
- ✅ App tem muitos estados por nível
- ✅ Quervalidar navegação e acessibilidade
- ✅ Calcular métricas progressivas

### Combinação Ideal:
Execute ambos em testes diferentes:
1. **BFS primeiro** (3 min) - Mapeia estrutura geral
2. **DFS depois** (3 min) - Explora profundamente caminhos descobertos
3. **Comparar resultados** - Análise de complementaridade

---

## Como Usar

### Via CLI:
```bash
# DFS (padrão)
poetry run python modules/rv-agent/example_usage.py --mode pure_algorithm --strategy dfs

# BFS
poetry run python modules/rv-agent/example_usage.py --mode pure_algorithm --strategy bfs
```

### Via Código:
```python
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# DFS
config_dfs = RVAgentConfig(
    package_name="br.unb.cic.cryptoapp",
    agent_mode="pure_algorithm",
    strategy="dfs",
    timeout=180
)

# BFS
config_bfs = RVAgentConfig(
    package_name="br.unb.cic.cryptoapp",
    agent_mode="pure_algorithm",
    strategy="bfs",
    timeout=180
)

agent = AgentFactory.create_agent(config_bfs, ...)
results = agent.run()
```

---

## Conclusão

**DFS e BFS são complementares, não concorrentes.**

Use DFS para profundidade, BFS para amplitude.
O ideal é combinar ambos para cobertura completa e sistemática.

No modo **multimode**, a LLM pode simular comportamento híbrido,
mas os modos puros são ótimos para baseline e análise comparativa.
