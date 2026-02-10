# Análise: Substituição da Análise Estática Java por Python (Androguard)

**Data:** 2026-01-29
**Status:** Planejamento
**Autor:** Claude Code

## 1. Problema

Os componentes de análise estática baseados em Soot/FlowDroid frequentemente travam em APKs complexos:

| Componente | Problema | Impacto |
|------------|----------|---------|
| **GATOR** | FixpointSolver não converge | WTG não gerado |
| **GESDA** | Call graph SPARK muito lento | Estrutura não extraída |
| **REACH** | Call graphs com 70k+ edges | Timeout em reachability |

**Problema crítico**: Timeout externo não gera arquivo de saída parcial.

### Componentes Java Atuais

```
rvsec/rvsec-android/
├── rvsec-gator/      → WTG (Window Transition Graph)
├── rvsec-gesda/      → Estrutura do app (widgets, layouts)
├── rvsec-reachability/ → Reachability de métodos MOP
├── rvsec-apk/        → Metadados do APK
└── rvsec-methods-extractor/ → Assinaturas de métodos
```

---

## 2. Análise Profunda do GATOR

### 2.1 Arquitetura Geral

GATOR é uma ferramenta sofisticada para construção de Window Transition Graphs (WTG) que modela a navegação entre telas de apps Android.

**Localização:** `/home/pedro/.../rvsec/rvsec-android/rvsec-gator/`

**Entry Points:**
- `presto.android.Main.main()` - Entry point principal
- `presto.android.gui.clients.RvsecWtgClient` - Cliente para output JSON
- `presto.android.gui.wtg.WTGBuilder` - Orquestrador do pipeline

### 2.2 Pipeline de 6 Estágios

O GATOR constrói o WTG através de um pipeline sofisticado:

```
┌─────────────────────────────────────────────────────────────────┐
│                    WTG Construction Pipeline                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Stage 1: ExplicitForwardEdgeBuilder                            │
│  ├── Build GUI hierarchy (window → views)                       │
│  ├── Detect widget handlers (onClick, onLongClick, etc.)        │
│  ├── Create edges from explicit user interactions               │
│  ├── Handle async operations (Handler.post, View.post)          │
│  └── Create implicit back event self-loops                      │
│                                                                  │
│  Stage 2: LifecycleForwardEdgeBuilder                           │
│  ├── Analyze lifecycle callbacks (onActivityResult, onNewIntent)│
│  ├── Add push/pop stack operations                              │
│  └── Build ownership mapping (activity → dialogs)               │
│                                                                  │
│  Stage 3: CloseWindowEdgeBuilder                                │
│  ├── Identify may-self-close / must-self-close windows          │
│  ├── Detect finish(), dismiss(), cancel() calls                 │
│  └── Handle owner-close scenarios                               │
│                                                                  │
│  Stage 4: CallbackSequenceBuilder                               │
│  ├── Build callback execution sequences                         │
│  └── Handle event bubbling and handler chaining                 │
│                                                                  │
│  Stage 5: BackEdgeBuilder                                       │
│  ├── Create back-edges for stack-based navigation               │
│  └── Handle interim targets                                     │
│                                                                  │
│  Stage 6: LifecycleCloseEdgeBuilder                             │
│  ├── Add edges from lifecycle-triggered closures                │
│  └── Final refinement of ownership                              │
│                                                                  │
│  [Edge Resurrection Phase]                                       │
│  └── Remove dead edges, keep only contributing edges            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Arquivo:** `sootandroid/src/main/java/presto/android/gui/wtg/WTGBuilder.java`

### 2.3 FixpointSolver

O coração do GATOR é o FixpointSolver que resolve dependências mútuas entre operações GUI:

**Arquivo:** `sootandroid/src/main/java/presto/android/gui/FixpointSolver.java`

```java
// Dados que o FixpointSolver computa:
Map<NOpNode, Set<NLayoutIdNode>> reachingLayoutIds;    // IDs de layout alcançando ops
Map<NOpNode, Set<NIdNode>> reachingViewIds;             // IDs de view alcançando ops
Map<NOpNode, Set<NNode>> reachingListeners;             // Listeners alcançando ops
Map<NActivityNode, Set<NNode>> activityRoots;           // Root view de cada activity
Map<NDialogNode, Set<NNode>> dialogRoots;               // Root view de cada dialog
```

**Problema de Convergência:**
- Iteração até ponto fixo
- APKs complexos podem não convergir
- Sem limite de iterações = loop infinito

### 2.4 Intent Analysis

Análise sofisticada para resolver targets de Intents:

**Arquivo:** `sootandroid/src/main/java/presto/android/gui/wtg/intent/IntentAnalysis.java`

```java
// Maps principais:
intentFlowtoStartActivity;     // Intent alloc → startActivity calls
intentFlowtoSetIntentContent;  // Intent alloc → setIntent/putExtra calls
intentContent;                 // Intent alloc → action/category/component
startActivitytoTarget;         // startActivity call → target activities
```

**Processo:**
1. Rastreia alocação de objetos Intent
2. Segue fluxo de dados para setAction(), setClass(), putExtra()
3. Resolve contra intent-filters do AndroidManifest.xml
4. Determina target activities (pode ser múltiplos)

### 2.5 Event Types Suportados

**Arquivo:** `sootandroid/src/main/java/presto/android/gui/listener/EventType.java`

| Categoria | Eventos |
|-----------|---------|
| **Explícitos** | click, long_click, select, scroll, swipe, drag, touch, focus_change, press_key, enter_text, item_click, item_long_click, zoom_in, zoom_out |
| **Implícitos** | implicit_lifecycle_event, implicit_on_activity_result, implicit_on_activity_newIntent, implicit_back_event, implicit_rotate_event, implicit_home_event, implicit_power_event, implicit_launch_event, implicit_async_event |

### 2.6 Uso do Soot

GATOR depende fortemente do Soot para:

1. **Bytecode Analysis**: Jimple IR, UnitGraph (CFG)
2. **Points-to Analysis**: SPARK para resolução de tipos
3. **Call Graph**: Virtual method dispatch
4. **Data-flow Analysis**: Reaching definitions

---

## 3. Capacidades do Androguard

### 3.1 O que Androguard Oferece

| Funcionalidade | API | Notas |
|---------------|-----|-------|
| **APK Parsing** | `APK(path)` | Manifest, recursos, certificados |
| **DEX Analysis** | `AnalyzeAPK(path)` | Retorna `(apk, dex, analysis)` |
| **Call Graph** | `analysis.get_call_graph()` | NetworkX MultiDiGraph |
| **XREFs** | `method.get_xref_to/from()` | Quem chama quem |
| **Basic Blocks** | `method.basic_blocks` | CFG por método |
| **Instructions** | `method.get_instructions()` | Bytecode Dalvik |
| **XML Parsing** | `AXMLPrinter(data)` | Layouts, manifest |

### 3.2 Exemplo de Uso (Script Existente)

**Arquivo:** `/home/pedro/.../rvsec-02/scripts/all_methods/reachability.py`

```python
from androguard.misc import AnalyzeAPK
from androguard.core.analysis.analysis import MethodAnalysis
import networkx as nx

# Análise do APK
apk, dex, analysis = AnalyzeAPK(apk_path)
cg = analysis.get_call_graph()  # NetworkX DiGraph

# Entry points
activities = apk.get_activities()
main_activity = apk.get_main_activity()

