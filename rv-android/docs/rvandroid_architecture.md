# RVAndroid Tool Architecture

## 1. Introduction

RVAndroid is an AI-driven Android testing tool within the RV-Android ecosystem that integrates language models with DroidBot to provide intelligent, context-aware testing actions. The tool systematically explores application functionality and triggers runtime monitors through LLM-guided decision making.

This document details the architecture, components, and execution flow of the RVAndroid tool, focusing on DroidBot and LLM integration.

### 1.1 Purpose and Goals

RVAndroid addresses key challenges in Android application testing:

1.  **Intelligent Action Selection**: Uses LLMs to understand application context and select meaningful test actions
2.  **Pattern Recognition**: Identifies common UI patterns (forms, lists, tabs) and applies appropriate testing strategies
3.  **Systematic Exploration**: Explores application functionality more thoroughly than traditional techniques
4.  **Monitored Operation Coverage**: Focuses testing efforts on paths that lead to monitored operations
5.  **Context-Aware Testing**: Considers application state and user interaction patterns

The system achieves these goals through architecture that integrates DroidBot's state exploration capabilities with LLM-based decision making.

### 1.2 Relationship to Other Components

RVAndroid fits into the broader RV-Android ecosystem:

1.  **RV-Android Platform**: Parent platform providing runtime verification foundation, including instrumentation, property specification, and result collection

2.  **DroidBot**: Underlying testing framework that RVAndroid enhances. DroidBot handles device interaction, state exploration, and action execution, while RVAndroid provides intelligence for action selection

3.  **RVDroid Tool**: Alternative testing tool with different architecture approach

4.  **rv-llm Module**: Provides LLM integration framework used by RVAndroid for prompt generation and language model interaction

RVAndroid leverages DroidBot's capabilities while adding an LLM-driven decision layer for testing effectiveness.

For detailed information about the LLM integration architecture, please refer to [docs/rv_llm_architecture.md](rv_llm_architecture.md).

## 2. System Architecture

### 2.1 High-Level Architecture

RVAndroid follows a client-server architecture where a custom DroidBot policy sends state information to the RVAndroid server, which processes the state and returns recommended actions:

```
┌─────────────────┐                      ┌───────────────────────────────────┐
│                 │                      │                                   │
│     DroidBot    │                      │            RVAndroid              │
│                 │                      │                                   │
│  ┌───────────┐  │                      │  ┌─────────────┐ ┌─────────────┐  │
│  │           │  │  HTTP/REST           │  │             │ │             │  │
│  │ RVAndroid ├──┼───────────────────────► │ State       │ │ Server      │  │
│  │ Policy    │  │  State Data          │  │ Processing  │ │ Component   │  │
│  │           │  │                      │  │             │ │             │  │
│  └───────┬───┘  │                      │  └──────┬──────┘ └──────┬──────┘  │
│          │      │                      │         │               │         │
│          │      │                      │         ▼               │         │
│          │      │                      │  ┌─────────────┐        │         │
│          │      │                      │  │             │        │         │
│          │      │  HTTP/REST           │  │ LLM Action  │        │         │
│          └──────┼◄──────────────────────┼─┤ Service     │        │         │
│                 │  Action Decisions    │  │             │        │         │
│                 │                      │  └─────┬───────┘        │         │
└─────────────────┘                      │        │                │         │
                                         │        │                │         │
                                         │        ▼                ▼         │
                                         │  ┌─────────────┐ ┌─────────────┐  │
                                         │  │             │ │             │  │
                                         │  │ Prompt      │ │ Screen      │  │
                                         │  │ Framework   │ │ Parser      │  │
                                         │  │             │ │             │  │
                                         │  └─────┬───────┘ └──────┬──────┘  │
                                         │        │                │         │
                                         │        ▼                │         │
                                         │  ┌─────────────┐        │         │
                                         │  │             │        │         │
                                         │  │ Language    │◄───────┘         │
                                         │  │ Model       │                  │
                                         │  │             │                  │
                                         │  └─────────────┘                  │
                                         │                                   │
                                         └───────────────────────────────────┘
```

### 2.2 Core Components

RVAndroid comprises key components:

1.  **RVAndroid Policy (DroidBot Side)**: Custom DroidBot policy that communicates with the RVAndroid server

2.  **Server Component**: REST API server that receives state information from DroidBot and returns action decisions

3.  **Screen Parser**: Processes DroidBot state data into structured UI representation (ScreenDescription)

4.  **State Enricher**: Enhances state with additional information such as detected UI patterns and monitored operations

5.  **LLM Action Service**: Orchestrates the process of generating and selecting testing actions based on current state

6.  **Prompt Framework**: Manages prompt generation for language models using templates and information fragments

7.  **Language Model Interface**: Interfaces with various LLM providers to generate action decisions based on prompts

Each component is modular and extensible, allowing for customization and testing process improvements.

## 3. Execution Flow

### 3.1 Overview

The RVAndroid execution flow follows a cyclic pattern where each cycle involves:
1.  DroidBot explores a state
2.  State information is sent to RVAndroid
3.  RVAndroid processes the state and generates action recommendations
4.  DroidBot executes the recommended actions
5.  The cycle repeats with the new state

