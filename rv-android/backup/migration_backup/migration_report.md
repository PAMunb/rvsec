# ComponentConfigurator Migration Report

**Migration Date**: ter 10 jun 2025 13:44:39 -03
**Files Processed**: 18

## Successful Migrations

### modules/rv-experiment/.venv/lib/python3.12/site-packages/redis/asyncio/connection.py
**Backup**: backup/migration_backup/modules/rv-experiment/.venv/lib/python3.12/site-packages/redis/asyncio/connection.py
**Changes Applied**: 0

### modules/rv-experiment/.venv/lib/python3.12/site-packages/redis/connection.py
**Backup**: backup/migration_backup/modules/rv-experiment/.venv/lib/python3.12/site-packages/redis/connection.py
**Changes Applied**: 0

### modules/rv-llm/src/rv_llm/config/component_configurator.py
**Backup**: backup/migration_backup/modules/rv-llm/src/rv_llm/config/component_configurator.py
**Changes Applied**: 2
- Replaced method call: (\w+)\.set_llm\([^)]+\) -> # LLM configuration moved to factory creation
- Replaced method call: (\w+)\.set_strategy\([^)]+\) -> # Strategy configuration moved to factory creation

### modules/rv-llm/src/rv_llm/llm/huggingface_llm.py
**Backup**: backup/migration_backup/modules/rv-llm/src/rv_llm/llm/huggingface_llm.py
**Changes Applied**: 1
- Replaced import: from rv_llm.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory

### modules/rv-llm/src/rv_llm/llm/ollama_llm.py
**Backup**: backup/migration_backup/modules/rv-llm/src/rv_llm/llm/ollama_llm.py
**Changes Applied**: 1
- Replaced import: from rv_llm.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory

### modules/rv-llm/src/rv_llm/llm/prompt/framework.py
**Backup**: backup/migration_backup/modules/rv-llm/src/rv_llm/llm/prompt/framework.py
**Changes Applied**: 2
- Replaced import: from rv_llm.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory
- Replaced instantiation pattern: (\s+)config = ComponentConfigurator\(\)

### modules/rv-llm/src/rv_llm/llm/prompt/information/fragment_manager.py
**Backup**: backup/migration_backup/modules/rv-llm/src/rv_llm/llm/prompt/information/fragment_manager.py
**Changes Applied**: 1
- Replaced import: from rv_llm.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory

### modules/rv-llm/src/rv_llm/llm/prompt/strategy/base_strategy.py
**Backup**: backup/migration_backup/modules/rv-llm/src/rv_llm/llm/prompt/strategy/base_strategy.py
**Changes Applied**: 1
- Replaced import: from rv_llm.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory

### modules/rv-llm/src/rv_llm/llm/prompt/strategy/strategies/batch_action_strategy.py
**Backup**: backup/migration_backup/modules/rv-llm/src/rv_llm/llm/prompt/strategy/strategies/batch_action_strategy.py
**Changes Applied**: 1
- Replaced import: from rv_llm.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory

### modules/rv-llm/src/rv_llm/llm/prompt/strategy/strategies/standard_strategy.py
**Backup**: backup/migration_backup/modules/rv-llm/src/rv_llm/llm/prompt/strategy/strategies/standard_strategy.py
**Changes Applied**: 1
- Replaced import: from rv_llm.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory

### modules/rv-llm/src/rv_llm/llm/prompt/template/jinja_repository.py
**Backup**: backup/migration_backup/modules/rv-llm/src/rv_llm/llm/prompt/template/jinja_repository.py
**Changes Applied**: 1
- Replaced import: from rv_llm.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory

### modules/rv-llm/src/rv_llm/llm/prompt/template/template_repository.py
**Backup**: backup/migration_backup/modules/rv-llm/src/rv_llm/llm/prompt/template/template_repository.py
**Changes Applied**: 1
- Replaced import: from rv_llm.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory

### modules/rvandroid-tool/src/rvandroid_tool/llm/service/action_generator.py
**Backup**: backup/migration_backup/modules/rvandroid-tool/src/rvandroid_tool/llm/service/action_generator.py
**Changes Applied**: 1
- Replaced import: from rvandroid.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory

### modules/rvandroid-tool/src/rvandroid_tool/llm/service/action_service.py
**Backup**: backup/migration_backup/modules/rvandroid-tool/src/rvandroid_tool/llm/service/action_service.py
**Changes Applied**: 1
- Replaced import: from rvandroid.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory

### modules/rvandroid-tool/src/rvandroid_tool/llm/service/llm_manager.py
**Backup**: backup/migration_backup/modules/rvandroid-tool/src/rvandroid_tool/llm/service/llm_manager.py
**Changes Applied**: 4
- Replaced import: from rvandroid.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory
- Replaced method call: (\w+)\.create_llm\(\) -> llm_factory.create_ollama()
- Replaced method call: (\w+)\.set_llm\([^)]+\) -> # LLM configuration moved to factory creation
- Added LLMFactory initialization to constructor

### modules/rvandroid-tool/src/rvandroid_tool/llm/service/response_processor.py
**Backup**: backup/migration_backup/modules/rvandroid-tool/src/rvandroid_tool/llm/service/response_processor.py
**Changes Applied**: 1
- Replaced import: from rvandroid.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory

### modules/rvandroid-tool/src/rvandroid_tool/llm/service/state_enricher.py
**Backup**: backup/migration_backup/modules/rvandroid-tool/src/rvandroid_tool/llm/service/state_enricher.py
**Changes Applied**: 1
- Replaced import: from rvandroid.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory

### modules/rvandroid-tool/src/rvandroid_tool/tools/rvandroid/tool.py
**Backup**: backup/migration_backup/modules/rvandroid-tool/src/rvandroid_tool/tools/rvandroid/tool.py
**Changes Applied**: 3
- Replaced import: from rv_llm.config.component_configurator import ComponentConfigurator -> from rv_llm.factories import LLMFactory, PromptStrategyFactory
- Replaced method call: (\w+)\.set_llm\([^)]+\) -> # LLM configuration moved to factory creation
- Replaced method call: (\w+)\.set_strategy\([^)]+\) -> # Strategy configuration moved to factory creation

## Failed Migrations

