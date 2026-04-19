# Integração de Broadcast Fuzzing e Service Testing no APE-RV

**Data**: 2026-03-18
**Contexto**: Análise de features do VLM-Fuzz (arXiv:2504.11675) para integração no ecossistema rv-android
**Escopo**: Análise arquitetural — NÃO implementar

---

## 1. O Que o VLM-Fuzz Faz (e o que realmente funciona)

### 1.1 Broadcast Fuzzing

O VLM-Fuzz possui `system-broadcast.json` com 187 broadcasts pré-formatados:
```json
{"action": "android.accounts.ACTION_ACCOUNT_REMOVED",
 "adb": ["adb shell am broadcast -a android.accounts.ACTION_ACCOUNT_REMOVED --es android.accounts.Account.name example@example.com --es android.accounts.Account.type com.example.account com.example.app/.MyReceiver"]}
```

**O que faz**: para cada Receiver no AndroidManifest, busca intent-filters matchando com os 187 broadcasts. Se há match, envia o broadcast com extras tipados (`--es`, `--ez`).

**O que NÃO faz** (bugs no código):
- `send_broadcast()` não tem `return` → retorna `None` → o check `if not uia.send_broadcast(...)` **sempre** é `True` → `time.sleep(2); continue` sempre executa
- Output do broadcast nunca é analisado
- Sem monitoramento de logcat pós-broadcast
- Sem verificação se o receiver processou o broadcast

### 1.2 Service Testing

**O que faz**: `am startservice package/.Service` seguido de `uia.analyze()` (mesma exploração DFS).

**O que NÃO faz**:
- `start_service()` não tem `return` → sempre retorna `None` → `analyze()` sempre é chamado (o que acidentalmente funciona)
- Sem verificação se o serviço iniciou
- Sem bind/unbind testing
- Sem lifecycle testing (stop, restart)

### 1.3 Avaliação honesta

A implementação no VLM-Fuzz é **rudimentar** — os bugs de control flow significam que broadcasts são enviados mas nunca verificados, e services são started mas o resultado é acidental. A **ideia** é boa; a **execução** é protótipo.

---

## 2. Por Que Isso É Relevante para a Tese

O objetivo da tese é **Runtime Verification** — detectar violações de propriedades (MOP) em tempo de execução. Broadcasts e Services são relevantes porque:

1. **BroadcastReceivers** frequentemente processam dados sensíveis:
   - `BOOT_COMPLETED` → inicia serviço de criptografia
   - `CONNECTIVITY_CHANGE` → sincroniza dados com TLS
   - `SMS_RECEIVED` → processa mensagem com crypto
   - Custom receivers → lógica de negócio com JCA

2. **Services** executam operações de background:
   - `IntentService` → processamento criptográfico off-thread
   - `JobService` → tarefas periódicas com TLS/cipher
   - Bound services → interface de crypto para Activities

3. **Esses code paths são INVISÍVEIS para exploração UI-only**. O SATA do APE-RV explora apenas Activities via UI. Se um BroadcastReceiver chama `Cipher.getInstance()` em `onReceive()`, essa chamada nunca é exercitada.

---

## 3. Estado Atual do Pipeline de Static Analysis

### 3.1 Arquitetura atual

```
APK
 ↓
lib/gator/gator (Python launcher)
 ↓
GATOR JVM + RvsecAnalysisClient.java (rvsec-analysis-client.jar)
 ↓
{app}.apk.json (unified JSON)
 ├── reachability[]   ← classes + methods + MOP flags
 ├── windows[]        ← Activities + widgets + listeners
 └── transitions[]    ← WTG edges
```

**Caminho do código-fonte do client GATOR**:
```
$RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/
├── client/    ← RvsecAnalysisClient (o que escreve o JSON)
├── sootandroid/ ← engine GATOR (GUI analysis)
└── commons/
```