This cycle continues until testing criteria are met or a time limit is reached.

### 3.2 Detailed Execution Flow

The following sections detail each step of the execution flow, explaining the data transformations and component interactions.

#### 3.2.1 DroidBot State Exploration

The execution cycle begins with DroidBot exploring the Android application:

1.  **Application Launch**: DroidBot starts the application under test on the emulator or device.

2.  **Initial State Capture**: DroidBot captures the initial application state, including:
    *   Current activity name
    *   UI hierarchy (view tree)
    *   Screenshots
    *   Available actions on UI elements

3.  **State Preparation**: DroidBot's RVAndroid policy preprocesses the state data, including:
    *   Creating a unique state identifier
    *   Extracting basic UI element properties
    *   Identifying possible actions for each UI element
    *   Packaging the state data for transmission

```python
# Pseudocode from RVAndroid Policy in DroidBot
def generate(self, current_state):
    """Generate the next action based on current state"""
    if current_state is None:
        return None
    
    # Prepare state data
    state_data = {
        'state_id': current_state.state_id,
        'activity': current_state.foreground_activity,
        'views': current_state.views,
        'screenshot_path': current_state.screenshot_path,
        'enabled_actions': self.get_enabled_actions(current_state)
    }
    
    # Send state to RVAndroid server
    response = self.send_state_to_server(state_data)
    
    # Process response and return action
    return self.parse_response(response, current_state)
```

#### 3.2.2 State Transmission

The DroidBot policy transmits state data to the RVAndroid server:

1.  **HTTP Request Preparation**: The state data is formatted as a JSON payload.

2.  **REST API Call**: An HTTP POST request is sent to the RVAndroid server's `/api/state` endpoint.

3.  **Synchronous Communication**: DroidBot waits for the RVAndroid server's response before proceeding.

The state data contains comprehensive information about the current application state, including:
- Activity name
- UI element hierarchy
- Element properties (text, resource IDs, bounds, etc.)
- Available actions
- Screenshot path

```
Example state data JSON:
{
  "state_id": "3a2b1c0d",
  "activity": "com.example.app.MainActivity",
  "views": [
    {
      "class": "android.widget.EditText",
      "resource_id": "com.example.app:id/username",
      "text": "",
      "bounds": [[50, 100], [300, 150]],
      "clickable": true,
      "enabled": true,
      "focused": false,
      "visible": true
    },
    {
      "class": "android.widget.Button",
      "resource_id": "com.example.app:id/login_button",
      "text": "Login",
      "bounds": [[100, 200], [250, 250]],
      "clickable": true,
      "enabled": true,
      "focused": false,
      "visible": true
    }
  ],
  "enabled_actions": [
    {
      "action_type": "touch",
      "view": {"resource_id": "com.example.app:id/login_button"},
      "action_id": 1
    },
    {
      "action_type": "set_text",
      "view": {"resource_id": "com.example.app:id/username"},
      "action_id": 2
    }
  ],
  "screenshot_path": "/path/to/screenshot.png"
}
```

#### 3.2.3 Server-Side State Processing

When the RVAndroid server receives state data, it processes it through several stages:

1.  **Request Handling**:
    ```python
    @app.route('/api/state', methods=['POST'])
    def process_state():
        """Process the state and return action recommendations."""
        state_data = request.json
        actions = action_service.process_state(state_data)
        return jsonify(actions)
    ```

2.  **Screen Parsing**: The raw state data is parsed into a structured ScreenDescription object:
    ```python
    # Screen parsing
    parser = ParserFactory.create(ParserType.DROIDBOT, BasicTextVisitor)
    screen_description = parser.parse(state_data, static_data)
    state_data[StateEntry.STRUCTURED_SCREEN] = screen_description
    ```

3.  **State Enrichment**: The StateEnricher adds additional context to the state:
    ```python
    # State enrichment
    enriched_state = state_enricher.enrich_state(state_data)
    ```

    This enrichment includes:
    - Adding screen descriptions
    - Processing screenshots for additional insights
    - Detecting UI patterns (forms, lists, etc.)
    - Adding monitored operations information based on static analysis

4.  **Action Generation**: The LLMActionService generates action recommendations:
    ```python
    # Action generation
    actions = llm_action_service.generate_actions(enriched_state)
    ```

#### 3.2.4 Prompt Generation and LLM Consultation

The core of RVAndroid's intelligence lies in its interaction with the language model:

1.  **Strategy Selection**: The system selects an appropriate prompt strategy based on the current state and configuration:
    ```python
    strategy = self.strategy_registry.get_strategy(self.prompt_config.strategy_type)
    ```

2.  **Prompt Assembly**: The selected strategy assembles a prompt using:
    - UI element information
    - Detected patterns
    - Action history
    - Application context
    - Monitored operations (if present)

    ```python
    # Information gathering
    information = self.information_manager.compose_information(state, context)
    
    # Template selection
    template_name = self.get_template_name(context) or self.DEFAULT_TEMPLATE
    
    # Prompt generation
    messages = self.template_repository.create_messages(template_name, {**information, **context})
    ```

