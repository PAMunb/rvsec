#!/usr/bin/env python3
"""
Unit tests for the variant system implementation in rv-experiment.

This test module validates that the variant system is working correctly
across all integration points: configuration, validation, tool registry,
and task generation.

### Test Coverage:
- ExperimentConfig with tool variants
- Tool specification parsing (CLI format)
- Variant validation and error handling
- Registry integration with variant support
- TaskConfiguration integration
- End-to-end configuration flow
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Test imports
from rv_experiment.config import ExperimentConfig
from rv_platform.config.platform_config import ToolConfig
from rv_android_core.util.error.exceptions import ConfigurationError, ToolVariantError
from rv_android_core.domain.task import TaskConfiguration, ToolConfig as TaskToolConfig


class TestVariantSystemBasics:
    """Test basic variant system functionality."""
    
    def test_tool_config_creation_with_variants(self):
        """Test creating ToolConfig with variants."""
        tool_config = ToolConfig(
            name="droidbot", 
            variants=["dfs_greedy", "bfs_greedy"],
            parameters={"count": 1000}
        )
        
        assert tool_config.name == "droidbot"
        assert "dfs_greedy" in tool_config.variants
        assert "bfs_greedy" in tool_config.variants
        assert tool_config.parameters["count"] == 1000
    
    def test_experiment_config_with_variants(self):
        """Test creating ExperimentConfig with tool variants."""
        tools = [
            ToolConfig(name="droidbot", variants=["dfs_greedy"]),
            ToolConfig(name="ape", variants=["sata"]),
            ToolConfig(name="rvandroid", variants=["default"], parameters={
                "llm_type": "ollama",
                "llm_model": "llama3.2",
                "prompt_strategy": "standard_modular"
            })
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ExperimentConfig(
                tool_configs=tools,
                repetitions=1,
                timeouts=[60],
                apks_dir=temp_dir,  # Use temp dir to avoid validation errors
                generate_monitors=False,
                instrument_apks=False,
                run_static_analysis=False
            )
            
            assert len(config.tool_configs) == 3
            assert config.tool_configs[0].name == "droidbot"
            assert config.tool_configs[1].name == "ape"
            assert config.tool_configs[2].name == "rvandroid"
    
    def test_task_tool_config_parsing(self):
        """Test TaskToolConfig parsing of tool specifications."""
        # Test basic tool name
        tool_config = TaskToolConfig.from_tool_specification("droidbot")
        assert tool_config.tool_name == "droidbot"
        assert tool_config.variant == "default"
        assert tool_config.get_full_tool_name() == "droidbot"
        
        # Test tool with variant
        tool_config = TaskToolConfig.from_tool_specification("droidbot:dfs_greedy")
        assert tool_config.tool_name == "droidbot"
        assert tool_config.variant == "dfs_greedy"
        assert tool_config.get_full_tool_name() == "droidbot:dfs_greedy"
        
        # Test tool with variant and parameters
        tool_config = TaskToolConfig.from_tool_specification(
            "rvandroid:custom", 
            {"llm_type": "ollama", "temperature": 0.1}
        )
        assert tool_config.tool_name == "rvandroid"
        assert tool_config.variant == "custom"
        assert tool_config.additional_params["llm_type"] == "ollama"
        assert tool_config.get_full_tool_name() == "rvandroid:custom"
    
    def test_task_configuration_with_tool_config(self):
        """Test TaskConfiguration using new ToolConfig."""
        tool_config = TaskToolConfig.from_tool_specification("droidbot:dfs_greedy")
        
        task_config = TaskConfiguration(
            apk_name="test.apk",
            repetition=1,
            timeout=300,
            tool_config=tool_config
        )
        
        assert task_config.apk_name == "test.apk"
        assert task_config.tool_config.tool_name == "droidbot"
        assert task_config.tool_config.variant == "dfs_greedy"
        assert "droidbot:dfs_greedy" in str(task_config)


class TestVariantValidation:
    """Test variant validation functionality."""
    
    def test_experiment_config_validation_with_mock_registry(self):
        """Test ExperimentConfig validation with mocked tool registry."""
        tools = [
            ToolConfig(name="droidbot", variants=["dfs_greedy"]),
            ToolConfig(name="ape", variants=["sata"])
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a dummy APK file for validation
            apk_path = Path(temp_dir) / "test.apk"
            apk_path.touch()
            
            config = ExperimentConfig(
                tool_configs=tools,
                repetitions=1,
                timeouts=[60],
                apks_dir=temp_dir,
                generate_monitors=False,
                instrument_apks=False,
                run_static_analysis=False
            )
            
            # Mock the registry to avoid import issues
            with patch('rv_tools.registry.registry.ToolRegistry') as mock_registry_class:
                mock_registry = Mock()
                mock_registry_class.get_instance.return_value = mock_registry
                mock_registry.is_tool_registered.return_value = True
                mock_registry.validate_tool_variant.return_value = True
                mock_registry.get_tool_variants.return_value = ["dfs_greedy", "bfs_greedy", "sata", "default"]
                
                # Should not raise exception
                config.validate()
    
    def test_invalid_tool_validation(self):
        """Test validation with invalid tool name."""
        tools = [ToolConfig(name="nonexistent_tool", variants=["default"])]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            apk_path = Path(temp_dir) / "test.apk"
            apk_path.touch()
            
            config = ExperimentConfig(
                tool_configs=tools,
                repetitions=1,
                timeouts=[60],
                apks_dir=temp_dir,
                generate_monitors=False,
                instrument_apks=False,
                run_static_analysis=False
            )
            
            # Mock the registry to simulate tool not found
            with patch('rv_tools.registry.registry.ToolRegistry') as mock_registry_class:
                mock_registry = Mock()
                mock_registry_class.get_instance.return_value = mock_registry
                mock_registry.is_tool_registered.return_value = False
                mock_registry.get_all_tool_names.return_value = ["droidbot", "ape", "rvandroid"]
                
                with pytest.raises(ConfigurationError) as exc_info:
                    config.validate()
                
                assert "nonexistent_tool" in str(exc_info.value)
                assert "not found in registry" in str(exc_info.value)
    
    def test_invalid_variant_validation(self):
        """Test validation with invalid variant name."""
        tools = [ToolConfig(name="droidbot", variants=["invalid_variant"])]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            apk_path = Path(temp_dir) / "test.apk"
            apk_path.touch()
            
            config = ExperimentConfig(
                tool_configs=tools,
                repetitions=1,
                timeouts=[60],
                apks_dir=temp_dir,
                generate_monitors=False,
                instrument_apks=False,
                run_static_analysis=False
            )
            
            # Mock the registry to simulate invalid variant
            with patch('rv_tools.registry.registry.ToolRegistry') as mock_registry_class:
                mock_registry = Mock()
                mock_registry_class.get_instance.return_value = mock_registry
                mock_registry.is_tool_registered.return_value = True
                mock_registry.validate_tool_variant.return_value = False
                mock_registry.get_tool_variants.return_value = ["dfs_greedy", "bfs_greedy", "default"]
                
                with pytest.raises(ConfigurationError) as exc_info:
                    config.validate()
                
                assert "invalid_variant" in str(exc_info.value)
                assert "Invalid variant" in str(exc_info.value)


class TestVariantSystemIntegration:
    """Test variant system integration with other components."""
    
    def test_rvandroid_custom_variant_validation(self):
        """Test RVAndroid custom variant validation."""
        tools = [
            ToolConfig(
                name="rvandroid", 
                variants=["custom"],
                parameters={
                    "llm_type": "ollama",
                    "llm_model": "llama3.2",
                    "prompt_strategy": "standard_modular"
                }
            )
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            apk_path = Path(temp_dir) / "test.apk"
            apk_path.touch()
            
            config = ExperimentConfig(
                tool_configs=tools,
                repetitions=1,
                timeouts=[60],
                apks_dir=temp_dir,
                generate_monitors=False,
                instrument_apks=False,
                run_static_analysis=False
            )
            
            # Mock the registry 
            with patch('rv_tools.registry.registry.ToolRegistry') as mock_registry_class:
                mock_registry = Mock()
                mock_registry_class.get_instance.return_value = mock_registry
                mock_registry.is_tool_registered.return_value = True
                mock_registry.validate_tool_variant.return_value = False  # Custom variant not in registry
                
                # Should not raise exception because custom variant has required parameters
                config.validate()
    
    def test_rvandroid_custom_variant_missing_params(self):
        """Test RVAndroid custom variant with missing required parameters."""
        tools = [
            ToolConfig(
                name="rvandroid", 
                variants=["custom"],
                parameters={"incomplete": "config"}  # Missing required params
            )
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            apk_path = Path(temp_dir) / "test.apk"
            apk_path.touch()
            
            config = ExperimentConfig(
                tool_configs=tools,
                repetitions=1,
                timeouts=[60],
                apks_dir=temp_dir,
                generate_monitors=False,
                instrument_apks=False,
                run_static_analysis=False
            )
            
            # Mock the registry 
            with patch('rv_tools.registry.registry.ToolRegistry') as mock_registry_class:
                mock_registry = Mock()
                mock_registry_class.get_instance.return_value = mock_registry
                mock_registry.is_tool_registered.return_value = True
                mock_registry.validate_tool_variant.return_value = False  # Custom variant not in registry
                mock_registry.get_tool_variants.return_value = ["default"]
                
                with pytest.raises(ConfigurationError) as exc_info:
                    config.validate()
                
                assert "Invalid variant 'custom'" in str(exc_info.value)
    
    def test_task_configuration_serialization(self):
        """Test TaskConfiguration serialization/deserialization with ToolConfig."""
        tool_config = TaskToolConfig.from_tool_specification("droidbot:dfs_greedy")
        
        original_config = TaskConfiguration(
            apk_name="test.apk",
            repetition=1,
            timeout=300,
            tool_config=tool_config
        )
        
        # Test to_dict
        config_dict = original_config.to_dict()
        assert config_dict["tool_config"]["tool_name"] == "droidbot"
        assert config_dict["tool_config"]["variant"] == "dfs_greedy"
        
        # Test from_dict
        restored_config = TaskConfiguration.from_dict(config_dict)
        assert restored_config.apk_name == original_config.apk_name
        assert restored_config.tool_config.tool_name == original_config.tool_config.tool_name
        assert restored_config.tool_config.variant == original_config.tool_config.variant
    
    def test_legacy_compatibility(self):
        """Test backward compatibility with legacy tool_name format."""
        # Test legacy dictionary format
        legacy_dict = {
            "apk_name": "test.apk",
            "repetition": 1,
            "timeout": 300,
            "tool_name": "droidbot"  # Legacy format
        }
        
        # Should convert legacy format automatically
        config = TaskConfiguration.from_dict(legacy_dict)
        assert config.tool_config.tool_name == "droidbot"
        assert config.tool_config.variant == "default"
        
        # Test create_from_tool_spec factory method
        config2 = TaskConfiguration.create_from_tool_spec(
            apk_name="test.apk",
            repetition=1,
            timeout=300,
            tool_spec="droidbot:dfs_greedy"
        )
        assert config2.tool_config.tool_name == "droidbot"
        assert config2.tool_config.variant == "dfs_greedy"


class TestVariantSystemEndToEnd:
    """End-to-end tests for variant system functionality."""
    
    def test_complete_variant_workflow(self):
        """Test complete workflow from CLI spec to task execution."""
        # 1. Parse CLI-style tool specification
        tool_specs = ["droidbot:dfs_greedy", "ape:sata", "rvandroid"]
        
        # 2. Create tool configs
        tool_configs = []
        for spec in tool_specs:
            if ":" in spec:
                name, variant = spec.split(":", 1)
            else:
                name, variant = spec, "default"
            
            params = {}
            if name == "rvandroid" and variant == "default":
                params = {
                    "llm_type": "ollama",
                    "llm_model": "llama3.2",
                    "prompt_strategy": "standard_modular"
                }
            
            tool_configs.append(ToolConfig(name=name, variants=[variant], parameters=params))
        
        # 3. Create experiment configuration
        with tempfile.TemporaryDirectory() as temp_dir:
            apk_path = Path(temp_dir) / "test.apk"
            apk_path.touch()
            
            config = ExperimentConfig(
                tool_configs=tool_configs,
                repetitions=1,
                timeouts=[60],
                apks_dir=temp_dir,
                generate_monitors=False,
                instrument_apks=False,
                run_static_analysis=False
            )
            
            # 4. Mock validation 
            with patch('rv_tools.registry.registry.ToolRegistry') as mock_registry_class:
                mock_registry = Mock()
                mock_registry_class.get_instance.return_value = mock_registry
                mock_registry.is_tool_registered.return_value = True
                mock_registry.validate_tool_variant.return_value = True
                
                config.validate()
            
            # 5. Create task configurations
            task_configs = []
            for i, tool_config in enumerate(config.tool_configs):
                variant = tool_config.variants[0] if tool_config.variants else "default"
                task_tool_config = TaskToolConfig(
                    tool_name=tool_config.name,
                    variant=variant,
                    additional_params=tool_config.parameters
                )
                
                task_config = TaskConfiguration(
                    apk_name=f"test{i}.apk",
                    repetition=1,
                    timeout=config.timeouts[0],
                    tool_config=task_tool_config
                )
                task_configs.append(task_config)
            
            # 6. Verify task configurations
            assert len(task_configs) == 3
            assert task_configs[0].tool_config.get_full_tool_name() == "droidbot:dfs_greedy"
            assert task_configs[1].tool_config.get_full_tool_name() == "ape:sata"
            assert task_configs[2].tool_config.get_full_tool_name() == "rvandroid"  # default variant


if __name__ == "__main__":
    # Run tests manually if needed
    pytest.main([__file__, "-v"])