**JARs compilados** (usados pelo rv-android):
- `lib/gator/rvsec-gator.jar` (17.2 MB) — engine GATOR
- `lib/gator/rvsec-analysis-client.jar` (59.5 MB) — client unificado (GESDA + REACH + WTG)

### 3.2 O que o RvsecAnalysisClient extrai HOJE

**Entry points para reachability** (`getEntryPoints()` no client Java):
```java
// SÓ Activities — o gap está AQUI
for (SootClass activity : output.getActivities()) {
    entryPoints.addAll(output.getLifecycleHandlers(activity));
    for (SootMethod m : activity.getMethods()) {
        if (m.isPublic() || m.isProtected()) {
            entryPoints.add(m);
        }
    }
}
```

**O que está no JSON hoje**:
- `reachability[].isActivity: true/false` — mas **SOMENTE classes de Activity** são listadas como entry points
- `windows[].type` — apenas `ACTIVITY`, `DIALOG`, `OPTIONSMENU`, `CONTEXTMENU`, `FRAGMENT`
- **Nenhuma informação sobre**: BroadcastReceivers, Services, ContentProviders, intent-filters

### 3.3 O que o GATOR/Soot JÁ tem acesso

O GATOR roda sobre o Soot framework, que faz análise completa do bytecode. Dentro da JVM do client:
- `Scene.v().getApplicationClasses()` — **TODAS** as classes do APK
- `SootClass.getSuperclass()` — permite detectar se herda de `BroadcastReceiver`, `Service`, etc.
- `SootClass.getMethods()` — todos os métodos, incluindo `onReceive()`, `onStartCommand()`
- `output.getActivities()` — lista de Activities (já usado)

**O Soot TEM as informações — o client simplesmente não as extrai.**

### 3.4 O que o MopData.java lê no APE-RV

```java
// MopData.java — lê o JSON no device
// Pass 1: reachability → bySignature map (signature → [directMop, transitiveMop])
// Pass 2: windows → widgetData (activity → shortId → MopFlags)
//                  → mopActivities (set de activities com MOP widgets)
```

O `MopScorer.java` usa esses dados para boost de prioridade:
- Widget direto MOP → +500
- Widget transitivo MOP → +300
- Activity com MOP (fallback) → +100

---

## 4. Abordagem Correta: Estender o RvsecAnalysisClient

A fonte de dados correta é o **RvsecAnalysisClient** — o client Java que roda dentro do GATOR e produz o JSON unificado. A informação sobre receivers/services deve fluir pelo **mesmo pipeline** que já existe para Activities.

### 4.1 Princípio arquitetural

```
HOJE:                                     PROPOSTO:

RvsecAnalysisClient                       RvsecAnalysisClient
  ├── extractClasses()                      ├── extractClasses()
  │   └── getActivities() only               │   └── getActivities() + getReceivers() + getServices()
  ├── extractWindows()                      ├── extractWindows()
  ├── extractTransitions()                  ├── extractTransitions()
  └── writeJson()                           ├── extractComponents()  ← NOVO
      ├── reachability                      └── writeJson()
      ├── windows                               ├── reachability (expandido)
      └── transitions                           ├── windows
                                                ├── transitions
                                                └── components  ← NOVA SEÇÃO
```

### 4.2 Mudanças no RvsecAnalysisClient (Java, dentro do GATOR)

#### 4.2.1 Expandir entry points para reachability