3.  **LLM Consultation**: The assembled prompt is sent to the language model:
    ```python
    # Send prompt to LLM
    response = self.language_model.generate(messages)
    ```

4.  **Response Processing**: The LLM's response is parsed to extract action decisions:
    ```python
    # Parse response
    actions = self.response_parser.parse(response, available_actions)
    ```

The prompt includes detailed information about the application state and testing context, enabling the LLM to make informed decisions:

```
Example LLM Prompt:

System: You are an Android testing assistant. Your task is to help test the Android application by selecting the most effective testing actions.

The current screen contains the following UI elements:
1. EditText [id: username, text: "", hint: "Enter username", enabled: true, clickable: true]
2. EditText [id: password, text: "", hint: "Enter password", enabled: true, clickable: true]
3. Button [id: login_button, text: "Login", enabled: true, clickable: true]

I've identified this screen as a LOGIN FORM pattern.

Available actions:
[1] TOUCH on "Login" button
[2] SET_TEXT on username field
[3] SET_TEXT on password field

User: Based on the current screen, select the SINGLE most effective testing action by providing its ID. Return your answer as a JSON object.
```

#### 3.2.5 Action Selection and Response

After consulting the LLM, RVAndroid selects and formats the final action recommendations:

1.  **Action Validation**: Ensure selected actions are valid and executable:
    ```python
    validated_actions = self.validate_actions(raw_actions, available_actions)
    ```

2.  **Action Prioritization**: Prioritize actions based on their relevance to testing goals:
    ```python
    prioritized_actions = self.prioritize_actions(validated_actions, state)
    ```

3.  **Response Preparation**: Format the actions for return to DroidBot:
    ```python
    response = {
        'actions': prioritized_actions,
        'metadata': {
            'strategy': strategy_name,
            'reasoning': reasoning
        }
    }
    ```

The response includes the selected actions along with metadata explaining the decision:

```
Example response:
{
  "actions": [
    {
      "action_id": 2,
      "action_type": "set_text",
      "view": {"resource_id": "com.example.app:id/username"},
      "params": {"text": "testuser"}
    },
    {
      "action_id": 3,
      "action_type": "set_text",
      "view": {"resource_id": "com.example.app:id/password"},
      "params": {"text": "password123"}
    },
    {
      "action_id": 1,
      "action_type": "touch",
      "view": {"resource_id": "com.example.app:id/login_button"}
    }
  ],
  "metadata": {
    "strategy": "batch",
    "reasoning": "Filled form fields with test data and submitted the form to test login functionality."
  }
}
```

#### 3.2.6 DroidBot Action Execution

Finally, DroidBot executes the recommended actions:

1.  **Response Parsing**: The DroidBot policy parses the RVAndroid server response:
    ```python
    def parse_response(self, response, current_state):
        """Parse the response from RVAndroid server."""
        if not response or 'actions' not in response:
            return None
           
        # Get the first action to execute
        action_data = response['actions'][0]
       
        # Convert to DroidBot action
        return self.convert_to_droidbot_action(action_data, current_state)
    ```

2.  **Action Execution**: DroidBot executes the action on the device:
    ```python
    # In DroidBot core
    def execute(self, action):
        """Execute an action on the device."""
        self.logger.info("Executing %s" % action)
        action.execute()
        self.last_event_time = time.time()
        self.last_event = action
    ```

3.  **New State Capture**: After execution, DroidBot captures the new application state:
    ```python
    # In DroidBot core
    def explore(self):
        """Start exploring the app."""
        while not self.stopped:
            # Get current state
            current_state = self.get_current_state()
           
            # Get next action
            action = self.policy.generate(current_state)
           
            # Execute action
            self.execute(action)
    ```

4.  **Cycle Continuation**: The cycle begins again with the new state, forming a continuous testing loop.

### 3.3 Implementation Details

#### 3.3.1 DroidBot Policy Implementation

The RVAndroid policy in DroidBot is implemented as a Python class that inherits from DroidBot's base Policy class:

```python
class RVAndroidPolicy(Policy):
    """A policy that interacts with the RVAndroid server for action decisions."""
    
    def __init__(self, device, app, server_url="http://localhost:5000"):
        super(RVAndroidPolicy, self).__init__(device, app)
        self.server_url = server_url
        self.session = requests.Session()
        self.action_history = []
        self.logger = logging.getLogger("RVAndroidPolicy")
        
    def generate(self, current_state):
        """Generate the next action based on current state."""
        if current_state is None:
            return None
            
        try:
            state_data = self.prepare_state_data(current_state)
            response = self.send_state_to_server(state_data)
            return self.parse_response(response, current_state)
        except Exception as e:
            self.logger.error(f"Error communicating with RVAndroid server: {e}")
            # Fall back to random policy if server communication fails
            return super(RVAndroidPolicy, self).generate(current_state)
```

#### 3.3.2 RVAndroid Server Implementation

The RVAndroid server is implemented using Flask, providing a RESTful API for DroidBot communication:

```python
from flask import Flask, request, jsonify
from rvandroid_tool.llm.service.action_service import LLMActionService
from rvandroid_tool.config.tool_config import RvAndroidToolConfig

app = Flask(__name__)

# Initialize components
config = RvAndroidToolConfig()
action_service = LLMActionService(config=config)

@app.route('/api/state', methods=['POST'])
def process_state():
    """Process the state and return action recommendations."""
    try:
        state_data = request.json
        actions = action_service.process_state(state_data)
        return jsonify(actions)
    except Exception as e:
        app.logger.error(f"Error processing state: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok"})

def start_server(host='0.0.0.0', port=5000):
    """Start the RVAndroid server."""
    app.run(host=host, port=port)
```

#### 3.3.3 Screen Parser Implementation

The screen parser transforms raw DroidBot state data into structured ScreenDescription objects:

```python
class DroidBotParser(ScreenParser):
    """Parser for DroidBot state data."""
    
    def __init__(self, visitor_class):
        """Initialize the parser with a visitor class."""
        super().__init__(visitor_class)
        self.logger = logging.getLogger("DroidBotParser")
        
    def parse(self, state, static_data=None):
        """Parse the DroidBot state into a ScreenDescription."""
        try:
            # Create basic screen info
            activity = state.get('activity', 'unknown')
            screen = ScreenDescription(activity=activity)
            
            # Process views
            views = state.get('views', [])
            for i, view in enumerate(views):
                # Create ScreenItem for each view
                item = self._create_screen_item(view, i, state)
                if item:
                    screen.add_item(item)
                    
            # Apply visitor for text generation
            if self.visitor_class:
                visitor = self.visitor_class()
                screen.accept(visitor)
                
            return screen
        except Exception as e:
            self.logger.error(f"Error parsing state: {e}")
            return None
            
    def _create_screen_item(self, view, index, state):
        """Create a ScreenItem from a view."""
        # Extract view properties
        resource_id = view.get('resource_id', '')
        text = view.get('text', '')
        view_class = view.get('class', '')
        clickable = view.get('clickable', False)
        enabled = view.get('enabled', True)
        
        # Create item with basic info
        item = ScreenItem(
            view=view,
            index=index,
            base_description=f"{view_class} - '{text}' ({resource_id})"
        )
        
        # Add available actions
        self._add_available_actions(item, view, state)
        
        return item
```

#### 3.3.4 State Enricher Implementation

The state enricher adds contextual information to the application state:

```python
class StateEnricher:
    """Enriches the state with additional information."""
    
    def __init__(self, static_data=None):
        """Initialize the state enricher."""
        self.static_data = static_data
        self.logger = logging.getLogger("StateEnricher")
        
        # Initialize analyzers
        self.screenshot_analyzer = None
        self.pattern_detector = None
        
        # Try to initialize optional components
        try:
            from rvandroid_tool.analysis.screenshot.screenshot_action_complementor import ScreenshotActionComplementor
            self.screenshot_analyzer = ScreenshotActionComplementor(static_data=self.static_data)
        except ImportError:
            self.logger.warning("Screenshot analyzer not available")
            
        try:
            from rvandroid_tool.analysis.patterns.pattern_detector import UIPatternDetectorManager
            self.pattern_detector = UIPatternDetectorManager()
        except ImportError:
            self.logger.warning("UI pattern detector not available")
            
    def enrich_state(self, state):
        """Add additional information to state."""
        try:
            # Process screenshot if available
            if self.screenshot_analyzer and 'screenshot_path' in state:
                self._process_screenshot(state)
                
            # Detect UI patterns
            if self.pattern_detector and 'structured_screen' in state:
                self._detect_ui_patterns(state)
                
            # Add monitored operations information
            if self.static_data:
                self._add_monitored_operations(state)
                
            return state
        except Exception as e:
            self.logger.error(f"Error enriching state: {e}")
            return state
            
    def _process_screenshot(self, state):
        """Process screenshot to extract additional information."""
        if not self.screenshot_analyzer:
            return
            
        screenshot_path = state.get('screenshot_path')
        if screenshot_path:
            try:
                results = self.screenshot_analyzer.analyze(state)
                state['screenshot_info'] = results
            except Exception as e:
                self.logger.error(f"Error processing screenshot: {e}")
                
    def _detect_ui_patterns(self, state):
        """Detect UI patterns in the screen."""
        if not self.pattern_detector:
            return
            
        screen = state.get('structured_screen')
        if screen:
            try:
                patterns = self.pattern_detector.detect_patterns(screen)
                state['ui_patterns'] = patterns
                
                # Add dominant pattern
                dominant = self.pattern_detector.get_dominant_pattern(screen)
                if dominant:
                    pattern_type, pattern_result = dominant
                    state['dominant_pattern'] = {
                        'type': pattern_type.value,
                        'confidence': pattern_result.confidence
                    }
            except Exception as e:
                self.logger.error(f"Error detecting UI patterns: {e}")
                
    def _add_monitored_operations(self, state):
        """Add monitored operations information."""
        if not self.static_data:
            return
            
        activity = state.get('activity', 'unknown')
        try:
            monitored_ops = []
            activity_class = self.static_data.classes.get_class(activity)
            
            if activity_class:
                for method in activity_class.methods:
                    if method.directly_reaches_mop or method.reaches_mop:
                        monitored_ops.append(method.signature)
                        
            if monitored_ops:
                state['monitored_operations'] = monitored_ops
        except Exception as e:
            self.logger.error(f"Error adding monitored operations: {e}")
```