# Reachability
is_reachable = nx.has_path(cg, source_node, target_node)

# XREFs
for method in analysis.get_methods():
    for _, call, offset in method.get_xref_to():
        print(f"Calls: {call.class_name}.{call.name}")
```

### 3.3 Parse de Layouts XML

```python
from androguard.core.bytecodes.axml import AXMLPrinter

for filename in apk.get_files():
    if filename.startswith('res/layout/'):
        xml_data = apk.get_file(filename)
        axml = AXMLPrinter(xml_data)
        root = axml.get_xml_obj()  # lxml.etree.Element

        for elem in root.iter():
            # Extrair android:onClick
            onclick = elem.get('{http://schemas.android.com/apk/res/android}onClick')
            widget_id = elem.get('{http://schemas.android.com/apk/res/android}id')
```

### 3.4 Análise de Instruções

```python
for method in analysis.get_methods():
    if method.is_external():
        continue
    m = method.get_method()
    for idx, ins in m.get_instructions_idx():
        op_name = ins.get_name()  # e.g., "invoke-virtual"
        output = ins.get_output()  # e.g., "v0, Ljava/lang/Object;-><init>()V"

        if 'startActivity' in output:
            # Detectou chamada startActivity
            pass
```

---

## 4. Comparação: GATOR vs Androguard

### 4.1 Tabela Comparativa

| Aspecto | GATOR (Soot) | Androguard | Gap |
|---------|--------------|------------|-----|
| **Call Graph** | SPARK (points-to) | CHA-like | 🔴 Menos preciso |
| **Data Flow** | Fixed-point solver | Nenhum | 🔴 Crítico |
| **Intent Resolution** | Flow analysis completo | Manual/heurístico | 🟡 Parcial |
| **GUI Hierarchy** | Flowgraph + solver | XML parsing | 🟡 Parcial |
| **Lifecycle** | Callbacks iterativos | Entry points básicos | 🟡 Parcial |
| **Listeners** | Bytecode + flow | Bytecode simples | 🟡 Parcial |
| **Stack Ops** | Push/pop tracking | Nenhum | 🔴 Não suportado |
| **Timeout** | Nenhum (pode travar) | Nativo Python | 🟢 Androguard melhor |
| **Robustez** | Baixa | Alta | 🟢 Androguard melhor |

### 4.2 Gaps Críticos

#### 🔴 Gap 1: Points-to Analysis

**GATOR**: Usa SPARK do Soot para resolver tipos precisos
```java
// GATOR sabe que 'intent' é do tipo específico
Intent intent = new Intent(this, TargetActivity.class);
startActivity(intent);  // → Target: TargetActivity
```

**Androguard**: Apenas CHA (Class Hierarchy Analysis)
```python
# Androguard vê apenas a chamada, não o tipo exato do Intent
# Pode resultar em múltiplos targets ou nenhum
```

**Impacto**: Intent resolution menos precisa

#### 🔴 Gap 2: Fixed-Point Solver

**GATOR**: Resolve dependências mútuas
```
Layout ID → inflate() → View objects → findViewById() → Widget
                ↑                              ↓
                └──────────────────────────────┘
```

**Androguard**: Não tem equivalente

**Impacto**: Não conseguimos resolver qual view está em qual activity com certeza

#### 🔴 Gap 3: Stack Operations

**GATOR**: Rastreia push/pop de windows
```java
// GATOR sabe que após startActivity, Activity2 está no topo
startActivity(intent);  // push(Activity2)
// E que finish() remove do topo
finish();  // pop(Activity1)
```

**Androguard**: Não modela stack

**Impacto**: Back navigation não é modelada

### 4.3 Gaps Parciais (Mitigáveis)

#### 🟡 Gap 4: Intent Resolution

**Mitigação**: Combinar análise de bytecode + heurísticas

```python
def resolve_intent(method, analysis):
    """Resolve Intent targets heuristicamente."""
    for idx, ins in method.get_instructions_idx():
        if 'new-instance' in ins.get_name() and 'Intent' in ins.get_output():
            # Rastrear próximas instruções para setClass, setAction
            pass

    # Fallback: usar manifest intent-filters
    return resolve_from_manifest(action, category)
```

**Precisão esperada**: ~70% dos casos

#### 🟡 Gap 5: GUI Hierarchy

**Mitigação**: Parse XML + setContentView analysis

```python
def find_layout_for_activity(apk, activity, analysis):
    """Encontra layout associado a uma Activity."""
    # 1. Buscar setContentView no onCreate
    for method in analysis.get_class(activity).get_methods():
        if method.name == 'onCreate':
            for ins in method.get_instructions():
                if 'setContentView' in str(ins):
                    layout_id = extract_layout_id(ins)
                    return resolve_layout_name(apk, layout_id)
    return None
```

#### 🟡 Gap 6: Listener Detection

**Mitigação**: Buscar padrões de setOnXxxListener

```python
LISTENER_PATTERNS = [
    'setOnClickListener',
    'setOnLongClickListener',
    'setOnTouchListener',
    'setOnScrollListener',
    # ...
]

def find_listeners(method, analysis):
    listeners = []
    for _, call, offset in method.get_xref_to():
        for pattern in LISTENER_PATTERNS:
            if pattern in call.name:
                listeners.append({
                    'type': pattern.replace('set', '').replace('Listener', ''),
                    'method': method,
                    'offset': offset
                })
    return listeners
```

---

## 5. Alternativas Investigadas

### 5.1 PySmali

**Repo**: https://github.com/UnknownCollections/pysmali

**O que faz**:
- Parser de arquivos .smali
- Preserva formatação 100%
- Suporta modificação programática

**O que NÃO faz**:
- ❌ Análise de control flow
- ❌ Data flow analysis
- ❌ Semântica de instruções

**Conclusão**: Não ajuda para nosso caso

### 5.2 Smalanalysis

**Repo**: https://github.com/v-m/smalanalysis

**O que faz**:
- Parse de smali para objetos Python
- Mapeamento de APK interno

**Limitações**:
- Não funciona bem com APKs obfuscados
- Parser simples demais

**Conclusão**: Não suficiente

### 5.3 Androguard 4.1.3

**Status**: Call graph restaurado (PR #985, Feb 2024)

**Vantagens**:
- Implementação Python pura
- Controle total de timeout
- Nunca trava
- API rica e bem documentada

**Conclusão**: ✅ Melhor opção disponível

---

## 6. Estratégia de Implementação

### 6.1 Decisões Arquiteturais

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| Base | Androguard 4.1.3 | Robustez > Precisão |
| Call Graph | CHA (androguard) | Aceitar over-approximation |
| Intent Resolution | Heurístico | Combinar bytecode + manifest |
| GUI Hierarchy | XML parsing | Sem fixed-point solver |
| Formato Saída | Compatível (.wtg, .reach) | Não quebrar código existente |

### 6.2 Módulo Proposto: rv-static-analysis-lite

```
modules/rv-static-analysis-lite/
├── pyproject.toml
├── CLAUDE.md
├── src/rv_static_analysis_lite/
│   ├── __init__.py
│   ├── __main__.py                # CLI
│   ├── analyzer.py                # Orquestrador
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── apk_analyzer.py        # Wrapper AnalyzeAPK
│   │   └── call_graph.py          # Call graph + métricas
│   │
│   ├── wtg/
│   │   ├── __init__.py
│   │   ├── wtg_builder.py         # Construtor principal
│   │   ├── window_extractor.py    # Activities, Dialogs, Menus
│   │   ├── widget_extractor.py    # Widgets dos layouts
│   │   ├── listener_detector.py   # setOnClickListener, etc.
│   │   ├── intent_resolver.py     # Resolução heurística
│   │   └── transition_builder.py  # Constrói edges
│   │
│   ├── reach/
│   │   ├── __init__.py
│   │   ├── reachability.py        # Análise de reachability
│   │   ├── mop_matcher.py         # Match com specs MOP
│   │   └── entrypoint_finder.py   # Activities, Services, etc.
│   │
│   └── output/
│       ├── __init__.py
│       ├── wtg_writer.py          # Gera .wtg (JSON)
│       └── reach_writer.py        # Gera .reach (CSV)
│
└── tests/
    ├── fixtures/                   # APKs de teste
    └── test_*.py