```java
// ANTES: só Activities como entry points
private Set<SootMethod> getEntryPoints(GUIAnalysisOutput output) {
    Set<SootMethod> entryPoints = new HashSet<>();
    for (SootClass activity : output.getActivities()) {
        entryPoints.addAll(output.getLifecycleHandlers(activity));
        // ...
    }
    return entryPoints;
}

// DEPOIS: Activities + Receivers + Services
private Set<SootMethod> getEntryPoints(GUIAnalysisOutput output) {
    Set<SootMethod> entryPoints = new HashSet<>();

    // Activities (existente)
    for (SootClass activity : output.getActivities()) {
        entryPoints.addAll(output.getLifecycleHandlers(activity));
        for (SootMethod m : activity.getMethods()) {
            if (m.isPublic() || m.isProtected()) entryPoints.add(m);
        }
    }

    // BroadcastReceivers (NOVO)
    for (SootClass receiver : findSubclasses("android.content.BroadcastReceiver")) {
        for (SootMethod m : receiver.getMethods()) {
            if (m.getName().equals("onReceive") || m.isPublic()) {
                entryPoints.add(m);
            }
        }
    }

    // Services (NOVO)
    for (SootClass service : findSubclasses("android.app.Service")) {
        for (SootMethod m : service.getMethods()) {
            String name = m.getName();
            if (name.equals("onStartCommand") || name.equals("onBind")
                || name.equals("onCreate") || name.equals("onHandleIntent")
                || m.isPublic()) {
                entryPoints.add(m);
            }
        }
    }

    return entryPoints;
}

private Set<SootClass> findSubclasses(String baseClass) {
    Set<SootClass> result = new HashSet<>();
    SootClass base = Scene.v().getSootClassUnsafe(baseClass);
    if (base == null) return result;

    Hierarchy hierarchy = Scene.v().getActiveHierarchy();
    // Soot's CHA (-withCHA flag) already builds the hierarchy
    for (SootClass appClass : Scene.v().getApplicationClasses()) {
        if (hierarchy.isClassSubclassOfIncluding(appClass, base)) {
            result.add(appClass);
        }
    }
    return result;
}
```

**Impacto na reachability**: Com receivers e services como entry points adicionais, o BFS de reachability (REACH) automaticamente descobre quais métodos MOP são atingíveis a partir desses componentes. Os flags `reachesMop` e `directlyReachesMop` passam a refletir caminhos via receivers/services.

#### 4.2.2 Marcar tipo de componente no reachability

```java
// ANTES: só isActivity e isMainActivity
"reachability": [{
    "className": "com.example.MyReceiver",
    "isActivity": false,
    "isMainActivity": false,
    "methods": [...]
}]

// DEPOIS: adicionar isReceiver, isService
"reachability": [{
    "className": "com.example.MyReceiver",
    "isActivity": false,
    "isMainActivity": false,
    "isReceiver": true,    // NOVO
    "isService": false,    // NOVO
    "methods": [...]
}]
```

Isso é **backward-compatible** — campos novos são ignorados por parsers que não os conhecem.

#### 4.2.3 Nova seção `components` no JSON

```json
{
  "reachability": [...],
  "windows": [...],
  "transitions": [...],

  "components": {
    "receivers": [
      {
        "className": "com.example.app.BootReceiver",
        "intentFilters": [
          {
            "actions": ["android.intent.action.BOOT_COMPLETED"],
            "categories": ["android.intent.category.DEFAULT"]
          }
        ],
        "exported": true,
        "reachesMop": true,
        "mopMethods": [
          "<com.example.app.BootReceiver: void onReceive(android.content.Context,android.content.Intent)>"
        ]
      }
    ],
    "services": [
      {
        "className": "com.example.app.CryptoService",
        "intentFilters": [
          {
            "actions": ["com.example.START_CRYPTO"]
          }
        ],
        "exported": false,
        "reachesMop": true,
        "mopMethods": [
          "<com.example.app.CryptoService: int onStartCommand(android.content.Intent,int,int)>"
        ]
      }
    ]
  }
}
```

**De onde vêm esses dados no Soot/GATOR**:
- `className`: `SootClass.getName()`
- `intentFilters`: Parsed do `AndroidManifest.xml` via `ProcessManifest` do Soot/FlowDroid (já disponível no classpath do GATOR)
- `exported`: Atributo `android:exported` do manifest
- `reachesMop`: Cross-reference com o BFS de reachability (mesma lógica já existente)
- `mopMethods`: Métodos do componente que atingem MOP (subset do reachability)