## 4. Data Flow

The data flowing through RVAndroid undergoes several transformations as it moves through the system. This section details the data at each stage of processing.

### 4.1 Input Data

The initial input to RVAndroid is the DroidBot state data:

```
DroidBot State Data
├── state_id: Unique identifier for the state
├── activity: Current activity name
├── views: List of UI elements with properties
│   ├── class: UI element class (e.g., Button, EditText)
│   ├── resource_id: Android resource identifier
│   ├── text: Text content of the element
│   ├── bounds: Element position on screen
│   ├── clickable: Whether element is clickable
│   ├── enabled: Whether element is enabled
│   ├── visible: Whether element is visible
│   └── ...other view properties
├── enabled_actions: List of possible actions
│   ├── action_id: Unique identifier for the action
│   ├── action_type: Type of action (touch, set_text, etc.)
│   ├── view: Target view for the action
│   └── params: Additional parameters for the action
├── screenshot_path: Path to the screenshot image
└── package_name: Application package name
```

### 4.2 Intermediate Data

As the data flows through RVAndroid, it is transformed and enriched:

```
Parsed Screen Description
├── activity: Current activity name
├── items: List of structured UI elements (ScreenItem objects)
│   ├── view: Original view data
│   ├── index: Numeric index
│   ├── base_description: Textual description
│   ├── actions: Available actions for this item
│   │   ├── id: Action identifier
│   │   ├── text: Action description
│   │   ├── type: Action type
│   │   ├── view: Target view
│   │   ├── reaches_mop: Whether action leads to monitored operations
│   │   └── params: Action parameters
│   └── complement: Additional information added by analyzers
└── text_representation: Textual description of the screen
```

```
Enriched State
├── All original DroidBot state data
├── structured_screen: Parsed ScreenDescription
├── screen_description: Textual description of the screen
├── ui_patterns: Detected UI patterns
│   ├── form: Form pattern details
│   ├── list: List pattern details
│   └── ...other patterns
├── dominant_pattern: Most prominent UI pattern
├── screenshot_info: Information extracted from screenshot
└── monitored_operations: Operations that can be triggered
```

```
LLM Prompt
├── system_message: Instructions and context for the LLM
├── user_message: Description of the current state and task
└── messages: Full message history for the conversation
```

### 4.3 Output Data

The final output from RVAndroid is the action recommendation:

```
Action Recommendation
├── actions: List of recommended actions
│   ├── action_id: Identifier matching DroidBot's actions
│   ├── action_type: Type of action to perform
│   ├── view: Target view for the action
│   └── params: Parameters for the action (e.g., text to enter)
└── metadata: Additional information about the decision
    ├── strategy: Strategy used for action selection
    └── reasoning: Explanation of why these actions were chosen
```

## 5. Component Interactions

### 5.1 DroidBot and RVAndroid Server

The interaction between DroidBot and the RVAndroid server is a critical communication channel:

```
DroidBot                                  RVAndroid Server
┌─────────────┐                            ┌─────────────┐
│             │                            │             │
│ RVAndroid   │   1. HTTP POST /api/state  │ Flask       │
│ Policy      ├───────────────────────────►│ Server      │
│             │   {state_data}             │             │
│             │                            │             │
│             │   2. HTTP Response         │             │
│             │◄───────────────────────────┤             │
│             │   {actions}                │             │
└─────────────┘                            └──────┬──────┘
                                                  │
                                                  │
                                                  ▼
                                           ┌─────────────┐
                                           │             │
                                           │ LLM Action  │
                                           │ Service     │
                                           │             │
                                           └─────────────┘
```

Key interactions:
1.  DroidBot's RVAndroid policy sends the current state to the RVAndroid server
2.  The server processes the state and returns action recommendations
3.  DroidBot executes the recommended actions
4.  The cycle repeats with the new state

### 5.2 Screen Parser and State Enricher

The screen parser and state enricher transform raw state data into actionable information:

```
┌─────────────┐                   ┌─────────────┐                   ┌─────────────┐
│             │                   │             │                   │             │
│ DroidBot    │  Raw State Data   │ Screen      │  ScreenDescription│ State       │
│ State       ├──────────────────►│ Parser      ├──────────────────►│ Enricher    │
│             │                   │             │                   │             │
└─────────────┘                   └─────────────┘                   └──────┬──────┘
                                                                           │
                                                                           │
       ┌──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐                   ┌─────────────┐                   ┌─────────────┐
│             │                   │             │                   │             │
│ Pattern     │                   │ Screenshot  │                   │ MOP         │
│ Detector    │◄──────────────────┤ Analyzer    │◄──────────────────┤ Analyzer    │
│             │                   │             │                   │             │
└──────┬──────┘                   └──────┬──────┘                   └──────┬──────┘
       │                                 │                                 │
       └─────────────────────────┬───────┴─────────────────────────┬──────┘
                                 │                                 │
                                 ▼                                 ▼
                          ┌─────────────┐                   ┌─────────────┐
                          │             │                   │             │
                          │ Enriched    │                   │ LLM Action  │
                          │ State       ├──────────────────►│ Service     │
                          │             │                   │             │
                          └─────────────┘                   └─────────────┘
```