```

### 6.3 Formato de Saída WTG (Compatível)

```json
{
  "fileName": "app.apk",
  "packageName": "com.example.app",
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
          "listeners": [
            {
              "type": "OnClickListener",
              "callbackMethod": {
                "name": "onClick",
                "className": "com.example.MainActivity$1"
              }
            }
          ]
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
          "window": 1,
          "widget": "2131034187",
          "event": "click"
        }
      ]
    }
  ]
}
```

### 6.4 Formato de Saída REACH (Compatível)

```csv
class,is_activity,is_main_activity,method,params,reachable,reaches_mop,directly_reaches_mop,signature,mop_methods_reached
com.example.MainActivity,true,true,onCreate,"[android.os.Bundle]",true,true,false,"<com.example.MainActivity: void onCreate(android.os.Bundle)>","[]"
com.example.MainActivity,true,true,encrypt,"[byte[];java.lang.String]",true,true,true,"<com.example.MainActivity: byte[] encrypt(byte[],java.lang.String)>","[<java.security.MessageDigest: void update(byte[])>]"
```

---

## 7. Limitações Conhecidas

### 7.1 Precisão vs GATOR

| Métrica | GATOR | rv-static-analysis-lite | Diferença |
|---------|-------|-------------------------|-----------|
| Intent Resolution | ~95% | ~70% | -25% |
| GUI Hierarchy | ~90% | ~60% | -30% |
| Listener Detection | ~95% | ~85% | -10% |
| Transition Edges | Preciso | Over-approx | Mais edges |
| Call Graph | SPARK | CHA | Mais edges |

### 7.2 O que NÃO será implementado (Core)

Na implementação core (Fases 1-6), estas funcionalidades são omitidas:

| Funcionalidade | Decisão | Justificativa |
|---------------|---------|---------------|
| Stack Operations | 🟡 Fase Ext-1 | Mitigável com simulador de pilha |
| Back Navigation | 🟡 Fase Ext-2 | Mitigável com análise de padrões |
| Lifecycle Completo | 🟡 Fase Ext-3 | Mitigável com análise de callbacks |
| Fixed-Point Solver | 🔴 Não implementar | Risco de reintroduzir problemas |
| Reflection | 🟡 Fase Ext-4 | Mitigável com over-approximation |

**Nota**: Funcionalidades marcadas como 🟡 têm implementação proposta na Seção 12 e podem ser adicionadas incrementalmente.

### 7.3 Aceitabilidade

**Por que é aceitável**:

1. **Robustez > Precisão**: Análise incompleta é pior que imprecisa
2. **Over-approximation é segura**: Falsos positivos são melhores para RV
3. **Casos simples cobertos**: Maioria dos apps não usa features avançadas
4. **Fallback disponível**: Pode-se usar GATOR quando não travar

---

## 8. Plano de Implementação

### Fase 1: Setup (30min)
- [ ] Atualizar androguard para 4.1.3
- [ ] Criar estrutura do módulo
- [ ] Configurar testes básicos

### Fase 2: REACH (2-3h)
- [ ] Adaptar `rvsec-02/scripts/all_methods/reachability.py`
- [ ] Implementar `reach/reachability.py`
- [ ] Implementar `reach/mop_matcher.py`
- [ ] Implementar `output/reach_writer.py`
- [ ] Testes com APK + specs MOP

### Fase 3: WTG Básico (3-4h)
- [ ] Implementar `wtg/window_extractor.py`
- [ ] Implementar `wtg/widget_extractor.py` (parse XML)
- [ ] Implementar `wtg/listener_detector.py`
- [ ] Implementar `output/wtg_writer.py`
- [ ] Testes de estrutura básica

### Fase 4: Intent Resolution (2h)
- [ ] Implementar `wtg/intent_resolver.py`
- [ ] Implementar `wtg/transition_builder.py`
- [ ] Testes de transições

### Fase 5: Integração (1-2h)
- [ ] Implementar `analyzer.py` (orquestrador)
- [ ] Implementar CLI (`__main__.py`)
- [ ] Integrar com `rv-static-analysis`
- [ ] Atualizar CLAUDE.md

### Fase 6: Validação (1h)
- [ ] Testar com APKs problemáticos (li.klass.fhem, etc.)
- [ ] Comparar output com GATOR (quando disponível)
- [ ] Documentar diferenças

---

## 9. Análise Detalhada: Construção do WTG no GATOR

Esta seção documenta em detalhe como o GATOR constrói o WTG e o que precisamos implementar em Python.

### 9.1 Widget Extraction (GATOR)

**Arquivo**: `sootandroid/src/main/java/presto/android/xml/DefaultXMLParser.java`

```java
private void readLayout(String file, AndroidView root, boolean isSys) {
    Document doc = dBuilder.parse(file);
    Element rootElement = doc.getDocumentElement();
    LinkedList<Pair<Node, AndroidView>> work = Lists.newLinkedList();
    work.add(new Pair<>(rootElement, root));

    while (!work.isEmpty()) {
        Pair<Node, AndroidView> p = work.removeFirst();
        Node node = p.getO1();
        AndroidView view = p.getO2();

        // Extrair ID do widget (android:id)
        Node idNode = attrMap.getNamedItemNS(ANDROID_NS, "id");
        if (idNode != null) {
            String txt = idNode.getTextContent();
            Pair<String, Integer> pair = parseAndroidId(txt, isSys);
        }

        // Extrair tipo do widget
        String guiName = node.getNodeName();

        // Extrair callback inline (android:onClick)
        String callback = readAndroidCallback(attrMap, "onClick");
        view.setInlineClickHandler(callback);

        // Extrair text/hint
        String text = readAndroidTextOrTitle(attrMap, "text");
        String hint = readAndroidTextOrTitle(attrMap, "hint");

        view.save(guiId, text, hint, guiName);
    }
}
```

**Implementação Python equivalente**:
```python
from androguard.core.bytecodes.axml import AXMLPrinter

ANDROID_NS = '{http://schemas.android.com/apk/res/android}'

def extract_widgets(apk, layout_file):
    """Extrai widgets de um layout XML."""
    xml_data = apk.get_file(layout_file)
    axml = AXMLPrinter(xml_data)
    root = axml.get_xml_obj()

    widgets = []
    for elem in root.iter():
        widget_id = elem.get(f'{ANDROID_NS}id')
        if widget_id:
            widget = {
                'widgetId': parse_android_id(widget_id),
                'type': get_widget_type(elem.tag),
                'name': extract_name_from_id(widget_id),
                'text': elem.get(f'{ANDROID_NS}text'),
                'hint': elem.get(f'{ANDROID_NS}hint'),
                'inputType': elem.get(f'{ANDROID_NS}inputType'),
            }
            # Callback inline (android:onClick)
            onclick = elem.get(f'{ANDROID_NS}onClick')
            if onclick:
                widget['listeners'] = [{'type': 'OnClickListener', 'method': onclick}]
            widgets.append(widget)
    return widgets