#### 4.2.4 Ordem de escrita (priority flush)

```java
// writeJson() — ordem de prioridade para timeout graceful
writer.beginObject();

// 1. reachability (MAIS CRÍTICO — coverage denominator)
writer.name("reachability");
writeReachability(writer);
writer.flush();

// 2. windows (UI structure)
writer.name("windows");
writeWindows(writer);
writer.flush();

// 3. transitions (WTG)
writer.name("transitions");
writeTransitions(writer);
writer.flush();

// 4. components (NOVO — receivers/services, MENOS crítico)
writer.name("components");
writeComponents(writer);
writer.flush();

writer.endObject();
```

A seção `components` é escrita **por último** — se o timeout interromper, as seções existentes são preservadas. Isso garante **zero impacto no pipeline atual** em caso de timeout.

---

## 5. Mudanças no Python (rv-static-analysis)

### 5.1 Parser: nova seção `components`

```python
# static_analysis_parser.py — adicionar parsing de components

def _parse_components(self, data: dict, code_package: str) -> Components:
    """Parse nova seção 'components' do JSON."""
    components_data = data.get("components", {})

    receivers = []
    for r in components_data.get("receivers", []):
        class_name = SignatureNormalizer.normalize(r["className"])
        if code_package not in class_name:
            continue
        receivers.append(Receiver(
            class_name=class_name,
            intent_filters=r.get("intentFilters", []),
            exported=r.get("exported", False),
            reaches_mop=r.get("reachesMop", False),
            mop_methods=r.get("mopMethods", []),
        ))

    services = []
    for s in components_data.get("services", []):
        class_name = SignatureNormalizer.normalize(s["className"])
        if code_package not in class_name:
            continue
        services.append(Service(
            class_name=class_name,
            intent_filters=s.get("intentFilters", []),
            exported=s.get("exported", False),
            reaches_mop=s.get("reachesMop", False),
            mop_methods=s.get("mopMethods", []),
        ))

    return Components(receivers=receivers, services=services)
```

### 5.2 Domain models

```python
# domain/components.py (NOVO)
@dataclass
class IntentFilter:
    actions: list[str]
    categories: list[str] = field(default_factory=list)

@dataclass
class Receiver:
    class_name: str
    intent_filters: list[IntentFilter]
    exported: bool
    reaches_mop: bool
    mop_methods: list[str]

@dataclass
class Service:
    class_name: str
    intent_filters: list[IntentFilter]
    exported: bool
    reaches_mop: bool
    mop_methods: list[str]

@dataclass
class Components:
    receivers: list[Receiver] = field(default_factory=list)
    services: list[Service] = field(default_factory=list)

    @property
    def mop_receivers(self) -> list[Receiver]:
        return [r for r in self.receivers if r.reaches_mop]

    @property
    def mop_services(self) -> list[Service]:
        return [s for s in self.services if s.reaches_mop]
```

### 5.3 Extensão do StaticAnalysisData

```python
# domain/static.py — adicionar components
@dataclass
class StaticAnalysisData:
    classes: Classes
    windows: Windows
    wtg: WindowTransitionGraph
    components: Components = field(default_factory=Components)  # NOVO
```

**Backward-compatible**: Se o JSON não tem `components` (JSONs antigos), o parser retorna `Components()` vazio.

---

## 6. Mudanças no APE-RV Java (consumer)

### 6.1 Estender MopData.java para ler `components`

