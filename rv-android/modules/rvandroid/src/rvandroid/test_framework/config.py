"""
Test framework configuration module.

This module provides configuration classes for the test framework
that evaluates different configurations of RVAndroid and RVDroid tools.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional

# Import LLM implementations for constants
try:
    # Try to import MCP-based implementations first
    from rv_android_core.mcp.adapters.ollama_adapter import OllamaAdapter
    from rv_android_core.mcp.adapters.dspy_adapter import DSPyAdapter
    USE_MCP = True
except ImportError:
    # Fall back to legacy implementations if necessary
    from rv_android_core.llm.ollama_llm import OllamaLLM
    from rv_android_core.llm.huggingface_llm import HuggingFaceLLM
    from rv_android_core.llm.dspy_llm import DSPyLLM
    USE_MCP = False


@dataclass
class ToolConfiguration:
    """
    Configuration for a testing tool.
    
    Represents settings for a specific testing tool (RVAndroid or RVDroid),
    including parameters for LLM, parsing strategy, etc.
    
    Uses the Model Context Protocol (MCP) for standardized LLM interactions.
    """
    # Basic settings
    tool_name: str
    timeout: int = 300  # in seconds

    # Emulator configuration
    # TODO voltar para true
    no_window: bool = False  # Whether to run emulator in headless mode

    # LLM configuration using MCP-compatible types
    llm_type: str = "ollama"  # ollama, dspy, etc.
    llm_model: str = "llama3.2:3b"  # Based on available MCP-compatible models
    temperature: float = 0.2
    max_tokens: int = 800
    
    # MCP-specific configuration
    use_mcp: bool = True  # Use MCP for all LLM operations
    mcp_config: Dict[str, Any] = field(default_factory=dict)

    # Strategy configuration
    # Options: single_action_strategy, flow_based_batch_strategy, composable_strategy
    strategy_type: str = "single_action_strategy"
    strategy_params: Dict[str, Any] = field(default_factory=dict)

    # Parser configuration
    parser_type: str = "uiautomator"  # Default for RVDroid
    parser_params: Dict[str, Any] = field(default_factory=dict)

    # Visitor configuration
    # Options: basic, enhanced, detailed
    visitor_type: str = "enhanced"
    visitor_params: Dict[str, Any] = field(default_factory=dict)

    # Static analysis configuration
    use_static_analysis: bool = True
    static_analysis_level: str = "detailed"  # basic, standard, detailed

    # Screenshot analysis configuration
    use_screenshot_analysis: bool = True
    screenshot_analysis_level: str = "standard"  # basic, standard, detailed

    # Monitored operations configuration
    monitored_operations_focus: bool = True  # Whether to focus on monitored operations
    monitored_operations_priority: str = "high"  # high, medium, low

    # Extra params
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolConfiguration':
        """Create from dictionary."""
        # Extract specific fields
        tool_name = data.pop('tool_name')
        timeout = data.pop('timeout', 300)

        # Extract emulator settings
        no_window = data.pop('no_window', True)

        # Extract LLM settings
        llm_type = data.pop('llm_type', 'ollama')
        llm_model = data.pop('llm_model', 'llama3.2:3b')
        temperature = data.pop('temperature', 0.2)
        max_tokens = data.pop('max_tokens', 800)
        
        # Extract MCP settings
        use_mcp = data.pop('use_mcp', True)
        mcp_config = data.pop('mcp_config', {})

        # Extract strategy settings
        strategy_type = data.pop('strategy_type', 'single_action_strategy')
        strategy_params = data.pop('strategy_params', {})

        # Extract parser settings
        parser_type = data.pop('parser_type', 'uiautomator')
        parser_params = data.pop('parser_params', {})

        # Extract visitor settings
        visitor_type = data.pop('visitor_type', 'enhanced')
        visitor_params = data.pop('visitor_params', {})

        # Extract static analysis settings
        use_static_analysis = data.pop('use_static_analysis', True)
        static_analysis_level = data.pop('static_analysis_level', 'detailed')

        # Extract screenshot analysis settings
        use_screenshot_analysis = data.pop('use_screenshot_analysis', True)
        screenshot_analysis_level = data.pop('screenshot_analysis_level', 'standard')
        
        # Extract monitored operations settings
        monitored_operations_focus = data.pop('monitored_operations_focus', True)
        monitored_operations_priority = data.pop('monitored_operations_priority', 'high')

        # Remaining settings go to extra_params
        extra_params = data

        return cls(
            tool_name=tool_name,
            timeout=timeout,
            no_window=no_window,
            llm_type=llm_type,
            llm_model=llm_model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_mcp=use_mcp,
            mcp_config=mcp_config,
            strategy_type=strategy_type,
            strategy_params=strategy_params,
            parser_type=parser_type,
            parser_params=parser_params,
            visitor_type=visitor_type,
            visitor_params=visitor_params,
            use_static_analysis=use_static_analysis,
            static_analysis_level=static_analysis_level,
            use_screenshot_analysis=use_screenshot_analysis,
            screenshot_analysis_level=screenshot_analysis_level,
            monitored_operations_focus=monitored_operations_focus,
            monitored_operations_priority=monitored_operations_priority,
            extra_params=extra_params
        )

    def get_id(self) -> str:
        """Generate a unique identifier for this configuration."""
        return (f"{self.tool_name}_{self.llm_type}_{self.llm_model.replace(':', '-')}_"
                f"{self.strategy_type}_{self.parser_type}_{self.visitor_type}_"
                f"sa-{self.static_analysis_level if self.use_static_analysis else 'off'}_"
                f"ss-{self.screenshot_analysis_level if self.use_screenshot_analysis else 'off'}_"
                f"{'headless' if self.no_window else 'windowed'}")


@dataclass
class TestSuite:
    """
    A test suite defining a set of configurations to test.
    
    Represents a collection of test configurations to be evaluated
    across a set of applications.
    """
    name: str
    description: str = ""
    tool_configurations: List[ToolConfiguration] = field(default_factory=list)
    apps: List[str] = field(default_factory=list)  # TODO mudar nome, eh o diretorio (ou list de diretorios) que contem os apks (e seus arquivos de analise estatica)
    output_dir: str = "test_results"
    repetitions: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'tool_configurations': [tc.to_dict() for tc in self.tool_configurations],
            'apps': self.apps,
            'output_dir': self.output_dir,
            'repetitions': self.repetitions
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestSuite':
        """Create from dictionary."""
        tool_configs = [
            ToolConfiguration.from_dict(tc)
            for tc in data.get('tool_configurations', [])
        ]

        return cls(
            name=data.get('name', 'Unnamed Test Suite'),
            description=data.get('description', ''),
            tool_configurations=tool_configs,
            apps=data.get('apps', []),
            output_dir=data.get('output_dir', 'test_results'),
            repetitions=data.get('repetitions', 1)
        )

    def save_to_file(self, filepath: str) -> None:
        """
        Save to JSON file.
        
        Args:
            filepath: Path where to save the file
        """
        # Handle empty or None filepath
        if not filepath:
            filepath = "test_suite_config.json"

        # Create directory if needed (only if there's a directory part)
        dirname = os.path.dirname(filepath)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        # Save the file
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> 'TestSuite':
        """Load from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def get_test_cases(self) -> List['TestCase']:
        """Generate all test cases from the test suite."""
        test_cases = []

        for app_path in self.apps:
            for config in self.tool_configurations:
                for rep in range(1, self.repetitions + 1):
                    test_cases.append(TestCase(
                        app_path=app_path,
                        tool_config=config,
                        repetition=rep,
                        output_dir=self.output_dir
                    ))

        return test_cases