def get_widget_type(tag):
    """Mapeia tag XML para tipo de widget."""
    TYPE_MAP = {
        'Button': 'BUTTON',
        'TextView': 'TEXT_VIEW',
        'EditText': 'EDIT_TEXT',
        'ImageButton': 'IMAGE_BUTTON',
        'ImageView': 'IMAGE_VIEW',
        'ListView': 'LIST_VIEW',
        'CheckBox': 'CHECK_BOX',
        'RadioButton': 'RADIO_BUTTON',
        'Spinner': 'SPINNER',
    }
    # Remove namespace se presente
    simple_tag = tag.split('}')[-1] if '}' in tag else tag
    return TYPE_MAP.get(simple_tag, simple_tag.upper())
```

**Complexidade**: 🟢 Baixa - Androguard já faz o parse XML

---

### 9.2 Layout Resolution (GATOR)

O GATOR associa Activities a layouts analisando `setContentView()` no bytecode.

**Arquivo**: `sootandroid/src/main/java/presto/android/gui/wtg/flowgraph/FlowgraphRebuilder.java`

O Flowgraph rastreia:
1. Chamadas `setContentView(layoutId)` em cada Activity
2. Chamadas `LayoutInflater.inflate(layoutId, ...)`
3. O ID do layout é uma constante (`R.layout.xxx`)

**Implementação Python**:
```python
def find_layout_for_activity(analysis, apk, activity_class):
    """Encontra o layout associado a uma Activity via setContentView."""
    # Converter nome da Activity para formato Dalvik
    dalvik_name = 'L' + activity_class.replace('.', '/') + ';'

    clazz = analysis.get_class_analysis(dalvik_name)
    if not clazz:
        return None

    for method in clazz.get_methods():
        method_obj = method.get_method()
        if method_obj is None or method_obj.get_name() != 'onCreate':
            continue

        # Buscar sequência: const vX, 0x7f0xxxxx; invoke setContentView
        instructions = list(method_obj.get_instructions())
        for i, ins in enumerate(instructions):
            if 'setContentView' in str(ins.get_output()):
                # Instrução anterior deve ter o layout ID (const)
                if i > 0:
                    prev_ins = instructions[i-1]
                    if 'const' in prev_ins.get_name():
                        layout_id = extract_const_value(prev_ins)
                        return resolve_layout_name(apk, layout_id)
    return None

def resolve_layout_name(apk, layout_id):
    """Resolve ID numérico para nome do layout."""
    # Layout IDs começam com 0x7f0 (res/layout)
    # Buscar em resources.arsc
    try:
        res = apk.get_android_resources()
        if res:
            # Resolver via tabela de recursos
            return res.get_resource_name(layout_id)
    except:
        pass
    return None
```

**Complexidade**: 🟡 Média - Precisa rastrear constantes no bytecode

---

### 9.3 Listener Detection (GATOR)

**Arquivo**: `sootandroid/src/main/java/presto/android/gui/graph/NSetListenerOpNode.java`

```java
// GATOR cria um nó no grafo para cada setListener
public class NSetListenerOpNode extends NOpNode {
    private ListenerInstance listenerInstance;

    public NSetListenerOpNode(ListenerInstance listenerInstance,
                              NVarNode viewNode,
                              NNode listenerNode,
                              Pair<Stmt, SootMethod> callSite) {
        this.listenerInstance = listenerInstance;
        // Edges conectam: view → this ← listener
        listenerNode.addEdgeTo(this);
        viewNode.addEdgeTo(this);
    }
}
```

**Padrões detectados pelo GATOR**:
- `view.setOnClickListener(listener)`
- `view.setOnLongClickListener(listener)`
- `view.setOnTouchListener(listener)`
- `view.setOnItemClickListener(listener)` (ListView)
- Context menu listeners
- XML `android:onClick` attributes

**Implementação Python**:
```python
LISTENER_PATTERNS = {
    'setOnClickListener': 'click',
    'setOnLongClickListener': 'long_click',
    'setOnTouchListener': 'touch',
    'setOnFocusChangeListener': 'focus_change',
    'setOnItemClickListener': 'item_click',
    'setOnItemLongClickListener': 'item_long_click',
    'setOnScrollListener': 'scroll',
    'setOnKeyListener': 'key',
}

def detect_listeners(analysis, activity_class):
    """Detecta setOnXxxListener no bytecode de uma Activity."""
    dalvik_name = 'L' + activity_class.replace('.', '/') + ';'
    clazz = analysis.get_class_analysis(dalvik_name)
    if not clazz:
        return []

    listeners = []
    for method in clazz.get_methods():
        # Buscar chamadas a setOnXxxListener via XREFs
        for ref_class, ref_method, offset in method.get_xref_to():
            ref_name = str(ref_method.get_name()) if hasattr(ref_method, 'get_name') else str(ref_method)

            for pattern, event_type in LISTENER_PATTERNS.items():
                if pattern in ref_name:
                    listener_info = {
                        'type': event_type,
                        'setter_method': method.get_method().get_name(),
                        'offset': offset,
                        # TODO: extrair view_id e callback_class
                    }
                    listeners.append(listener_info)

    return listeners
```

**Complexidade**: 🟡 Média - Precisa analisar argumentos das chamadas

---

### 9.4 Intent Resolution (GATOR)

**Arquivo**: `sootandroid/src/main/java/presto/android/gui/wtg/intent/IntentAnalysis.java`

```java
public class IntentAnalysis {
    // Map 1: Alocação de Intent → chamadas startActivity que o recebem
    private Map<NAllocNode, Set<NStartActivityOpNode>> intentFlowtoStartActivity;

    // Map 2: Alocação de Intent → chamadas setIntent/putExtra
    private Map<NAllocNode, Set<NSetIntentContentOpNode>> intentFlowtoSetIntentContent;

    // Map 3: Conteúdo do Intent (action, extras, flags)
    private Map<NAllocNode, IntentAnalysisInfo> intentContent;

    // Map 4: StartActivity → Activities alvo
    private Multimap<NStartActivityOpNode, String> startActivitytoTarget;
}
```

**Processo do GATOR**:
1. Rastreia `new Intent()` (alocação)
2. Segue fluxo de dados para `intent.setClass()`, `intent.setAction()`
3. Resolve targets:
   - **Explicit Intent**: `new Intent(this, Target.class)` → Target direto
   - **Implicit Intent**: Match com intent-filters do manifest

**Implementação Python (heurística)**:
```python
def resolve_intent_targets(analysis, apk, method):
    """Resolve startActivity → target Activities (heurístico)."""
    targets = []
    instructions = list(method.get_method().get_instructions())

    for i, ins in enumerate(instructions):
        output = ins.get_output()
        if 'startActivity' not in output:
            continue

        # Estratégia 1: Buscar const-class nas instruções anteriores
        # Padrão: const-class vX, Lcom/example/TargetActivity;
        for j in range(max(0, i-10), i):
            prev_output = instructions[j].get_output()
            if 'const-class' in instructions[j].get_name():
                # Extrair nome da classe
                match = re.search(r'L([^;]+);', prev_output)
                if match:
                    target = match.group(1).replace('/', '.')
                    targets.append(target)
                    break

        # Estratégia 2: Buscar setClass/setComponent
        for j in range(max(0, i-15), i):
            if 'setClass' in instructions[j].get_output() or \
               'setComponent' in instructions[j].get_output():
                # Extrair target da chamada setClass
                target = extract_set_class_target(instructions, j)
                if target:
                    targets.append(target)
                    break

    # Estratégia 3: Fallback - se não encontrou, usar todas Activities
    if not targets:
        # Over-approximation: todas as Activities são possíveis targets
        targets = list(apk.get_activities())

    return list(set(targets))  # Remover duplicatas