```java
// MopData.java — adicionar parsing de components
public class MopData {
    // ... campos existentes ...

    // NOVO: receivers e services com MOP
    private List<ReceiverInfo> mopReceivers = new ArrayList<>();
    private List<ServiceInfo> mopServices = new ArrayList<>();

    // No parse():
    private void parseComponents(JsonReader reader) throws IOException {
        reader.beginObject();
        while (reader.hasNext()) {
            String section = reader.nextName();
            if ("receivers".equals(section)) {
                parseReceivers(reader);
            } else if ("services".equals(section)) {
                parseServices(reader);
            } else {
                reader.skipValue();
            }
        }
        reader.endObject();
    }

    private void parseReceivers(JsonReader reader) throws IOException {
        reader.beginArray();
        while (reader.hasNext()) {
            reader.beginObject();
            String className = null;
            boolean reachesMop = false;
            List<String> actions = new ArrayList<>();

            while (reader.hasNext()) {
                String key = reader.nextName();
                switch (key) {
                    case "className": className = reader.nextString(); break;
                    case "reachesMop": reachesMop = reader.nextBoolean(); break;
                    case "intentFilters": actions = parseIntentFilterActions(reader); break;
                    default: reader.skipValue();
                }
            }
            reader.endObject();

            if (reachesMop && className != null) {
                mopReceivers.add(new ReceiverInfo(className, actions));
            }
        }
        reader.endArray();
    }

    // Getters
    public List<ReceiverInfo> getMopReceivers() { return mopReceivers; }
    public List<ServiceInfo> getMopServices() { return mopServices; }
    public boolean hasComponents() { return !mopReceivers.isEmpty() || !mopServices.isEmpty(); }
}
```

### 6.2 Integração no SataAgent

```java
// SataAgent.java — usar receivers/services como escape hatch na stagnation

// No selectNewActionNonnull(), ANTES do restart:
if (graphStableCounter > Config.graphStableRestartThreshold) {
    // NOVO: tentar broadcast ANTES de restart
    if (Config.testBroadcasts && _mopData != null && _mopData.hasComponents()) {
        Action broadcastAction = selectBroadcastAction();
        if (broadcastAction != null) {
            graphStableCounter = 0;  // reset — broadcast pode desbloquear
            return broadcastAction;
        }
    }
    // Fallback existente: restart
    return getStartAction();
}

private Action selectBroadcastAction() {
    List<ReceiverInfo> receivers = _mopData.getMopReceivers();
    if (receivers.isEmpty()) return null;

    // Round-robin pelos receivers MOP
    ReceiverInfo receiver = receivers.get(broadcastIndex % receivers.size());
    broadcastIndex++;

    if (receiver.getActions().isEmpty()) return null;
    String action = receiver.getActions().get(0);

    return new BroadcastAction(ActionType.EVENT_BROADCAST,
        receiver.getClassName(), action);
}
```

### 6.3 Execução do broadcast em MonkeySourceApe

```java
// MonkeySourceApe.java
case EVENT_BROADCAST:
    BroadcastAction ba = (BroadcastAction) action;
    Intent intent = new Intent(ba.getBroadcastAction());
    intent.setComponent(new ComponentName(mPackage, ba.getReceiverClass()));
    // AndroidDevice.broadcastIntent() JÁ EXISTE (usado para IME)
    AndroidDevice.broadcastIntent(intent);
    break;

case EVENT_START_SERVICE:
    ServiceAction sa = (ServiceAction) action;
    Intent serviceIntent = new Intent();
    serviceIntent.setComponent(new ComponentName(mPackage, sa.getServiceClass()));
    // Precisa adicionar startService() em AndroidDevice — simétrico ao broadcastIntent()
    AndroidDevice.startService(serviceIntent);
    break;
```

### 6.4 Nova propriedade em Config.java

```java
static boolean testBroadcasts = getBooleanProperty("ape.testBroadcasts", false);
static boolean testServices = getBooleanProperty("ape.testServices", false);
```

E no aperv-tool Python:
```python
# APERV_PROPERTY_MAPPING — adicionar
"test_broadcasts": "ape.testBroadcasts",
"test_services": "ape.testServices",
```

---

## 7. Fluxo de Dados End-to-End

