"""
ReactEngine Prototype for Tool-Calling Validation.

Simplified ReactEngine implementation to test LangChain + Ollama tool-calling
architecture without full RVAgent dependencies.
"""
import time
import logging
from typing import Dict, Any, List
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama

from ..tools.mock_tools import get_mock_tools, get_mock_ui_state


class PrototypeReactEngine:
    """
    Simplified ReAct Engine for tool-calling validation.

    Tests:
    - LangChain + Ollama integration
    - Tool-calling with qwen2.5vl:7b
    - AgentExecutor with Android tools
    - ReAct pattern with mock UI state
    """

    def __init__(self, model: str = "qwen2.5vl:7b", temperature: float = 0.25):
        self.model = model
        self.temperature = temperature
        self.logger = logging.getLogger("rv_agent.prototype.react_engine")

        # Initialize mock tools
        self.tools = get_mock_tools()
        self.logger.info(f"[PROTOTYPE] Initialized with {len(self.tools)} mock tools")

        # Initialize LLM with Phase 0 validated parameters
        try:
            self.llm = ChatOllama(
                model=model,
                temperature=temperature,
                top_p=0.8,               # Phase 0 validated
                top_k=50,                # Phase 0 validated
                max_tokens=800,
                base_url="http://localhost:11434"
            )
            self.logger.info(f"[PROTOTYPE] LLM initialized: {model} (temp: {temperature})")
        except Exception as e:
            self.logger.error(f"[PROTOTYPE] Failed to initialize LLM: {e}")
            raise

        # Create ReAct prompt template
        self.prompt_template = self._create_react_prompt()

        # Create LangChain ReAct agent
        try:
            self.agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=self.prompt_template
            )
            self.logger.info("[PROTOTYPE] ReAct agent created successfully")
        except Exception as e:
            self.logger.error(f"[PROTOTYPE] Failed to create ReAct agent: {e}")
            raise

        # Create agent executor
        try:
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=3,  # Keep short for prototype
                early_stopping_method="generate",
                return_intermediate_steps=True
            )
            self.logger.info("[PROTOTYPE] AgentExecutor created successfully")
        except Exception as e:
            self.logger.error(f"[PROTOTYPE] Failed to create AgentExecutor: {e}")
            raise

    def _create_react_prompt(self) -> ChatPromptTemplate:
        """Create ReAct prompt template optimized for tool-calling prototype."""
        return ChatPromptTemplate.from_messages([
            ("system", """You are an Android testing agent prototype using ReAct pattern with tool-calling.

GOAL: Test the Android application by using available tools to interact with UI elements.

COORDINATE ENHANCEMENT (Phase 0 validated - CRITICAL for success):
- Always use explicit coordinates when available from UI descriptions
- Format: "at position (x, y)" is CRITICAL for success

AVAILABLE TOOLS:
- android_click: Click on elements using coordinates
- android_input: Input text into fields
- android_scroll: Scroll to reveal content
- android_back: Navigate back

TESTING STRATEGY:
1. ANALYZE the current screen and UI elements
2. REASON about which [UNTESTED] elements to interact with first
3. ACT by calling appropriate tools with coordinates from the UI description
4. Focus on [UNTESTED] elements for systematic coverage

IMPORTANT: Use exact coordinates provided in the UI element descriptions."""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

    def test_single_tool_call(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Test a single tool call directly."""
        try:
            self.logger.info(f"[PROTOTYPE] Testing single tool call: {tool_name}")

            # Find the tool
            tool = None
            for t in self.tools:
                if t.name == tool_name:
                    tool = t
                    break

            if not tool:
                return {"success": False, "error": f"Tool {tool_name} not found"}

            # Execute tool
            start_time = time.time()
            result = tool._run(**kwargs)
            execution_time = time.time() - start_time

            return {
                "success": True,
                "tool_name": tool_name,
                "result": result,
                "execution_time": execution_time,
                "kwargs": kwargs
            }

        except Exception as e:
            self.logger.error(f"[PROTOTYPE] Single tool test failed: {e}")
            return {"success": False, "error": str(e)}

    def test_react_cycle(self, custom_input: str = None) -> Dict[str, Any]:
        """Test full ReAct cycle with mock UI state."""
        try:
            # Use mock UI state or custom input
            if custom_input is None:
                ui_state = get_mock_ui_state()
                input_text = f"Here is the current Android screen:\n\n{ui_state}\n\nPlease analyze the screen and perform one or two testing actions on [UNTESTED] elements."
            else:
                input_text = custom_input

            self.logger.info("[PROTOTYPE] Starting ReAct cycle test")
            self.logger.debug(f"[PROTOTYPE] Input: {input_text[:100]}...")

            # Execute ReAct cycle
            start_time = time.time()
            result = self.agent_executor.invoke({"input": input_text})
            execution_time = time.time() - start_time

            # Extract results
            cycle_result = {
                "success": True,
                "execution_time": execution_time,
                "final_output": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
                "tool_calls_count": len(result.get("intermediate_steps", [])),
                "input_length": len(input_text)
            }

            self.logger.info(f"[PROTOTYPE] ReAct cycle completed in {execution_time:.2f}s")
            self.logger.info(f"[PROTOTYPE] Tool calls executed: {cycle_result['tool_calls_count']}")

            return cycle_result

        except Exception as e:
            self.logger.error(f"[PROTOTYPE] ReAct cycle test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": 0,
                "tool_calls_count": 0
            }

    def test_tool_calling_flow(self) -> Dict[str, Any]:
        """Test complete tool-calling flow with multiple scenarios."""
        results = {
            "overall_success": True,
            "tests": [],
            "summary": {}
        }

        # Test 1: Individual tool calls
        self.logger.info("[PROTOTYPE] Testing individual tools...")

        tool_tests = [
            {"name": "android_click", "kwargs": {"coordinates": "245,678", "element_description": "login button"}},
            {"name": "android_input", "kwargs": {"text": "testuser@example.com", "coordinates": "300,450"}},
            {"name": "android_scroll", "kwargs": {"direction": "down", "distance": "medium"}},
            {"name": "android_back", "kwargs": {}}
        ]

        for test in tool_tests:
            result = self.test_single_tool_call(test["name"], **test["kwargs"])
            results["tests"].append({
                "type": "single_tool",
                "tool": test["name"],
                "result": result
            })
            if not result["success"]:
                results["overall_success"] = False

        # Test 2: Full ReAct cycle
        self.logger.info("[PROTOTYPE] Testing full ReAct cycle...")
        react_result = self.test_react_cycle()
        results["tests"].append({
            "type": "react_cycle",
            "result": react_result
        })
        if not react_result["success"]:
            results["overall_success"] = False

        # Generate summary
        successful_tools = sum(1 for test in results["tests"] if test.get("result", {}).get("success", False))
        total_tests = len(results["tests"])

        results["summary"] = {
            "total_tests": total_tests,
            "successful_tests": successful_tools,
            "success_rate": successful_tools / total_tests if total_tests > 0 else 0,
            "model_used": self.model,
            "temperature": self.temperature,
            "tools_available": len(self.tools)
        }

        return results

    def run_interactive_test(self):
        """Run interactive test session."""
        print("\n" + "="*60)
        print("🧪 RVAgent Tool-Calling Prototype")
        print("="*60)
        print(f"Model: {self.model}")
        print(f"Tools available: {len(self.tools)}")
        print(f"Temperature: {self.temperature}")
        print()

        while True:
            print("\nOptions:")
            print("1. Test single tool call")
            print("2. Test ReAct cycle with mock UI")
            print("3. Test ReAct cycle with custom input")
            print("4. Run full validation test")
            print("5. Exit")

            choice = input("\nChoose option (1-5): ").strip()

            if choice == "1":
                print("\nAvailable tools:")
                for i, tool in enumerate(self.tools):
                    print(f"  {i+1}. {tool.name}")

                tool_choice = input("Choose tool number: ").strip()
                try:
                    tool_idx = int(tool_choice) - 1
                    tool = self.tools[tool_idx]
                    print(f"\nTesting {tool.name}...")

                    # Simple test parameters
                    if tool.name == "android_click":
                        result = self.test_single_tool_call("android_click", coordinates="245,678", element_description="test button")
                    elif tool.name == "android_input":
                        result = self.test_single_tool_call("android_input", text="test input", coordinates="300,450")
                    elif tool.name == "android_scroll":
                        result = self.test_single_tool_call("android_scroll", direction="down")
                    elif tool.name == "android_back":
                        result = self.test_single_tool_call("android_back")

                    print(f"Result: {result}")

                except (ValueError, IndexError):
                    print("Invalid tool selection")

            elif choice == "2":
                print("\nTesting ReAct cycle with mock UI...")
                result = self.test_react_cycle()
                print(f"Success: {result['success']}")
                print(f"Execution time: {result.get('execution_time', 0):.2f}s")
                print(f"Tool calls: {result.get('tool_calls_count', 0)}")
                print(f"Final output: {result.get('final_output', 'No output')[:200]}...")

            elif choice == "3":
                custom_input = input("\nEnter custom input for ReAct cycle: ")
                result = self.test_react_cycle(custom_input)
                print(f"Success: {result['success']}")
                print(f"Final output: {result.get('final_output', 'No output')}")

            elif choice == "4":
                print("\nRunning full validation test...")
                results = self.test_tool_calling_flow()
                print("\n" + "="*40)
                print("VALIDATION RESULTS")
                print("="*40)
                print(f"Overall success: {results['overall_success']}")
                print(f"Success rate: {results['summary']['success_rate']:.1%}")
                print(f"Tests passed: {results['summary']['successful_tests']}/{results['summary']['total_tests']}")

                for test in results['tests']:
                    test_type = test['type']
                    success = test['result']['success']
                    print(f"  {test_type}: {'✅' if success else '❌'}")

            elif choice == "5":
                print("\n👋 Goodbye!")
                break

            else:
                print("Invalid option")