```

**Precisão esperada**:
| Tipo de Intent | GATOR | Python (heurístico) |
|----------------|-------|---------------------|
| Explicit (const-class) | ~98% | ~90% |
| Explicit (setClass) | ~95% | ~70% |
| Implicit | ~90% | ~50% |
| Fallback | N/A | 100% (over-approx) |

**Complexidade**: 🔴 Alta - GATOR usa points-to analysis, nós usamos heurísticas

---

### 9.5 Transition Building (GATOR)

**Arquivo**: `sootandroid/src/main/java/presto/android/gui/wtg/WTGBuilder.java`

O GATOR usa um pipeline de 6 estágios:

```java
private void building() {
    // Stage 1: Edges explícitos (startActivity, showDialog, openMenu)
    Multimap<WTGEdgeSig, WTGEdge> stage1 =
        new ExplicitForwardEdgeBuilder(guiOutput, flowgraphRebuilder)
            .buildEdges(wtg);

    // Stage 2: Edges de lifecycle (onActivityResult, onNewIntent)
    Multimap<WTGEdgeSig, WTGEdge> stage2 =
        new LifecycleForwardEdgeBuilder(...)
            .buildEdges(wtg, stage1, ownership);

    // Stage 3: Edges de close (finish, dismiss)
    Multimap<WTGEdgeSig, WTGEdge> stage3 =
        new CloseWindowEdgeBuilder(...)
            .buildEdges(wtg, stage2, ownership);

    // Stage 4: Sequências de callbacks
    // Stage 5: Back edges
    // Stage 6: Lifecycle close edges
}
```

**Estrutura WTGEdge**:
```java
public class WTGEdge {
    private final WTGNode srcNode;           // Window origem
    private final WTGNode tgtNode;           // Window destino
    private final Set<EventHandler> handlers; // Eventos que disparam
    private final List<StackOperation> stackOps; // Push/pop de windows
}
```

**Implementação Python (simplificada - apenas Stage 1 e 3)**:
```python
def build_transitions(analysis, apk, windows, listeners_by_activity):
    """Constrói edges do WTG baseado em listeners e intents."""
    transitions = []
    window_by_name = {w['name']: w for w in windows}

    for window in windows:
        activity_class = window['name']
        dalvik_name = 'L' + activity_class.replace('.', '/') + ';'
        clazz = analysis.get_class_analysis(dalvik_name)
        if not clazz:
            continue

        # Analisar cada método da Activity
        for method in clazz.get_methods():
            method_obj = method.get_method()
            if method_obj is None:
                continue

            # Buscar startActivity neste método
            targets = resolve_intent_targets(analysis, apk, method)

            for target in targets:
                if target not in window_by_name:
                    continue

                target_window = window_by_name[target]

                # Determinar qual evento dispara esta transição
                event = determine_triggering_event(
                    method_obj.get_name(),
                    listeners_by_activity.get(activity_class, [])
                )

                transition = {
                    'sourceId': window['id'],
                    'targetId': target_window['id'],
                    'events': [event] if event else []
                }
                transitions.append(transition)

    # Remover duplicatas
    return deduplicate_transitions(transitions)

def determine_triggering_event(method_name, listeners):
    """Determina qual evento dispara a transição."""
    # Se método é onClick, onItemClick, etc.
    EVENT_METHODS = {
        'onClick': 'click',
        'onLongClick': 'long_click',
        'onItemClick': 'item_click',
        'onOptionsItemSelected': 'menu_click',
    }

    if method_name in EVENT_METHODS:
        return {'event': EVENT_METHODS[method_name]}

    # Buscar em listeners registrados
    for listener in listeners:
        if listener.get('callback_method') == method_name:
            return {
                'widget': listener.get('view_id'),
                'event': listener.get('type')
            }

    return None
```

**O que NÃO implementaremos**:
- Stack operations (push/pop)
- Back edges (botão back)
- Lifecycle edges (onActivityResult)
- Edge resurrection

**Complexidade**: 🟡 Média - Apenas Stage 1 e 3

---

### 9.6 Resumo: Componentes a Implementar

| Componente | GATOR | GATOR-Python | Precisão |
|------------|-------|--------------|----------|
| **Widget Extractor** | DocumentBuilder XML | Androguard AXMLPrinter | ~100% |
| **Layout Resolver** | Flowgraph + solver | Bytecode scan | ~80% |
| **Listener Detector** | NSetListenerOpNode + flow | XREFs + patterns | ~85% |
| **Intent Resolver** | Points-to + flow analysis | Heurísticas | ~70% |
| **Transition Builder** | 6-stage pipeline | Stage 1 + 3 | ~60% |

**Algoritmo simplificado final**:
```python
def build_wtg(apk_path):
    """Constrói WTG usando Androguard."""
    apk, dex, analysis = AnalyzeAPK(apk_path)

    # 1. Extrair Windows
    windows = extract_windows(apk)

    # 2. Para cada window, extrair widgets e listeners
    for window in windows:
        layout = find_layout_for_activity(analysis, apk, window['name'])
        if layout:
            window['layoutFileName'] = layout
            window['widgets'] = extract_widgets(apk, f'res/layout/{layout}.xml')
        window['_listeners'] = detect_listeners(analysis, window['name'])

    # 3. Construir transições
    listeners_by_activity = {w['name']: w.pop('_listeners', []) for w in windows}
    transitions = build_transitions(analysis, apk, windows, listeners_by_activity)

    return {
        'fileName': os.path.basename(apk_path),
        'packageName': apk.get_package(),
        'windows': windows,
        'transitions': transitions
    }
```

---

## 10. Referências

### Papers
- [GATOR Paper](https://web.cse.ohio-state.edu/presto/pubs/ase15.pdf) - Static Window Transition Graphs for Android

### Documentação
- [Androguard Docs](https://androguard.readthedocs.io/en/latest/)
- [Androguard XREFs](https://androguard.readthedocs.io/en/latest/intro/xrefs.html)
- [FlowDroid GitHub](https://github.com/secure-software-engineering/FlowDroid)

### Código Existente
- GATOR: `/home/pedro/.../rvsec/rvsec-android/rvsec-gator/`
- Reachability Script: `/home/pedro/.../rvsec-02/scripts/all_methods/reachability.py`

---

## 11. Validação do Androguard 4.1.3

### 10.1 Teste de Call Graph

**Data**: 2026-01-29
**APK de Teste**: `cryptoapp.apk` (br.unb.cic.cryptoapp)
**Ambiente**: Python venv isolado com androguard==4.1.3

**Código de Teste Completo** (`/tmp/androguard_test/test_callgraph.py`):
```python
#!/usr/bin/env python3
"""Simple test to verify androguard 4.1.3 call graph creation."""
import sys
import time