```
                         BUILD TIME (uma vez)
                         ─────────────────────
APK
 ↓
GATOR + RvsecAnalysisClient (JVM)
 │
 ├── Soot CHA: detecta subclasses de Activity, BroadcastReceiver, Service
 ├── REACH BFS: entry points = Activities + Receivers + Services
 │              → reachesMop flags incluem caminhos via onReceive()/onStartCommand()
 ├── WTG: window transitions (apenas Activities — sem mudança)
 └── Components: extrai receivers/services com intent-filters do manifest
 ↓
{app}.apk.json
 ├── reachability[]  (expandido: receivers/services como entry points)
 ├── windows[]       (sem mudança)
 ├── transitions[]   (sem mudança)
 └── components{}    (NOVO: receivers[], services[])


                         RUNTIME (cada trial)
                         ─────────────────────
aperv-tool (Python)
 ├── Push ape-rv.jar
 ├── Push {app}.apk.json → /data/local/tmp/static_analysis.json
 ├── Push ape.properties (com ape.testBroadcasts=true)
 └── Execute APE-RV

APE-RV (Java, on-device)
 ├── Config.java: lê ape.testBroadcasts=true
 ├── MopData.java: lê static_analysis.json
 │   ├── reachability → MOP scoring (existente)
 │   ├── windows → widget scoring (existente)
 │   └── components → mopReceivers[], mopServices[] (NOVO)
 └── SataAgent.java:
     ├── Exploração normal (SATA + MOP)
     ├── Stagnation detectada → tenta broadcast MOP receiver (NOVO)
     │   → AndroidDevice.broadcastIntent() (infraestrutura existente)
     │   → Se broadcast abre Activity → SATA vê a transição e explora
     └── Periodicamente → startService para MOP services (NOVO)

rv-coverage (logcat monitoring)
 └── Captura violations em receivers/services
     (já funciona — logcat captura TUDO do processo)
```

---

## 8. Impacto nas 4 Camadas

| Camada | Componente | Mudança | Backward-compatible? |
|--------|-----------|---------|---------------------|
| **1. GATOR Client** | `RvsecAnalysisClient.java` | Expandir entry points, nova seção `components` | ✅ Sim — seção extra no JSON |
| **2. rv-static-analysis** | `static_analysis_parser.py` | Parser para `components`, novos domain models | ✅ Sim — seção ausente = `Components()` vazio |
| **3. APE-RV** | `MopData.java`, `SataAgent.java`, `Config.java` | Ler `components`, broadcast actions, properties | ✅ Sim — `testBroadcasts=false` por default |
| **4. aperv-tool** | `tool.py`, property mapping | Nova property + novo variant | ✅ Sim — variant opt-in |

**Cada camada é independente** — pode ser implementada e testada separadamente. O JSON expandido é backward-compatible em todas as direções:
- JSON novo + parser antigo → seção `components` ignorada
- JSON antigo + parser novo → `Components()` vazio
- `testBroadcasts=false` (default) → APE-RV ignora components mesmo se presentes no JSON

---

## 9. Comparação com Abordagem Anterior (Opção A descartada)

| Aspecto | Opção A anterior (Androguard runtime) | Abordagem correta (GATOR pipeline) |
|---------|---------------------------------------|-------------------------------------|
| Fonte de dados | Androguard parse do APK em runtime | GATOR/Soot CHA em build time |
| Reachability MOP | Cross-reference manual (Python) | BFS nativo do REACH (já existe) |
| Intent-filters | Androguard `get_intent_filters()` | Soot `ProcessManifest` (mais preciso) |
| Consistência | Dados separados do SA principal | Dados integrados no JSON unificado |
| Onde roda | rv-platform (Python, host-side) | RvsecAnalysisClient (Java, build-time) |
| APE-RV integration | Sem integração (broadcasts pré-exploração) | Integrado ao SATA (escape hatch) |
| MOP coverage | Não afeta reachability analysis | Expande universe de métodos MOP |