Key interactions:
1.  The screen parser converts raw state data into a structured ScreenDescription
2.  The state enricher coordinates multiple analyzers to enrich the state
3.  The pattern detector identifies UI patterns in the screen
4.  The screenshot analyzer processes visual information
5.  The MOP analyzer adds monitored operation information
6.  The enriched state is passed to the LLM Action Service

### 5.3 LLM Action Service and Prompt Framework

The LLM Action Service and Prompt Framework collaborate to generate intelligent testing actions:

```
┌─────────────┐                   ┌─────────────┐                   ┌─────────────┐
│             │                   │             │                   │             │
│ Enriched    │                   │ LLM Action  │                   │ Strategy    │
│ State       ├──────────────────►│ Service     ├──────────────────►│ Registry    │
│             │                   │             │                   │             │
└─────────────┘                   └──────┬──────┘                   └──────┬──────┘
                                         │                                 │
                                         │                                 │
                                         ▼                                 ▼
                                  ┌─────────────┐                   ┌─────────────┐
                                  │             │                   │             │
                                  │ Selected    │◄──────────────────┤ Prompt      │
                                  │ Strategy    │                   │ Strategies  │
                                  │             │                   │             │
                                  └──────┬──────┘                   └─────────────┘
                                         │
                                         │
                                         ▼
┌─────────────┐                   ┌─────────────┐                   ┌─────────────┐
│             │                   │             │                   │             │
│ Information │◄──────────────────┤ Prompt      │                   │ Template    │
│ Manager     │                   │ Framework   ├──────────────────►│ Repository  │
│             │                   │             │                   │             │
└──────┬──────┘                   └──────┬──────┘                   └──────┬──────┘
       │                                 │                                 │
       │                                 │                                 │
       ▼                                 ▼                                 ▼
┌─────────────┐                   ┌─────────────┐                   ┌─────────────┐
│             │                   │             │                   │             │
│ Information │                   │ Language    │                   │ Prompt      │
│ Fragments   │                   │ Model       │                   │ Templates   │
│             │                   │             │                   │             │
└─────────────┘                   └──────┬──────┘                   └─────────────┘
                                         │
                                         │
                                         ▼
                                  ┌─────────────┐
                                  │             │
                                  │ LLM         │
                                  │ Response    │
                                  │             │
                                  └──────┬──────┘
                                         │
                                         │
                                         ▼
                                  ┌─────────────┐
                                  │             │
                                  │ Action      │
                                  │ Recommendation│
                                  │             │
                                  └─────────────┘
```

Key interactions:
1.  The LLM Action Service selects an appropriate strategy based on the state
2.  The selected strategy coordinates the prompt generation process
3.  The information manager collects relevant information from fragments
4.  The template repository provides prompt templates
5.  The prompt framework assembles the final prompt
6.  The language model generates a response
7.  The response is parsed into action recommendations

## 6. Integration with DroidBot

### 6.1 DroidBot Architecture

DroidBot follows an event-based architecture with several key components:

1.  **DeviceBridge**: Interfaces with the Android device (real or emulated)
2.  **App**: Represents the application under test
3.  **Policy**: Implements the testing strategy
4.  **InputManager**: Handles input event generation and execution
5.  **StateManager**: Tracks and manages application states
6.  **EventManager**: Coordinates event generation and execution

### 6.2 RVAndroid Policy Integration

RVAndroid integrates with DroidBot through a custom policy implementation:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                        DroidBot                         │
│                                                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐           │
│  │            │ │            │ │            │           │
│  │ App        │ │ Device     │ │ State      │           │
│  │            │ │ Bridge     │ │ Manager    │           │
│  └────────────┘ └────────────┘ └────────────┘           │
│         │             │              │                  │
│         │             │              │                  │
│         ▼             ▼              ▼                  │
│  ┌────────────────────────────────────────────────┐     │
│  │                                                │     │
│  │               Event Manager                    │     │
│  │                                                │     │
│  └───────────────────────┬────────────────────────┘     │
│                          │                              │
│                          │                              │
│                          ▼                              │
│  ┌────────────────────────────────────────────────┐     │
│  │                 Policies                        │     │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐   │     │
│  │ │            │ │            │ │            │   │     │
│  │ │ Random     │ │ UTG        │ │ RVAndroid  │───┼─────┼────────►
│  │ │ Policy     │ │ Policy     │ │ Policy     │   │     │
│  │ │            │ │            │ │            │   │     │
│  │ └────────────┘ └────────────┘ └────────────┘   │     │
│  │                                                │     │
│  └────────────────────────────────────────────────┘     │
│                                                         │
└─────────────────────────────────────────────────────────┘
                                                               ┌─────────────────────┐
                                                               │                     │
                                                               │    RVAndroid        │
                                                               │    Server           │
                                                               │                     │
                                                               └─────────────────────┘