def main():
    apk_path = "/path/to/cryptoapp.apk"

    print(f"Loading APK: {apk_path}")
    start = time.time()

    # Import androguard
    from androguard.misc import AnalyzeAPK

    # Load APK - returns (APK, list[DEX], Analysis)
    print("Analyzing APK...")
    apk, dex, analysis = AnalyzeAPK(apk_path)

    load_time = time.time() - start
    print(f"APK loaded in {load_time:.2f}s")

    # Basic APK info
    print(f"Package: {apk.get_package()}")
    print(f"Main Activity: {apk.get_main_activity()}")
    print(f"Activities: {len(apk.get_activities())}")

    # Generate call graph - returns NetworkX MultiDiGraph
    print("Generating call graph...")
    cg_start = time.time()
    cg = analysis.get_call_graph()
    cg_time = time.time() - cg_start
    print(f"Call graph generated in {cg_time:.2f}s")

    # Call graph metrics
    print(f"Nodes: {cg.number_of_nodes()}")
    print(f"Edges: {cg.number_of_edges()}")

    # Sample nodes - each node is a MethodAnalysis object
    for i, node in enumerate(cg.nodes()):
        if i >= 5:
            break
        method = node.get_method()
        print(f"  {method.get_class_name()}->{method.get_name()}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**Código de Teste XREFs** (`/tmp/androguard_test/test_xrefs.py`):
```python
#!/usr/bin/env python3
"""Test XREFs to find which app methods call crypto APIs."""
from androguard.misc import AnalyzeAPK

apk_path = "/path/to/cryptoapp.apk"
apk, dex, analysis = AnalyzeAPK(apk_path)

# APIs crypto a detectar
crypto_apis = [
    'Ljavax/crypto/Cipher;',
    'Ljava/security/MessageDigest;',
    'Ljavax/crypto/KeyGenerator;',
    'Ljava/security/SecureRandom;',
]

for crypto_class in crypto_apis:
    clazz = analysis.get_class_analysis(crypto_class)
    if clazz is None:
        continue

    print(f"\n{crypto_class}:")
    for method in clazz.get_methods():
        # get_xref_from() retorna quem chama este método
        xrefs_from = list(method.get_xref_from())
        if xrefs_from:
            method_obj = method.get_method()
            if method_obj:
                print(f"  .{method_obj.get_name()}() called by:")
                for ref_class, ref_method, offset in xrefs_from[:5]:
                    caller_class = ref_method.get_class_name()
                    caller_method = ref_method.get_name()
                    print(f"    -> {caller_class}->{caller_method}")
```

**Resultados**:

| Métrica | Valor |
|---------|-------|
| Tempo de carregamento APK | 22.51s |
| Tempo de geração CG | 3.27s |
| **Tempo total** | **25.83s** |
| Nós (métodos) | 38,474 |
| Arestas (chamadas) | 74,560 |

**Info do APK**:
- Package: `br.unb.cic.cryptoapp`
- Main Activity: `br.unb.cic.cryptoapp.MainActivity`
- Activities: 4
- Services: 0
- Receivers: 0

**Amostra de Nós** (primeiros 10):
```
Lbr/unb/cic/cryptoapp/BuildConfig;-><clinit>()V
Ljava/lang/Boolean;->parseBoolean(Ljava/lang/String;)Z
Lbr/unb/cic/cryptoapp/BuildConfig;-><init>()V
Ljava/lang/Object;-><init>()V
Lbr/unb/cic/cryptoapp/MainActivity$1;-><init>()V
Lbr/unb/cic/cryptoapp/MainActivity$1;->onMenuItemClick()Z
Landroid/content/Intent;-><init>()V
Lbr/unb/cic/cryptoapp/MainActivity;->startActivity()V
```

### 10.2 Teste de XREFs (Crypto APIs)

**APIs Detectadas**:

| Classe Crypto | Métodos Chamados |
|---------------|------------------|
| `Ljavax/crypto/Cipher;` | getInstance(), init(), doFinal() |
| `Ljava/security/MessageDigest;` | getInstance(), digest(), update() |
| `Ljavax/crypto/KeyGenerator;` | getInstance(), init(), generateKey() |
| `Ljava/security/SecureRandom;` | <init>(), nextBytes() |
| `Ljavax/crypto/spec/SecretKeySpec;` | <init>() |
| `Ljavax/crypto/spec/IvParameterSpec;` | <init>() |

### 10.3 Conclusão do Teste

✅ **SUCESSO**: O androguard 4.1.3 gera call graphs funcionais:
- Call graph completo em ~26 segundos
- NetworkX DiGraph com 38k+ nós
- APIs crypto detectadas via XREFs
- Sem travamentos ou erros

**Próximo passo**: Implementar módulo rv-static-analysis-lite.

---

## 12. Melhorias Propostas (Análise de LLMs)

Esta seção documenta melhorias sugeridas por análises de múltiplas LLMs sobre o plano. Estas são **funcionalidades opcionais** que podem ser implementadas em fases futuras para aumentar a fidelidade do WTG sem sacrificar robustez.

### 12.1 Reavaliação de "Gaps Não Mitigáveis"

A classificação original de alguns gaps como "não mitigáveis" era conservadora. Análise mais profunda mostra que são **parcialmente mitigáveis** com heurísticas:

| Gap Original | Viabilidade | Nova Classificação |
|--------------|-------------|-------------------|
| Stack Operations | 7/10 | 🟡 Parcialmente mitigável |
| Back Navigation | 6/10 | 🟡 Parcialmente mitigável |
| Lifecycle Completo | 7/10 | 🟡 Parcialmente mitigável |
| Fixed-Point Solver | 3/10 | 🔴 Não recomendado |
| Reflection | 5/10 | 🟡 Parcialmente mitigável |

**Decisão**: Fixed-Point Solver permanece como "não implementar" pois contradiria o objetivo principal (robustez > precisão) e arriscaria reintroduzir problemas de convergência.

---

### 12.2 Stack Operations: Simulador de Pilha

**Problema**: O GATOR rastreia push/pop de Activities para modelar navegação.

**Solução Proposta**: Simulador de pilha conceitual baseado em análise de bytecode.

```python
class ActivityStackSimulator:
    """Simula pilha de Activities para modelar navegação."""

    def __init__(self, manifest_info: dict):
        self.stack: list[str] = []
        self.launch_modes = manifest_info.get('launch_modes', {})

    def push_activity(self, activity: str, intent_flags: list[str] = None):
        """Simula startActivity."""
        flags = intent_flags or []

        # FLAG_ACTIVITY_CLEAR_TOP: Remove atividades acima da target
        if 'FLAG_ACTIVITY_CLEAR_TOP' in flags:
            while self.stack and self.stack[-1] != activity:
                self.stack.pop()
            if self.stack and self.stack[-1] == activity:
                return  # Já no topo

        # FLAG_ACTIVITY_SINGLE_TOP: Não empilhar se já no topo
        if 'FLAG_ACTIVITY_SINGLE_TOP' in flags:
            if self.stack and self.stack[-1] == activity:
                return

        # Verificar launchMode do manifest
        launch_mode = self.launch_modes.get(activity, 'standard')
        if launch_mode == 'singleTop' and self.stack and self.stack[-1] == activity:
            return

        self.stack.append(activity)

    def pop_activity(self) -> str | None:
        """Simula finish() ou back button."""
        return self.stack.pop() if self.stack else None

    def get_back_target(self) -> str | None:
        """Retorna Activity que seria exibida após back."""
        if len(self.stack) < 2:
            return None
        return self.stack[-2]
```

**Detecção no Bytecode**:
```python
def detect_stack_operations(analysis, method):
    """Detecta push/pop de activities no bytecode."""
    operations = []
    instructions = list(method.get_method().get_instructions())

    for i, ins in enumerate(instructions):
        output = ins.get_output()

        # Detectar startActivity (push)
        if 'startActivity' in output or 'startActivityForResult' in output:
            target = resolve_intent_target(instructions, i)
            flags = extract_intent_flags(instructions, i)
            operations.append({
                'type': 'push',
                'target': target,
                'flags': flags
            })

        # Detectar finish() (pop)
        if 'finish()V' in output or 'finishActivity' in output:
            operations.append({'type': 'pop'})

    return operations

def extract_intent_flags(instructions, start_index):
    """Extrai Intent flags das instruções anteriores."""
    flags = []
    FLAG_PATTERNS = {
        'FLAG_ACTIVITY_NEW_TASK': 0x10000000,
        'FLAG_ACTIVITY_CLEAR_TOP': 0x04000000,
        'FLAG_ACTIVITY_SINGLE_TOP': 0x20000000,
        'FLAG_ACTIVITY_CLEAR_TASK': 0x00008000,
    }

    # Buscar addFlags ou setFlags nas instruções anteriores
    for i in range(max(0, start_index - 20), start_index):
        output = instructions[i].get_output()
        if 'addFlags' in output or 'setFlags' in output:
            # Extrair valor da flag da instrução const anterior
            for flag_name, flag_value in FLAG_PATTERNS.items():
                if hex(flag_value) in str(instructions[i-1].get_output()):
                    flags.append(flag_name)

    return flags
```

**Impacto**: Permite modelar ordem correta de navegação e comportamento do botão back.

---

### 12.3 Back Navigation: Modelagem do Botão Voltar

**Problema**: GATOR modela transições de "back", Androguard não.

**Solução Proposta**: Combinação de análise de stack + detecção de padrões.

```python
def detect_back_handlers(analysis, activity_class):
    """Detecta tratamento personalizado do botão back."""
    dalvik_name = 'L' + activity_class.replace('.', '/') + ';'
    clazz = analysis.get_class_analysis(dalvik_name)
    if not clazz:
        return None

    back_handler = None

    for method in clazz.get_methods():
        method_obj = method.get_method()
        if method_obj is None:
            continue

        method_name = method_obj.get_name()

        # Padrão 1: Override de onBackPressed()
        if method_name == 'onBackPressed':
            back_handler = {
                'type': 'onBackPressed_override',
                'method': method_name,
                'custom_behavior': analyze_back_pressed(method)
            }

        # Padrão 2: Tratamento de KEYCODE_BACK em onKeyDown
        if method_name in ('onKeyDown', 'onKeyUp'):
            if has_back_key_handling(method):
                back_handler = {
                    'type': 'key_event_handling',
                    'method': method_name
                }

    return back_handler

def generate_back_transitions(windows, stack_simulator):
    """Gera transições sintéticas de back navigation."""
    back_transitions = []

    for window in windows:
        if window.get('isMain', False):
            continue  # Main activity não tem back (sai do app)

        # Simular navegação até esta activity
        # e determinar qual seria o target do back
        back_target = determine_back_target(window, stack_simulator)

        if back_target:
            back_transitions.append({
                'sourceId': window['id'],
                'targetId': back_target['id'],
                'events': [{
                    'event': 'implicit_back_event',
                    'synthetic': True
                }]
            })

    return back_transitions
```

**Análise do Manifest** (bônus):
```python
def read_launch_modes_from_manifest(apk):
    """Lê launchMode e noHistory do AndroidManifest."""
    launch_modes = {}

    # Parse do manifest
    manifest = apk.get_android_manifest_xml()

    for activity in manifest.findall('.//activity'):
        name = activity.get('{http://schemas.android.com/apk/res/android}name')
        launch_mode = activity.get('{http://schemas.android.com/apk/res/android}launchMode', 'standard')
        no_history = activity.get('{http://schemas.android.com/apk/res/android}noHistory', 'false')

        launch_modes[name] = {
            'launchMode': launch_mode,
            'noHistory': no_history == 'true'
        }

    return launch_modes
```

---

### 12.4 Lifecycle Completo: Análise Estendida

**Problema**: Apenas entry points básicos (onCreate) são analisados.

**Solução Proposta**: Análise sistemática de todos os callbacks de lifecycle.

```python
LIFECYCLE_CALLBACKS = {
    'Activity': [
        # Lifecycle padrão
        'onCreate', 'onStart', 'onResume', 'onPause', 'onStop', 'onDestroy', 'onRestart',
        # Result handling
        'onActivityResult', 'onNewIntent',
        # State management
        'onSaveInstanceState', 'onRestoreInstanceState',
        # Permission handling (API 23+)
        'onRequestPermissionsResult',
    ],
    'Service': [
        'onCreate', 'onStartCommand', 'onBind', 'onUnbind', 'onDestroy', 'onRebind',
    ],
    'BroadcastReceiver': [
        'onReceive',
    ],
    'Fragment': [
        'onCreate', 'onCreateView', 'onViewCreated', 'onStart', 'onResume',
        'onPause', 'onStop', 'onDestroyView', 'onDestroy', 'onActivityResult',
    ],
}

def analyze_component_lifecycle(analysis, component_class, component_type='Activity'):
    """Analisa todos os callbacks de lifecycle de um componente."""
    dalvik_name = 'L' + component_class.replace('.', '/') + ';'
    clazz = analysis.get_class_analysis(dalvik_name)
    if not clazz:
        return {}

    lifecycle_info = {}
    expected_callbacks = LIFECYCLE_CALLBACKS.get(component_type, [])

    for method in clazz.get_methods():
        method_obj = method.get_method()
        if method_obj is None:
            continue

        method_name = method_obj.get_name()

        if method_name in expected_callbacks:
            # Analisar o que o método faz
            lifecycle_info[method_name] = {
                'implemented': True,
                'calls_super': has_super_call(method),
                'starts_activities': find_start_activity_calls(method),
                'shows_dialogs': find_show_dialog_calls(method),
                'finishes': find_finish_calls(method),
            }

    # Marcar callbacks não implementados
    for callback in expected_callbacks:
        if callback not in lifecycle_info:
            lifecycle_info[callback] = {'implemented': False}

    return lifecycle_info

def find_transitions_from_lifecycle(lifecycle_info, windows):
    """Encontra transições originadas de callbacks de lifecycle."""
    transitions = []

    # onActivityResult pode disparar navegação baseada em resultCode
    if 'onActivityResult' in lifecycle_info and lifecycle_info['onActivityResult']['implemented']:
        for activity_start in lifecycle_info['onActivityResult'].get('starts_activities', []):
            transitions.append({
                'type': 'lifecycle_transition',
                'trigger': 'onActivityResult',
                'target': activity_start
            })

    # onNewIntent pode mudar comportamento da activity
    if 'onNewIntent' in lifecycle_info and lifecycle_info['onNewIntent']['implemented']:
        # Marcar que esta activity pode receber intents em background
        pass

    return transitions
```

**Impacto**: Captura transições que ocorrem em callbacks além do onCreate.

---

### 12.5 Reflection Detection: Over-Approximation

**Problema**: Reflection permite chamadas dinâmicas não detectáveis estaticamente.

**Solução Proposta**: Detectar padrões e aplicar over-approximation conservadora.

```python
REFLECTION_PATTERNS = [
    ('Ljava/lang/Class;', 'forName', 'class_load'),
    ('Ljava/lang/Class;', 'getMethod', 'method_lookup'),
    ('Ljava/lang/Class;', 'getDeclaredMethod', 'method_lookup'),
    ('Ljava/lang/reflect/Method;', 'invoke', 'method_invoke'),
    ('Ljava/lang/reflect/Constructor;', 'newInstance', 'instance_creation'),
    ('Ljava/lang/Class;', 'newInstance', 'instance_creation'),
]

def detect_reflection_usage(analysis):
    """Detecta uso de reflection no APK."""
    reflection_sites = []

    for method in analysis.get_methods():
        if method.is_external():
            continue

        for ref_class, ref_method, offset in method.get_xref_to():
            ref_class_name = str(ref_class.name) if hasattr(ref_class, 'name') else str(ref_class)
            ref_method_name = str(ref_method.get_name()) if hasattr(ref_method, 'get_name') else str(ref_method)

            for pattern_class, pattern_method, reflection_type in REFLECTION_PATTERNS:
                if pattern_class in ref_class_name and pattern_method in ref_method_name:
                    # Tentar extrair string literal (nome da classe/método)
                    target_string = extract_string_before_call(method, offset)

                    reflection_sites.append({
                        'caller_class': method.get_method().get_class_name(),
                        'caller_method': method.get_method().get_name(),
                        'reflection_type': reflection_type,
                        'potential_target': target_string,
                        'offset': offset,
                    })

    return reflection_sites

def apply_reflection_over_approximation(cg, reflection_sites, all_methods):
    """Aplica over-approximation para reflection no call graph."""
    added_edges = []

    for site in reflection_sites:
        if site['reflection_type'] == 'method_invoke':
            caller_method = find_method_in_cg(cg, site['caller_class'], site['caller_method'])

            if site['potential_target']:
                # Temos o nome do método alvo - adicionar edge específica
                target_method = find_method_by_name(all_methods, site['potential_target'])
                if target_method:
                    cg.add_edge(caller_method, target_method, reflection=True)
                    added_edges.append((site, target_method))
            else:
                # Sem informação - marcar para análise manual
                site['needs_manual_review'] = True

    return added_edges

def generate_reflection_report(reflection_sites):
    """Gera relatório de uso de reflection para revisão."""
    report = {
        'total_sites': len(reflection_sites),
        'by_type': {},
        'unresolved': [],
        'resolved': [],
    }

    for site in reflection_sites:
        rtype = site['reflection_type']
        report['by_type'][rtype] = report['by_type'].get(rtype, 0) + 1

        if site.get('potential_target'):
            report['resolved'].append(site)
        else:
            report['unresolved'].append(site)

    return report
```

**Impacto**: Identifica locais de reflection para análise manual ou over-approximation automática.

---

### 12.6 Multi-Pass Heuristic (Alternativa ao Fixed-Point)

Em vez de um solver de ponto fixo que pode não convergir, usar abordagem de múltiplas passagens com número fixo de iterações:

```python
class MultiPassAnalyzer:
    """Análise em múltiplas passagens em vez de fixed-point."""

    def __init__(self, apk, analysis, max_passes=3):
        self.apk = apk
        self.analysis = analysis
        self.max_passes = max_passes

        # Estado acumulado entre passagens
        self.activity_layouts = {}      # Activity → Layout
        self.layout_widgets = {}        # Layout → Widgets
        self.widget_listeners = {}      # Widget → Listeners
        self.listener_callbacks = {}    # Listener → Callback methods

    def analyze(self):
        """Executa análise em múltiplas passagens."""
        for pass_num in range(self.max_passes):
            changes = 0

            # Pass 1: Activity → Layout (via setContentView)
            changes += self._pass_activity_layouts()

            # Pass 2: Layout → Widgets (via XML parsing)
            changes += self._pass_layout_widgets()

            # Pass 3: Widget → Listener (via findViewById + setOnXxxListener)
            changes += self._pass_widget_listeners()

            # Se nenhuma mudança, convergiu
            if changes == 0:
                break

        return self._build_result()

    def _pass_activity_layouts(self):
        """Passagem 1: Mapeia Activities para Layouts."""
        changes = 0

        for activity in self.apk.get_activities():
            if activity in self.activity_layouts:
                continue

            layout = find_layout_for_activity(self.analysis, self.apk, activity)
            if layout:
                self.activity_layouts[activity] = layout
                changes += 1

        return changes

    def _pass_layout_widgets(self):
        """Passagem 2: Extrai Widgets dos Layouts."""
        changes = 0

        for activity, layout in self.activity_layouts.items():
            if layout in self.layout_widgets:
                continue

            layout_file = f'res/layout/{layout}.xml'
            if layout_file in [f for f in self.apk.get_files()]:
                widgets = extract_widgets(self.apk, layout_file)
                self.layout_widgets[layout] = widgets
                changes += len(widgets)

        return changes

    def _pass_widget_listeners(self):
        """Passagem 3: Conecta Widgets a Listeners via bytecode."""
        changes = 0

        for activity in self.apk.get_activities():
            layout = self.activity_layouts.get(activity)
            if not layout:
                continue

            widgets = self.layout_widgets.get(layout, [])
            widget_ids = {w['widgetId'] for w in widgets if w.get('widgetId')}

            # Analisar bytecode da Activity
            listeners = detect_listeners_with_widgets(
                self.analysis, activity, widget_ids
            )

            for listener in listeners:
                widget_id = listener.get('widget_id')
                if widget_id and widget_id not in self.widget_listeners:
                    self.widget_listeners[widget_id] = listener
                    changes += 1

        return changes

    def _build_result(self):
        """Constrói resultado final da análise."""
        return {
            'activity_layouts': self.activity_layouts,
            'layout_widgets': self.layout_widgets,
            'widget_listeners': self.widget_listeners,
            'passes_executed': self.max_passes,
        }
```

**Vantagem**: Evita loops infinitos do fixed-point solver enquanto captura a maioria das relações.

---

### 12.7 Resumo: Fases de Implementação Estendidas

| Fase | Funcionalidade | Prioridade | Complexidade |
|------|---------------|------------|--------------|
| Core | REACH + WTG básico | 🔴 Alta | Média |
| Ext-1 | Stack Operations | 🟡 Média | Média |
| Ext-2 | Back Navigation | 🟡 Média | Média |
| Ext-3 | Lifecycle Completo | 🟢 Baixa | Baixa |
| Ext-4 | Reflection Detection | 🟢 Baixa | Média |
| Ext-5 | Multi-Pass Analyzer | 🟡 Média | Alta |

**Recomendação**: Implementar fases Core primeiro. Fases Ext-* são opcionais e podem ser adicionadas incrementalmente baseado em necessidade.

---

## 13. Próximos Passos

1. ✅ **Validar androguard 4.1.3** - Concluído
2. **Criar módulo rv-static-analysis-lite**
3. **Implementar REACH primeiro** (já temos base)
4. **Implementar WTG básico** (sem stack/back)
5. **Validar com APKs problemáticos**
6. **Integrar no pipeline de experimentos**
7. **(Opcional) Implementar melhorias Ext-1 a Ext-5**