**A diferença fundamental**: Com a abordagem GATOR, os métodos de receivers/services entram como **entry points do BFS de reachability**. Isso significa que o REACH descobre automaticamente quais métodos MOP são atingíveis SOMENTE via receivers/services (não via Activities). Essa informação é impossível de obter com Androguard — precisa da análise de call graph do Soot.

---

## 10. Estimativa de Impacto Revisada

### 10.1 Impacto na reachability (build-time)

Adicionar receivers/services como entry points pode **expandir o universo de métodos reachable**:
- Métodos chamados SOMENTE por `onReceive()` ou `onStartCommand()` e não por nenhuma Activity
- Esses métodos atualmente são `reachable: false` (não atingíveis por nenhum entry point)
- Com a mudança, passam a `reachable: true` e potencialmente `reachesMop: true`
- **Impacto no denominador de coverage**: o total de métodos reachable pode aumentar (mais métodos para cobrir)
- **Impacto no numerador**: broadcasts/services exercitados → novos métodos MOP executados

### 10.2 Impacto na exploração (runtime)

- **Stagnation escape**: Broadcasts como alternativa ao restart quando o grafo estagna
- **Novos estados**: Broadcasts podem abrir Activities não alcançáveis via UI direta
- **MOP coverage**: Exercitar `onReceive()` e `onStartCommand()` que chamam crypto APIs

### 10.3 Custo-benefício revisado

| Camada | Esforço | Pode ser feito em paralelo? |
|--------|---------|----------------------------|
| GATOR Client Java | 3-4 dias | Sim (repo separado) |
| rv-static-analysis parser | 1 dia | Sim |
| APE-RV Java (consumer) | 2-3 dias | Após GATOR |
| aperv-tool (Python) | 0.5 dia | Após APE-RV |
| **Total** | **~7-8 dias** | **~4-5 dias se paralelo** |

---

## 11. Priorização e Sequência

### Prioridade 1: Calibração (plano atual)
A calibração dos 19 parâmetros do APE-RV é mais impactante. Nenhuma mudança de code-path resolve se os pesos e thresholds estão errados.

### Prioridade 2: Expandir reachability no GATOR Client
Mudança mais valiosa com esforço mínimo: adicionar receivers/services como entry points no BFS. Isso **não requer mudanças no APE-RV** — apenas expande os flags `reachesMop` no JSON. O MopScorer do APE-RV já lê esses flags. Resultado: MOP scoring mais preciso para Activities que compartilham código com receivers.

### Prioridade 3: Nova seção `components` no JSON
Extrair receivers/services com intent-filters para o JSON unificado. Requer parser Python + domain models.

### Prioridade 4: Broadcast actions no APE-RV
Integrar broadcasts como escape hatch no SATA. Requer mudanças no Java do APE-RV + rebuild JAR.

### Sequência recomendada
```
Calibração (NOW) → GATOR entry points (P2) → Components JSON (P3) → Broadcast actions (P4)
       ↓                    ↓                        ↓                       ↓
  +5-10pp coverage    +0-2pp (scoring)        dados disponíveis        +1-5pp coverage
```

---

## 12. Dados do VLM-Fuzz Reutilizáveis

| Artefato | Path | Uso |
|----------|------|-----|
| 187 system broadcasts | `/tmp/VLM-Fuzz/system-broadcast.json` | Referência para extras tipados (não para parsing de manifest) |
| Component iteration pattern | `/tmp/VLM-Fuzz/main.py:108-210` | Validação: Service→Receiver→Activity (ordem importa) |

**NÃO reutilizar**: parsing de manifest (temos Soot/GATOR), catálogo de broadcasts como mecanismo principal (nossos broadcasts são guiados por reachability MOP, não por catálogo genérico), código Python do VLM-Fuzz (bugs, qualidade).

**O catálogo de 187 broadcasts pode ser útil como complemento**: para receivers com intent-filters que matcham broadcasts do sistema, os extras tipados do catálogo ajudam a construir Intents mais realistas. Mas a **decisão de quais receivers testar** vem da reachability MOP do GATOR, não do catálogo.
