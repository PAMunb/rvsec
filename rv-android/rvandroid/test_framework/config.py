"""
Test framework configuration module.

This module provides configuration classes for the test framework
that evaluates different configurations of RVAndroid and RVDroid tools.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set, Union


@dataclass
class ToolConfiguration:
    """
    Configuration for a testing tool.
    
    Represents settings for a specific testing tool (RVAndroid or RVDroid),
    including parameters for LLM, parsing strategy, etc.
    """
    # Basic settings
    tool_name: str
    timeout: int = 300  # in seconds
    
    # LLM configuration
    llm_type: str = "ollama"
    llm_model: str = "llama3.2:3b"
    temperature: float = 0.2
    max_tokens: int = 800
    
    # Strategy configuration
    strategy_type: str = "composable_single_action"
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    # Parser configuration
    parser_type: str = "droidbot"
    parser_params: Dict[str, Any] = field(default_factory=dict)
    
    # Visitor configuration
    visitor_type: str = "enhanced"
    visitor_params: Dict[str, Any] = field(default_factory=dict)
    
    # Static analysis configuration
    use_static_analysis: bool = True
    static_analysis_level: str = "detailed"  # basic, standard, detailed
    
    # Screenshot analysis configuration
    use_screenshot_analysis: bool = False
    screenshot_analysis_level: str = "standard"  # basic, standard, detailed
    
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
        
        # Extract LLM settings
        llm_type = data.pop('llm_type', 'ollama')
        llm_model = data.pop('llm_model', 'llama3.2:3b')
        temperature = data.pop('temperature', 0.2)
        max_tokens = data.pop('max_tokens', 800)
        
        # Extract strategy settings
        strategy_type = data.pop('strategy_type', 'composable_single_action')
        strategy_params = data.pop('strategy_params', {})
        
        # Extract parser settings
        parser_type = data.pop('parser_type', 'droidbot')
        parser_params = data.pop('parser_params', {})
        
        # Extract visitor settings
        visitor_type = data.pop('visitor_type', 'enhanced')
        visitor_params = data.pop('visitor_params', {})
        
        # Extract static analysis settings
        use_static_analysis = data.pop('use_static_analysis', True)
        static_analysis_level = data.pop('static_analysis_level', 'detailed')
        
        # Extract screenshot analysis settings
        use_screenshot_analysis = data.pop('use_screenshot_analysis', False)
        screenshot_analysis_level = data.pop('screenshot_analysis_level', 'standard')
        
        # Remaining settings go to extra_params
        extra_params = data
        
        return cls(
            tool_name=tool_name,
            timeout=timeout,
            llm_type=llm_type,
            llm_model=llm_model,
            temperature=temperature,
            max_tokens=max_tokens,
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
            extra_params=extra_params
        )

    def get_id(self) -> str:
        """Generate a unique identifier for this configuration."""
        return (f"{self.tool_name}_{self.llm_type}_{self.llm_model.replace(':', '-')}_"
                f"{self.strategy_type}_{self.parser_type}_{self.visitor_type}_"
                f"sa-{self.static_analysis_level if self.use_static_analysis else 'off'}_"
                f"ss-{self.screenshot_analysis_level if self.use_screenshot_analysis else 'off'}")


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
    apps: List[str] = field(default_factory=list)
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
        """Save to JSON file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
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
    """Create a set of diverse configurations to test various aspects of LLM and analysis."""
    configurations = []
    
    # Different LLM providers
    llm_types = ["ollama", "huggingface", "dspy", "langchain", "frontier"]
    
    # Different LLM models by provider
    llm_models = {
        "ollama": ["llama3.2:3b", "gemma3:4b", "phi3.5:3.8b"],
        "huggingface": ["meta-llama/Meta-Llama-3.1-8B-Instruct"],
        "dspy": ["meta-llama/Meta-Llama-3.1-8B-Instruct"],
        "langchain": ["meta-llama/Meta-Llama-3.1-8B-Instruct"],
        "frontier": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"]
    }
    
    # Different prompt strategies
    strategy_types = [
        "basic", 
        "single_action", 
        "composable_single_action", 
        "dspy_single_action", 
        "composable"
    ]
    
    # Different parsers
    parser_types = ["droidbot", "uiautomator"]
    
    # Different visitors
    visitor_types = ["basic", "enhanced", "detailed"]
    
    # Static analysis levels
    static_analysis_levels = ["basic", "standard", "detailed"]
    
    # Screenshot analysis
    screenshot_options = [True, False]
    screenshot_levels = ["basic", "standard", "detailed"]
    
    # Create default RVAndroid configurations
    for llm_type in llm_types[:2]:  # Limit to first 2 LLM types for simplicity
        for model in llm_models[llm_type][:1]:  # Take first model of each type
            for strategy in strategy_types[:3]:  # Take first 3 strategies
                for parser in parser_types:
                    for visitor in visitor_types:
                        for use_static in [True]:  # Always use static analysis
                            for static_level in static_analysis_levels[:2]:  # First 2 levels
                                for use_screenshot in screenshot_options:
                                    if use_screenshot:
                                        for ss_level in screenshot_levels[:1]:  # Just first level
                                            configurations.append(ToolConfiguration(
                                                tool_name="rvandroid",
                                                llm_type=llm_type,
                                                llm_model=model,
                                                strategy_type=strategy,
                                                parser_type=parser,
                                                visitor_type=visitor,
                                                use_static_analysis=use_static,
                                                static_analysis_level=static_level,
                                                use_screenshot_analysis=use_screenshot,
                                                screenshot_analysis_level=ss_level
                                            ))
                                    else:
                                        configurations.append(ToolConfiguration(
                                            tool_name="rvandroid",
                                            llm_type=llm_type,
                                            llm_model=model,
                                            strategy_type=strategy,
                                            parser_type=parser,
                                            visitor_type=visitor,
                                            use_static_analysis=use_static,
                                            static_analysis_level=static_level,
                                            use_screenshot_analysis=False
                                        ))
    
    # Create RVDroid configurations with LLM enabled
    for llm_type in llm_types[:1]:  # Just the first LLM type
        for model in llm_models[llm_type][:1]:  # Just the first model
            for strategy in strategy_types[:2]:  # First 2 strategies
                for visitor in visitor_types:
                    for static_level in static_analysis_levels[:1]:  # Just first level
                        configurations.append(ToolConfiguration(
                            tool_name="rvdroid",
                            llm_type=llm_type,
                            llm_model=model,
                            strategy_type=strategy,
                            parser_type="uiautomator",  # RVDroid uses UIAutomator
                            visitor_type=visitor,
                            use_static_analysis=True,
                            static_analysis_level=static_level,
                            use_screenshot_analysis=False,
                            extra_params={"use_llm": True}
                        ))
    
    # Add RVDroid without LLM as baseline
    configurations.append(ToolConfiguration(
        tool_name="rvdroid",
        llm_type="ollama",
        llm_model="llama3.2:3b",
        strategy_type="basic",
        parser_type="uiautomator",
        visitor_type="basic",
        use_static_analysis=True,
        static_analysis_level="basic",
        use_screenshot_analysis=False,
        extra_params={"use_llm": False}
    ))
    
    return configurations


def create_default_test_suite() -> TestSuite:
    """Create a default test suite with various configurations for testing."""
    return TestSuite(
        name="Default Test Suite",
        description="Test suite with diverse configurations of RVAndroid and RVDroid",
        tool_configurations=create_default_configurations(),
        apps=[],
        output_dir="test_results",
        repetitions=1
    )