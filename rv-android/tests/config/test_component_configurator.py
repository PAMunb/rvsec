import os
from unittest.mock import patch, MagicMock

import pytest

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.config.configuration import Configuration
from rvandroid.config.configuration_manager import ConfigurationManager
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType
from rvandroid.parser.screen.visitor.base_visitor import BaseScreenVisitor


class TestComponentConfigurator:
    """Tests for the ComponentConfigurator class"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock Configuration instance"""
        return MagicMock(spec=Configuration)

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock ConfigurationManager instance"""
        return MagicMock(spec=ConfigurationManager)

    @pytest.fixture
    def mock_static_data(self):
        """Create a mock static data object"""
        return MagicMock()

    @pytest.fixture
    def configurator(self, mock_config, mock_config_manager, mock_static_data):
        """Create a ComponentConfigurator with mocked dependencies"""
        with patch('rvandroid.config.component_configurator.Configuration') as mock_config_cls, \
                patch('rvandroid.config.component_configurator.ConfigurationManager') as mock_config_manager_cls:
            mock_config_cls.get_instance.return_value = mock_config
            mock_config_manager_cls.return_value = mock_config_manager

            return ComponentConfigurator(mock_static_data)

    def test_component_configurator_initialization(self, configurator, mock_static_data, mock_config,
                                                   mock_config_manager):
        """Test ComponentConfigurator constructor"""
        assert configurator.static_data == mock_static_data
        assert configurator.config == mock_config
        assert configurator.config_manager == mock_config_manager

        # Check if default configuration is initialized
        assert hasattr(configurator, 'llm_config')
        assert hasattr(configurator, 'parser_class')
        assert hasattr(configurator, 'visitor_class')
        assert hasattr(configurator, 'strategy_class')

    def test_set_llm(self, configurator):
        """Test set_llm method"""
        # Test with valid LLM type
        result = configurator.set_llm("ollama", "llama3.2:3b", temperature=0.5, max_tokens=1000)

        assert result == configurator  # Should return self for chaining
        assert configurator.llm_config.model_type == "ollama"
        assert configurator.llm_config.model_name == "llama3.2:3b"
        assert configurator.llm_config.temperature == 0.5
        assert configurator.llm_config.max_tokens == 1000

        # Test with model unspecified (should use first available)
        result = configurator.set_llm("huggingface")

        assert result == configurator
        assert configurator.llm_config.model_type == "huggingface"
        assert configurator.llm_config.model_name == "meta-llama/Meta-Llama-3.1-8B-Instruct"

        # Test with invalid LLM type
        with pytest.raises(ValueError):
            configurator.set_llm("invalid_llm_type")

    def test_set_strategy(self, configurator):
        """Test set_strategy method"""
        # Create a mock for the strategy class
        mock_strategy = MagicMock()

        # Patch the imported class inside the method
        with patch('rvandroid.llm.prompt.prompt_strategy_dspy.DSPyPromptStrategy', mock_strategy):
            # Test with valid strategy type
            result = configurator.set_strategy("dspy", max_tokens=500)

            assert result == configurator  # Should return self for chaining
            assert configurator.llm_config.strategy_type == "dspy"
            assert configurator.strategy_kwargs == {"max_tokens": 500}

        # Test with invalid strategy type
        with pytest.raises(ValueError):
            configurator.set_strategy("invalid_strategy_type")

    def test_set_parser(self, configurator):
        """Test set_parser method"""
        # Create a mock for the parser class
        mock_parser = MagicMock()

        # Patch the imported class inside the method
        with patch('rvandroid.parser.screen.uiautomator.uiautomator_parser.UIAutomator2Parser', mock_parser):
            # Test with valid parser type
            result = configurator.set_parser("uiautomator", timeout=30)

            assert result == configurator  # Should return self for chaining
            assert configurator.llm_config.parser_type == ParserType.UIAUTOMATOR
            assert configurator.parser_kwargs == {"timeout": 30}

        # Test with invalid parser type
        with pytest.raises(ValueError):
            configurator.set_parser("invalid_parser_type")

    def test_set_visitor(self, configurator):
        """Test set_visitor method"""
        # Create a mock for the visitor class
        mock_visitor = MagicMock()

        # Patch the imported class inside the method
        with patch('rvandroid.parser.screen.visitor.enhanced_visitor.EnhancedTextVisitor', mock_visitor):
            # Test with valid visitor type
            result = configurator.set_visitor("detailed", include_bounds=True)

            assert result == configurator  # Should return self for chaining
            assert configurator.visitor_kwargs == {"include_bounds": True}

        # Test with invalid visitor type
        with pytest.raises(ValueError):
            configurator.set_visitor("invalid_visitor_type")

    def test_create_parser(self, configurator):
        """Test create_parser method"""
        # Setup mock
        mock_parser_instance = MagicMock(spec=AbstractScreenParser)
        mock_parser_class = MagicMock(return_value=mock_parser_instance)
        configurator.parser_class = mock_parser_class

        # Call method
        parser = configurator.create_parser()

        # Verify
        assert parser == mock_parser_instance
        mock_parser_class.assert_called_once()

    def test_create_visitor(self, configurator, mock_static_data):
        """Test create_visitor method"""
        # Setup mock
        mock_visitor_instance = MagicMock(spec=BaseScreenVisitor)
        mock_visitor_class = MagicMock(return_value=mock_visitor_instance)
        configurator.visitor_class = mock_visitor_class
        configurator.visitor_kwargs = {"include_content": True}

        # Call method
        visitor = configurator.create_visitor()

        # Verify
        assert visitor == mock_visitor_instance
        mock_visitor_class.assert_called_once_with(mock_static_data, "", include_content=True)

        # Test with explicit parameters
        other_static_data = MagicMock()
        configurator.create_visitor(other_static_data, "TestActivity")

        # Should use provided parameters instead of instance defaults
        mock_visitor_class.assert_called_with(other_static_data, "TestActivity", include_content=True)

    def test_create_strategy(self, configurator, mock_static_data):
        """Test create_strategy method"""
        # Setup mock
        mock_strategy_instance = MagicMock()
        mock_strategy_class = MagicMock(return_value=mock_strategy_instance)
        configurator.strategy_class = mock_strategy_class
        configurator.strategy_kwargs = {"max_tokens": 500}

        # Setup mock parser
        mock_parser = MagicMock()
        with patch.object(configurator, 'create_parser', return_value=mock_parser):
            # Call method
            strategy = configurator.create_strategy()

            # Verify
            assert strategy == mock_strategy_instance
            mock_strategy_class.assert_called_once_with(mock_static_data, mock_parser, max_tokens=500)

            # Test with explicit static data
            other_static_data = MagicMock()
            configurator.create_strategy(other_static_data)

            # Should use provided static data instead of instance default
            mock_strategy_class.assert_called_with(other_static_data, mock_parser, max_tokens=500)

    def test_create_llm(self, configurator):
        """Test create_llm method"""
        # Setup mock
        mock_llm_instance = MagicMock()
        mock_model_factory = MagicMock()
        mock_model_factory.create.return_value = mock_llm_instance

        # Patch the imported ModelFactory
        with patch('rvandroid.llm.model_factory.ModelFactory', mock_model_factory):
            # Set LLM config
            configurator.llm_config.model_type = "ollama"
            configurator.llm_config.model_name = "llama3.2:3b"
            configurator.llm_config.kwargs = {"temperature": 0.7}

            # Call method
            llm = configurator.create_llm()

            # Verify
            assert llm == mock_llm_instance
            mock_model_factory.create.assert_called_once_with("ollama", "llama3.2:3b", temperature=0.7)

    def test_from_config(self, configurator, mock_config):
        """Test from_config method"""
        # Ao invés de usar side_effect, que pode ser problemático se não tiver
        # o número exato de chamadas correspondentes, usaremos return_value
        # para cada chamada específica de get_str.

        # Configurar os mocks individualmente
        mock_config.get_str.reset_mock(side_effect=True)  # Remover qualquer side_effect anterior

        # Usar um dict para mapear argumentos para valores de retorno
        return_values = {
            ("llm.type", "ollama"): "ollama",
            ("llm.model", None): "llama3.2:3b",
            ("strategy.type", "basic"): "basic",
            ("parser.type", "droidbot"): "droidbot",
            ("visitor.type", "enhanced"): "enhanced"
        }

        # Configurar o mock para retornar valores com base nos argumentos
        def get_str_side_effect(key, default=None):
            return return_values.get((key, default), default)

        mock_config.get_str.side_effect = get_str_side_effect

        # Configurar o mock para get
        def get_side_effect(key, default=None):
            if key == "llm.base_url":
                return None
            elif key == "llm.api_key":
                return None
            elif key == "llm.temperature":
                return 0.7
            return default

        mock_config.get.side_effect = get_side_effect

        # Chamar o método
        result = configurator.from_config()

        # Verificar resultado e chamadas
        assert result == configurator  # Should return self for chaining
        mock_config.get_str.assert_any_call("llm.type", "ollama")
        mock_config.get_str.assert_any_call("llm.model", None)
        mock_config.get_str.assert_any_call("strategy.type", "basic")
        mock_config.get_str.assert_any_call("parser.type", "droidbot")
        mock_config.get_str.assert_any_call("visitor.type", "enhanced")

        # Testar com arquivo de configuração
        with patch('os.path.exists', return_value=True):
            configurator.from_config("config.json")
            mock_config.load_from_file.assert_called_once_with("config.json")

    def test_to_config_dict(self, configurator):
        """Test to_config_dict method"""
        # Setup config values
        configurator.llm_config.model_type = "ollama"
        configurator.llm_config.model_name = "llama3.2:3b"
        configurator.llm_config.temperature = 0.7
        configurator.llm_config.max_tokens = 500
        configurator.llm_config.strategy_type = "basic"
        configurator.llm_config.parser_type = ParserType.DROIDBOT
        configurator.llm_config.kwargs = {"base_url": "http://localhost:11434"}

        # Add a mock for _get_visitor_type_name
        with patch.object(configurator, '_get_visitor_type_name', return_value="enhanced"):
            # Call method
            config_dict = configurator.to_config_dict()

            # Verify
            assert "llm" in config_dict
            assert config_dict["llm"]["type"] == "ollama"
            assert config_dict["llm"]["model"] == "llama3.2:3b"
            assert config_dict["llm"]["temperature"] == 0.7
            assert config_dict["llm"]["max_tokens"] == 500
            assert config_dict["llm"]["base_url"] == "http://localhost:11434"

            assert "strategy" in config_dict
            assert config_dict["strategy"]["type"] == "basic"

            assert "parser" in config_dict
            assert config_dict["parser"]["type"] == "droidbot"

            assert "visitor" in config_dict

    def test_save_to_config_file(self, configurator):
        """Test save_to_config_file method"""
        # Setup
        config_dict = {"llm": {"type": "ollama"}}

        with patch.object(configurator, 'to_config_dict', return_value=config_dict), \
                patch('os.makedirs') as mock_makedirs, \
                patch('builtins.open', create=True), \
                patch('json.dump') as mock_json_dump:
            # Call method
            result = configurator.save_to_config_file("/path/to/config.json")

            # Verify
            assert result is True
            mock_makedirs.assert_called_once_with(os.path.dirname("/path/to/config.json"), exist_ok=True)
            mock_json_dump.assert_called_once()

    def test_describe_configuration(self, configurator):
        """Test describe_configuration method"""
        # Setup
        configurator.llm_config.model_type = "ollama"
        configurator.llm_config.model_name = "llama3.2:3b"
        configurator.llm_config.strategy_type = "basic"
        configurator.llm_config.parser_type = ParserType.DROIDBOT
        configurator.strategy_class = MagicMock()
        configurator.strategy_class.__name__ = "BasicPromptStrategy001"
        configurator.parser_class = MagicMock()
        configurator.parser_class.__name__ = "DroidBotParser"
        configurator.visitor_class = MagicMock()
        configurator.visitor_class.__name__ = "TextVisitor"

        # Call method
        description = configurator.describe_configuration()

        # Verify
        assert "llm" in description
        assert description["llm"]["type"] == "ollama"
        assert description["llm"]["model"] == "llama3.2:3b"
        assert description["llm"]["strategy_type"] == "basic"
        assert description["llm"]["parser_type"] == "DROIDBOT"

        assert description["strategy"] == "BasicPromptStrategy001"
        assert description["parser"] == "DroidBotParser"
        assert description["visitor"] == "TextVisitor"

    def test_get_available_llm_types(self, configurator):
        """Test get_available_llm_types method"""
        types = configurator.get_available_llm_types()
        assert "ollama" in types
        assert "huggingface" in types
        assert "dspy" in types
        assert "langchain" in types
        assert "frontier" in types

    def test_get_available_strategy_types(self, configurator):
        """Test get_available_strategy_types method"""
        types = configurator.get_available_strategy_types()
        assert "basic" in types
        assert "dspy" in types
        assert "single_action" in types

    def test_get_available_parser_types(self, configurator):
        """Test get_available_parser_types method"""
        types = configurator.get_available_parser_types()
        assert "droidbot" in types
        assert "uiautomator" in types

    def test_get_available_visitor_types(self, configurator):
        """Test get_available_visitor_types method"""
        types = configurator.get_available_visitor_types()
        assert "basic" in types
        assert "enhanced" in types
        assert "detailed" in types

    def test_get_available_models(self, configurator):
        """Test get_available_models method"""
        # Test with valid LLM type
        models = configurator.get_available_models("ollama")
        assert "llama3.2:3b" in models
        assert "gemma3:4b" in models

        # Test with invalid LLM type
        models = configurator.get_available_models("nonexistent")
        assert models == []