```

The RVAndroid policy is integrated into DroidBot's policy framework, allowing it to be selected and used like any other policy:

```python
# Command line usage:
# python -m droidbot -a app.apk -o output_dir -policy rvandroid -server_url http://localhost:5000
```

### 6.3 Policy Implementation Details

The RVAndroid policy extends DroidBot's base Policy class:

```python
class RVAndroidPolicy(Policy):
    """A policy that uses RVAndroid server for intelligent action decisions."""
    
    def __init__(self, device, app, server_url="http://localhost:5000"):
        """Initialize the RVAndroid policy."""
        super(RVAndroidPolicy, self).__init__(device, app)
        self.server_url = server_url
        self.session = requests.Session()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("RVAndroid policy initialized with server URL: %s", server_url)
        
        # Test server connection
        try:
            response = self.session.get(f"{self.server_url}/health")
            if response.status_code == 200:
                self.logger.info("Successfully connected to RVAndroid server")
            else:
                self.logger.warning("RVAndroid server returned status code %d", response.status_code)
        except Exception as e:
            self.logger.warning("Failed to connect to RVAndroid server: %s", str(e))
```

Key Methods:

1.  **Generate Method**: Produces the next action to execute
    ```python
    def generate(self, current_state):
        """Generate the next action based on the current state."""
        if current_state is None:
            return None
           
        # Get state and process with RVAndroid
        state_data = self.prepare_state_data(current_state)
        response = self.send_state_to_server(state_data)
        action = self.parse_response(response, current_state)
       
        # Fall back to random if RVAndroid fails
        if action is None:
            self.logger.warning("Falling back to random action selection")
            return self.random_policy.generate(current_state)
           
        return action
    ```

2.  **State Preparation**: Formats the state for the server
    ```python
    def prepare_state_data(self, state):
        """Prepare the state data for sending to the server."""
        views = state.views or []
        enabled_actions = self.get_enabled_actions(state)
       
        # Basic state data
        state_data = {
            'state_id': state.state_id,
            'package_name': self.app.package_name,
            'activity': state.foreground_activity,
            'views': views,
            'enabled_actions': enabled_actions,
            'timestamp': time.time()
        }
       
        # Add screenshot if available
        if state.screenshot_path:
            state_data['screenshot_path'] = state.screenshot_path
           
        return state_data
    ```

3.  **Server Communication**: Handles the interaction with the RVAndroid server
    ```python
    def send_state_to_server(self, state_data):
        """Send the state data to the RVAndroid server."""
        try:
            response = self.session.post(
                f"{self.server_url}/api/state",
                json=state_data,
                timeout=30
            )
           
            if response.status_code == 200:
                return response.json()
               
            self.logger.warning(
                "RVAndroid server returned status code %d: %s",
                response.status_code,
                response.text
            )
            return None
        except Exception as e:
            self.logger.error("Error communicating with RVAndroid server: %s", str(e))
            return None
    ```

4.  **Response Parsing**: Converts server responses into DroidBot actions
    ```python
    def parse_response(self, response, current_state):
        """Parse the response from the RVAndroid server."""
        if not response or 'actions' not in response or not response['actions']:
            return None
           
        try:
            # Get the first action (DroidBot executes one at a time)
            action_data = response['actions'][0]
            action_id = action_data.get('action_id')
           
            # Find the corresponding action in enabled actions
            for action in current_state.get_possible_input():
                if hasattr(action, 'action_id') and action.action_id == action_id:
                    return action
                   
            # If not found, try to create a new action
            return self.create_action_from_data(action_data, current_state)
        except Exception as e:
            self.logger.error("Error parsing response: %s", str(e))
            return None
    ```

## 7. Configuration System

### 7.1 Configuration Options

RVAndroid can be configured through several mechanisms:

1.  **JSON Configuration File**: Primary configuration method
2.  **Command Line Arguments**: Overrides for file-based configuration
3.  **Environment Variables**: System-wide settings

Main configuration options include:

1.  **Server Settings**:
    - `server.host`: Host address for the RVAndroid server
    - `server.port`: Port number for the RVAndroid server
    - `server.log_level`: Logging level for server operations

2.  **LLM Configuration**:
    - `llm.provider`: LLM provider (ollama, huggingface, etc.)
    - `llm.model`: Model name to use (llama3, etc.)
    - `llm.temperature`: Temperature for generation
    - `llm.max_tokens`: Maximum tokens to generate
    - `llm.api_key`: API key for cloud-based providers

3.  **Strategy Settings**:
    - `strategy.default`: Default prompt strategy to use
    - `strategy.use_batch`: Whether to use batch action strategies
    - `strategy.min_batch_size`: Minimum actions in a batch
    - `strategy.max_batch_size`: Maximum actions in a batch

4.  **Parser Configuration**:
    - `parser.type`: Parser type to use (droidbot, uiautomator)
    - `parser.visitor`: Visitor class for text generation

5.  **Enrichment Options**:
    - `enrichment.use_screenshots`: Whether to use screenshot analysis
    - `enrichment.use_patterns`: Whether to use UI pattern detection
    - `enrichment.use_mop`: Whether to use monitored operations information

### 7.2 Configuration Example

A typical configuration file might look like:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 5000,
    "log_level": "INFO"
  },
  "llm": {
    "provider": "ollama",
    "model": "llama3",
    "temperature": 0.3,
    "max_tokens": 800,
    "base_url": "http://localhost:11434"
  },
  "strategy": {
    "default": "single",
    "use_batch": true,
    "min_batch_size": 3,
    "max_batch_size": 10
  },
  "parser": {
    "type": "droidbot",
    "visitor": "basic"
  },
  "enrichment": {
    "use_screenshots": true,
    "use_patterns": true,
    "use_mop": true
  }
}
```