@dataclass
class TestCase:
    """
    A single test case combining a specific tool configuration with an app.
    
    Represents an individual test to be executed, combining a specific
    tool configuration with a target application.
    """
    app_path: str
    tool_config: ToolConfiguration
    repetition: int = 1
    output_dir: str = ""

    def get_id(self) -> str:
        """Generate a unique identifier for this test case."""
        app_name = os.path.basename(self.app_path).split('.')[0]
        config_id = self.tool_config.get_id()
        return f"{app_name}_{config_id}_r{self.repetition}"

    def get_result_dir(self) -> str:
        """Get the directory for the test results."""
        return os.path.join(self.output_dir, self.get_id())


def create_default_configurations() -> List[ToolConfiguration]:
    """
    Create a set of diverse configurations to test various aspects of LLM and analysis.
    
    This is a legacy function that has been replaced by the ConfigurationGenerator.
    It now delegates to the new implementation for better validation and flexibility.
    
    Returns:
        List of tool configurations
    """
    from rv_android_core.test_framework.config_generator import ConfigurationGenerator

    generator = ConfigurationGenerator()

    # Generate a comparative set with various configurations
    # llm_types = [OllamaLLM.NAME, HuggingFaceLLM.NAME, DSPyLLM.NAME]
    # models = {
    #     OllamaLLM.NAME: OllamaLLM.MODELS,
    #     HuggingFaceLLM.NAME: HuggingFaceLLM.MODELS,
    #     DSPyLLM.NAME: DSPyLLM.MODELS
    # }
    llm_types = [OllamaLLM.NAME, DSPyLLM.NAME]
    models = {
        OllamaLLM.NAME: OllamaLLM.MODELS,
        DSPyLLM.NAME: DSPyLLM.MODELS
    }
    strategy_types = ["basic", "single_action", "dspy", "dspy_single_action", "composable", "composable_single_action"]
    visitor_types = ["basic", "default", "detailed"]

    configurations = generator.generate_all_combinations(
        llm_types=llm_types,
        models=models,
        strategy_types=strategy_types,
        visitor_types=visitor_types
    )

    return configurations


def create_default_test_suite() -> TestSuite:
    """
    Create a default test suite with various configurations for testing.
    
    Uses the ConfigurationGenerator to create a diverse set of configurations.
    
    Returns:
        TestSuite with diverse configurations
    """
    from rv_android_core.test_framework.config_generator import create_comparative_test_suite

    return create_comparative_test_suite()