### 7.3 Component Configurator

The configuration is managed through the `RvAndroidToolConfig` class, which provides a central point for component configuration.

## 8. Deployment

### 8.1 Running RVAndroid

To deploy and run RVAndroid, follow these steps:

1.  **Start the RVAndroid Server**:
    ```bash
    # Start the server
    python -m rvandroid_tool.server --port 5000
    ```

2.  **Run DroidBot with RVAndroid Policy**:
    ```bash
    # Run DroidBot with RVAndroid policy
    python -m droidbot -a app.apk -o output_dir -policy rvandroid -server_url http://localhost:5000
    ```

3.  **View Results**: DroidBot will generate results in the specified output directory.

### 8.2 Docker Deployment

RVAndroid can also be deployed using Docker:

```bash
# Build the Docker image
docker build -t rvandroid -f docker/rvandroid/Dockerfile .

# Run the RVAndroid server
docker run -p 5000:5000 rvandroid
```

DroidBot can then connect to the containerized RVAndroid server.

### 8.3 Integration with RV-Android Platform

RVAndroid integrates with the RV-Android platform through the tools registry:

```python
# Register RVAndroid tool
from rv_android.tools.registry import ToolRegistry
from rvandroid_tool.tools.rvandroid.tool import RVAndroidTool

ToolRegistry.register(RVAndroidTool())
```

This allows RVAndroid to be used as a testing tool within the RV-Android platform.

## 9. Conclusion

RVAndroid combines DroidBot's exploratory capabilities with language model decision-making for Android application testing. By structuring application state information and providing it to LLMs in a consistent format, RVAndroid enables testing that can identify issues traditional testing tools might miss.

The system's modular architecture allows for extension and improvement, while its integration with DroidBot ensures compatibility with existing testing workflows. The tool is positioned to leverage improvements in language model capabilities for application testing.

For more detailed information about the LLM integration architecture, please refer to [docs/rv_llm_architecture.md](rv_llm_architecture.md).

## Appendix: DroidBot Integration

The integration between `rvandroid-tool` and DroidBot is facilitated by a custom DroidBot policy, `RVAndroidPolicy`. This policy acts as a client to the `rvandroid-tool` server, enabling LLM-driven test generation within the DroidBot framework.

### `RVAndroidPolicy`

The `RVAndroidPolicy` is a subclass of DroidBot's `UtgBasedInputPolicy`. Its primary responsibility is to override the `generate_event` method. Instead of using a local strategy to decide the next action, it communicates with the `rvandroid-tool` server.

The policy performs the following steps:

1.  **State Preparation**: It captures the current state of the application from DroidBot and prepares it in a JSON format that the `rvandroid-tool` server can understand. This includes the view hierarchy, foreground activity, and other relevant information.

2.  **Server Communication**: It sends the prepared state to the `/api/get_actions` endpoint of the `rvandroid-tool` server via an HTTP POST request.

3.  **Response Handling**: It receives a list of recommended actions from the server. The policy is designed to handle both single-action and batch-action responses.

4.  **Event Generation**: It converts the received action(s) into DroidBot `InputEvent` objects. If the server returns a batch of actions, the policy creates a `CompoundEvent` that wraps all the individual events.

5.  **Fallback Mechanism**: If the communication with the server fails, or if the server returns no valid actions, the policy falls back to a default DroidBot policy, such as `UtgGreedySearchPolicy`.

### Server-Side Handling

The `rvandroid-tool` server, implemented in `rvandroid_tool/server.py`, listens for requests from the `RVAndroidPolicy`. When a request is received at the `/api/get_actions` endpoint, the server delegates the processing to the `LLMActionService`. This service uses the prompt framework and the configured LLM to analyze the state and generate a list of actions, which are then sent back to the `RVAndroidPolicy`.

### Running with DroidBot

To use the `RVAndroidPolicy`, DroidBot must be started with the `-policy rvandroid` command-line argument. The URL of the `rvandroid-tool` server can be specified with the `-server_url` argument. For example:

```bash
python -m droidbot.start -a <path_to_apk> -o <output_dir> -policy rvandroid -server_url http://localhost:5000/api/get_actions
```

This command instructs DroidBot to use the `RVAndroidPolicy`, which will then communicate with the `rvandroid-tool` server at the specified URL to get its testing actions.