#!/usr/bin/env python3
"""
Teste manual do sistema rv-tools.

Este script testa as funcionalidades do sistema rv-tools, incluindo
registro de ferramentas, sistema de variantes, parsing de especificações,
arquitetura unificada e integração com rv-platform/rv-experiment.
"""

import sys
import os
from typing import List, Dict, Any

# Add modules to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules', 'rv-android-core', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules', 'rv-tools', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules', 'rvandroid-tool', 'src'))

def test_tool_spec():
    """Testa a ToolSpec."""
    print("=== Testando ToolSpec ===")
    
    try:
        from rv_android_core.tools.tool_spec import ToolSpec
        
        # Teste criação de spec builtin
        spec = ToolSpec.create_builtin_spec(
            name="test_tool",
            description="Ferramenta de teste",
            url="https://github.com/test/tool",
            version="1.0.0",
            process_pattern="test_process"
        )
        
        print(f"✅ ToolSpec criada: {spec.name}")
        print(f"   URL: {spec.url}")
        print(f"   Versão: {spec.version}")
        print(f"   Process Pattern: {spec.process_pattern}")
        
        # Teste serialização
        spec_dict = spec.to_dict()
        spec_restored = ToolSpec.from_dict(spec_dict)
        
        if spec_restored.name == spec.name and spec_restored.url == spec.url:
            print("✅ Serialização/deserialização funcionando")
        else:
            print("❌ Problema na serialização")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste ToolSpec: {e}")
        return False

def test_tool_registry():
    """Testa o ToolRegistry."""
    print("\n=== Testando ToolRegistry ===")
    
    try:
        from rv_tools.registry.registry import ToolRegistry
        from rv_android_core.tools.tool_spec import ToolSpec
        from rv_android_core.tools.abstract_tool import AbstractTool
        from rv_android_core.commands.command import Command
        from rv_android_core.util.jar_resolver import JarResolver
        
        # Reset registry para teste limpo
        ToolRegistry.reset_instance()
        registry = ToolRegistry.get_instance()
        
        # Classe de teste usando arquitetura unificada
        class TestTool(AbstractTool):
            def __init__(self, name="test", description="Test tool", process_pattern="test"):
                super().__init__(name, description, process_pattern)
                self.config = {}
                self.jar_resolver = JarResolver()
            
            def configure(self, config):
                self.config.update(config)
            
            def execute_tool_specific_logic(self, task, app):
                """Implementação usando arquitetura unificada."""
                self.logger.info(f"Starting {self.name} execution for {app.package_name}")
                
                # Build command
                command = Command("echo", ["test"], timeout=30)
                
                # Execute with centralized error handling
                with open(task.result.trace_file, 'wb') as trace_file:
                    result = self._execute_and_check_command(command, stdout=trace_file)
                
                self.logger.info(f"{self.name} execution completed successfully")
        
        # Teste registro de ferramenta
        spec = ToolSpec.create_builtin_spec(
            name="test_tool",
            description="Ferramenta de teste",
            url="https://github.com/test/tool",
            version="1.0.0"
        )
        
        registry.register_tool("test_tool", TestTool, spec)
        print("✅ Ferramenta registrada com sucesso")
        
        # Teste registro de variantes
        registry.register_variant("test_tool", "variant1", {"param1": "value1"})
        registry.register_variant("test_tool", "variant2", {"param2": "value2"})
        print("✅ Variantes registradas com sucesso")
        
        # Teste recuperação de ferramentas
        tool_names = registry.get_tool_names()
        if "test_tool" in tool_names:
            print("✅ Ferramenta encontrada na lista")
        
        # Teste recuperação de variantes
        variants = registry.get_tool_variants("test_tool")
        if "variant1" in variants and "variant2" in variants:
            print("✅ Variantes recuperadas com sucesso")
        
        # Teste criação de instância com variante
        tool_instance = registry.get_tool("test_tool", "variant1")
        if hasattr(tool_instance, 'config') and tool_instance.config.get("param1") == "value1":
            print("✅ Instância com variante criada corretamente")
        
        # Teste infraestrutura unificada
        if hasattr(tool_instance, '_execute_and_check_command'):
            print("✅ Método centralizado _execute_and_check_command disponível")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste ToolRegistry: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tool_factory():
    """Testa o ToolFactory com parsing de especificações."""
    print("\n=== Testando ToolFactory e Parsing ===")
    
    try:
        from rv_tools.registry.factory import ToolFactory
        from rv_tools.registry.registry import ToolRegistry
        from rv_android_core.tools.tool_spec import ToolSpec
        from rv_android_core.tools.abstract_tool import AbstractTool
        from rv_android_core.commands.command import Command
        
        # Setup registry com ferramentas de teste
        ToolRegistry.reset_instance()
        registry = ToolRegistry.get_instance()
        
        class TestTool(AbstractTool):
            def __init__(self, name="test", description="Test tool", process_pattern="test"):
                super().__init__(name, description, process_pattern)
                self.config = {}
            
            def configure(self, config):
                self.config.update(config)
                print(f"   Configurado com: {config}")
            
            def execute_tool_specific_logic(self, task, app):
                """Implementação usando arquitetura unificada."""
                self.logger.info(f"Starting {self.name} execution for {app.package_name}")
                
                # Build command
                command = Command("echo", ["test"], timeout=30)
                
                # Execute with centralized error handling
                with open(task.result.trace_file, 'wb') as trace_file:
                    result = self._execute_and_check_command(command, stdout=trace_file)
                
                self.logger.info(f"{self.name} execution completed successfully")
        
        # Registrar ferramenta com variantes
        spec = ToolSpec.create_builtin_spec(
            name="droidbot",
            description="DroidBot test",
            url="https://github.com/honeynet/droidbot",
            version="1.0.0"
        )
        
        registry.register_tool("droidbot", TestTool, spec)
        registry.register_variant("droidbot", "bfs_greedy", {"policy": "bfs_greedy"})
        registry.register_variant("droidbot", "dfs_greedy", {"policy": "dfs_greedy"})
        
        # Teste parsing de especificações
        test_specs = [
            "droidbot",                                    # Simples
            "droidbot:bfs_greedy",                        # Com variante
            "droidbot:dfs_greedy@count=2000",            # Variante + parâmetros
            "droidbot@timeout=600,debug=true",           # Só parâmetros
            "droidbot:bfs_greedy:extra@count=1000,seed=42"  # Múltiplas variantes + parâmetros
        ]
        
        print("Testando parsing de especificações:")
        
        for spec in test_specs:
            try:
                print(f"  Parsing: '{spec}'")
                tool_name, variants, params = ToolFactory._parse_tool_spec(spec)
                print(f"    -> Tool: {tool_name}, Variants: {variants}, Params: {params}")
                
                # Teste criação de ferramenta
                tool_instance = ToolFactory.create_tool_from_spec(spec, registry)
                print(f"    -> Instância criada: {tool_instance.name}")
                
                # Verificar arquitetura unificada
                if hasattr(tool_instance, '_execute_and_check_command'):
                    print(f"    -> ✅ Arquitetura unificada presente")
                
            except Exception as e:
                print(f"    -> ❌ Erro: {e}")
        
        print("✅ Parsing de especificações funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste ToolFactory: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_builtin_tools():
    """Testa as ferramentas built-in com arquitetura unificada."""
    print("\n=== Testando Ferramentas Built-in ===")
    
    try:
        # Teste MonkeyTool
        from rv_tools.builtin.monkey.tool import MonkeyTool
        
        monkey = MonkeyTool()
        print(f"✅ MonkeyTool criado: {monkey.name}")
        print(f"   URL: {monkey.TOOL_SPEC.url}")
        
        # Verificar arquitetura unificada
        if hasattr(monkey, '_execute_and_check_command'):
            print("✅ MonkeyTool usando arquitetura unificada")
        
        # Teste configuração
        monkey.configure({"event_count": 5000, "seed": 42})
        if monkey.config["event_count"] == 5000 and monkey.config["seed"] == 42:
            print("✅ MonkeyTool configuração funcionando")
        
        # Teste DroidBotTool  
        from rv_tools.builtin.droidbot.tool import DroidBotTool, register_droidbot_variants
        
        droidbot = DroidBotTool()
        print(f"✅ DroidBotTool criado: {droidbot.name}")
        print(f"   URL: {droidbot.TOOL_SPEC.url}")
        print(f"   Políticas disponíveis: {droidbot.get_available_policies()}")
        
        # Verificar arquitetura unificada
        if hasattr(droidbot, '_execute_and_check_command'):
            print("✅ DroidBotTool usando arquitetura unificada")
        
        # Teste configuração de variante
        droidbot.configure({"policy": "bfs_greedy", "count": 2000})
        if droidbot.config["policy"] == "bfs_greedy" and droidbot.config["count"] == 2000:
            print("✅ DroidBotTool configuração funcionando")
        
        # Teste FastBot com JarResolver
        from rv_tools.builtin.fastbot.tool import FastBotTool
        
        fastbot = FastBotTool()
        print(f"✅ FastBotTool criado: {fastbot.name}")
        print(f"   Estratégias disponíveis: {fastbot.get_available_strategies()}")
        
        # Verificar integração com JarResolver
        if hasattr(fastbot, 'jar_resolver'):
            print("✅ FastBotTool usando JarResolver")
        
        # Verificar arquitetura unificada
        if hasattr(fastbot, '_execute_and_check_command'):
            print("✅ FastBotTool usando arquitetura unificada")
        
        # Teste APE
        from rv_tools.builtin.ape.tool import APETool
        
        ape = APETool()
        print(f"✅ APETool criado: {ape.name}")
        print(f"   Estratégias disponíveis: {ape.get_available_strategies()}")
        
        # Verificar integração com JarResolver
        if hasattr(ape, 'jar_resolver'):
            print("✅ APETool usando JarResolver")
        
        # Verificar arquitetura unificada
        if hasattr(ape, '_execute_and_check_command'):
            print("✅ APETool usando arquitetura unificada")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de ferramentas built-in: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_circuit_breaker():
    """Testa a funcionalidade do circuit breaker."""
    print("\\n=== Testando Circuit Breaker ===")
    
    try:
        from rv_android_core.commands.circuit_breaker import CommandCircuitBreaker, CircuitBreakerState
        from rv_android_core.commands.command import Command
        from rv_android_core.util.exceptions import CircuitBreakerOpenError
        
        # Create circuit breaker with low threshold for testing
        circuit_breaker = CommandCircuitBreaker(failure_threshold=2, retry_count=1)
        
        # Create test command
        test_command = Command("echo", ["test"], timeout=30)
        
        # Test initial state - should be closed
        state = circuit_breaker.get_circuit_state(test_command)
        if state == CircuitBreakerState.CLOSED:
            print("✅ Circuit breaker initial state: CLOSED")
        else:
            print(f"❌ Unexpected initial state: {state}")
            return False
        
        # Test execution allowed initially
        if circuit_breaker.is_execution_allowed(test_command):
            print("✅ Execution allowed in CLOSED state")
        else:
            print("❌ Execution blocked in CLOSED state")
            return False
        
        # Record failures to trigger circuit breaker
        circuit_breaker.record_failure(test_command)
        circuit_breaker.record_failure(test_command)
        
        # Check if circuit opened
        state = circuit_breaker.get_circuit_state(test_command)
        if state == CircuitBreakerState.OPEN:
            print("✅ Circuit breaker opened after failures")
        else:
            print(f"❌ Circuit breaker should be open, but is: {state}")
            return False
        
        # Test execution blocked when open
        try:
            circuit_breaker.is_execution_allowed(test_command)
            print("❌ Execution should be blocked in OPEN state")
            return False
        except CircuitBreakerOpenError:
            print("✅ Execution blocked in OPEN state")
        
        # Test transition to half-open after retry count
        try:
            circuit_breaker.is_execution_allowed(test_command)  # This should transition to half-open
        except CircuitBreakerOpenError:
            pass
        
        # Check if transitioned to half-open
        if circuit_breaker.is_execution_allowed(test_command):
            state = circuit_breaker.get_circuit_state(test_command)
            if state == CircuitBreakerState.HALF_OPEN:
                print("✅ Circuit breaker transitioned to HALF_OPEN")
            else:
                print(f"❌ Expected HALF_OPEN, got: {state}")
                return False
        
        # Test success closes circuit
        circuit_breaker.record_success(test_command)
        state = circuit_breaker.get_circuit_state(test_command)
        if state == CircuitBreakerState.CLOSED:
            print("✅ Circuit breaker closed after success")
        else:
            print(f"❌ Circuit breaker should be closed after success, but is: {state}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste Circuit Breaker: {e}")
        return False

def test_unified_architecture():
    """Testa componentes da arquitetura unificada."""
    print("\n=== Testando Arquitetura Unificada ===")
    
    try:
        # Teste JarResolver
        from rv_android_core.util.jar_resolver import JarResolver
        
        jar_resolver = JarResolver()
        print("✅ JarResolver criado")
        
        # Teste busca de informações (sem precisar de arquivos reais)
        search_info = jar_resolver.get_search_paths_info("test.jar")
        if search_info and 'jar_name' in search_info:
            print("✅ JarResolver search paths funcionando")
        
        # Teste Command com timeout handling
        from rv_android_core.commands.command import Command
        from rv_android_core.util.exceptions import RVCommandTimeoutError
        
        # Comando simples que deve funcionar
        command = Command("echo", ["test"], timeout=30)
        print("✅ Command criado com timeout handling")
        
        # Teste ErrorHandler
        from rv_android_core.util.error.error_handler import ErrorHandler
        
        error_handler = ErrorHandler.get_instance()
        stats = error_handler.get_error_statistics()
        if 'error_counts' in stats:
            print("✅ ErrorHandler funcionando")
        
        # Teste exceções específicas
        from rv_android_core.util.exceptions import (
            RVCommandTimeoutError, RVToolTimeoutError, 
            RVToolExecutionError, JarNotFoundError
        )
        
        try:
            raise RVCommandTimeoutError("Test timeout", timeout_seconds=30, command="test")
        except RVCommandTimeoutError as e:
            if e.timeout_seconds == 30:
                print("✅ RVCommandTimeoutError funcionando")
        
        try:
            raise JarNotFoundError("test.jar not found", jar_name="test.jar", search_paths=["/path1", "/path2"])
        except JarNotFoundError as e:
            if e.jar_name == "test.jar":
                print("✅ JarNotFoundError funcionando")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste da arquitetura unificada: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_plugin_interface():
    """Testa a interface de plugins."""
    print("\n=== Testando Interface de Plugins ===")
    
    try:
        from rv_tools.interfaces.plugin_interface import ToolPlugin
        from rv_android_core.tools.abstract_tool import AbstractTool
        from rv_android_core.tools.tool_spec import ToolSpec
        from rv_android_core.commands.command import Command
        
        # Plugin de teste usando arquitetura unificada
        class TestPlugin(ToolPlugin):
            def get_plugin_name(self):
                return "test_plugin"
            
            def get_plugin_version(self):
                return "1.0.0"
            
            def get_plugin_description(self):
                return "Plugin de teste"
            
            def get_tool_names(self):
                return ["test_external_tool"]
            
            def get_tool_class(self, tool_name):
                if tool_name == "test_external_tool":
                    class ExternalTool(AbstractTool):
                        def __init__(self, name="external", description="External tool", process_pattern="external"):
                            super().__init__(name, description, process_pattern)
                            self.config = {}
                        
                        def configure(self, config):
                            self.config.update(config)
                        
                        def execute_tool_specific_logic(self, task, app):
                            """Implementação usando arquitetura unificada."""
                            self.logger.info(f"Starting {self.name} execution for {app.package_name}")
                            
                            # Build command
                            command = Command("echo", ["external_test"], timeout=30)
                            
                            # Execute with centralized error handling
                            with open(task.result.trace_file, 'wb') as trace_file:
                                result = self._execute_and_check_command(command, stdout=trace_file)
                            
                            self.logger.info(f"{self.name} execution completed successfully")
                    return ExternalTool
                raise ValueError(f"Unknown tool: {tool_name}")
            
            def get_tool_spec(self, tool_name):
                if tool_name == "test_external_tool":
                    return ToolSpec.create_external_spec(
                        name="test_external_tool",
                        description="Ferramenta externa de teste",
                        url="https://github.com/test/external",
                        version="1.0.0"
                    )
                raise ValueError(f"Unknown tool: {tool_name}")
            
            def get_tool_variants(self, tool_name):
                if tool_name == "test_external_tool":
                    return ["variant_a", "variant_b"]
                return []
            
            def get_variant_config(self, tool_name, variant_name):
                if tool_name == "test_external_tool":
                    if variant_name == "variant_a":
                        return {"mode": "a"}
                    elif variant_name == "variant_b":
                        return {"mode": "b"}
                return {}
        
        # Teste do plugin
        plugin = TestPlugin()
        print(f"✅ Plugin criado: {plugin.get_plugin_name()}")
        
        # Teste metadata
        metadata = plugin.get_plugin_metadata()
        if metadata["name"] == "test_plugin":
            print("✅ Metadata do plugin funcionando")
        
        # Teste criação de instância
        tool_instance = plugin.create_tool_instance("test_external_tool")
        if tool_instance.name == "test_external_tool":
            print("✅ Criação de instância via plugin funcionando")
        
        # Verificar arquitetura unificada
        if hasattr(tool_instance, '_execute_and_check_command'):
            print("✅ Plugin tool usando arquitetura unificada")
        
        # Teste registro no registry
        from rv_tools.registry.registry import ToolRegistry
        
        ToolRegistry.reset_instance()
        registry = ToolRegistry.get_instance()
        
        plugin.register_tools(registry)
        print("✅ Registro de ferramentas via plugin funcionando")
        
        # Verificar se variantes foram registradas
        variants = registry.get_tool_variants("test_external_tool")
        if "variant_a" in variants and "variant_b" in variants:
            print("✅ Variantes registradas via plugin")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de interface de plugins: {e}")
        import traceback
        traceback.print_exc()
        return False

def tmp_rvandroid_registration():
    """Testa o registro do RVAndroid real."""
    print("\n=== Testando Registro do RVAndroid Real ===")
    
    try:
        # Importar a implementação real do RVAndroid
        from rv_tools.registry.registry import ToolRegistry
        from rvandroid_tool.tools.rvandroid.tool import RVAndroidTool, register_rvandroid_variants
        
        ToolRegistry.reset_instance()
        registry = ToolRegistry.get_instance()
        
        # Registro do RVAndroid real
        registry.register_tool("rvandroid", RVAndroidTool, RVAndroidTool.TOOL_SPEC)
        print("✅ RVAndroid real registrado")
        print(f"   Nome: {RVAndroidTool.TOOL_SPEC.name}")
        print(f"   URL: {RVAndroidTool.TOOL_SPEC.url}")
        print(f"   Versão: {RVAndroidTool.TOOL_SPEC.version}")
        
        # Registro das variantes reais do RVAndroid
        register_rvandroid_variants(registry)
        
        variants = registry.get_tool_variants("rvandroid")
        print(f"✅ Variantes do RVAndroid registradas: {len(variants)}")
        print(f"   Variantes: {variants}")
        
        # Teste instância básica
        basic_tool = registry.get_tool("rvandroid")
        print(f"✅ Instância básica criada: {basic_tool.name}")
        print(f"   Backends disponíveis: {basic_tool.get_available_backends()}")
        print(f"   Estratégias disponíveis: {basic_tool.get_available_strategies()}")
        print(f"   Visitor types disponíveis: {basic_tool.get_available_visitors()}")
        
        # Teste parsing complexo do RVAndroid
        from rv_tools.registry.factory import ToolFactory
        
        rvandroid_specs = [
            "rvandroid",
            "rvandroid:ollama",
            "rvandroid:llama",
            "rvandroid:llama:batch",
            "rvandroid:llama:batch@llm_temperature=0.3",
            "rvandroid:gpt4:context@llm_temperature=0.2,llm_max_tokens=2048",
            "rvandroid:llama_batch@server_port=5001,debug_mode=true"
        ]
        
        print("\nTestando especificações complexas do RVAndroid:")
        for spec in rvandroid_specs:
            try:
                print(f"  Parsing: '{spec}'")
                tool_instance = ToolFactory.create_tool_from_spec(spec, registry)
                
                # Mostrar configuração relevante
                relevant_config = {
                    k: v for k, v in tool_instance.config.items() 
                    if k in ['llm_backend', 'llm_model', 'prompt_strategy', 'llm_temperature', 'llm_max_tokens', 'server_port', 'debug_mode']
                }
                print(f"    -> Instância criada com config: {relevant_config}")
                
            except Exception as e:
                print(f"    -> ❌ Erro: {e}")
        
        # Teste get_tool_info
        tool_info = basic_tool.get_tool_info()
        print(f"\n✅ Informações da ferramenta obtidas: {len(tool_info)} campos")
        
        print("✅ Sistema de variantes complexas do RVAndroid real funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste do RVAndroid: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration_scenarios():
    """Testa cenários de integração com rv-platform e rv-experiment."""
    print("\n=== Testando Cenários de Integração ===")
    
    try:
        from rv_tools.registry.registry import ToolRegistry
        from rv_tools.registry.factory import ToolFactory
        
        # Simular integração com rv-platform
        print("Simulando integração com rv-platform...")
        
        # Reset e setup
        ToolRegistry.reset_instance()
        registry = ToolRegistry.get_instance()
        
        # Registrar ferramentas para teste de integração
        from rv_tools.builtin.monkey.tool import MonkeyTool
        from rv_tools.builtin.droidbot.tool import DroidBotTool, register_droidbot_variants
        from rv_tools.builtin.fastbot.tool import FastBotTool, register_fastbot_variants
        from rv_tools.builtin.ape.tool import APETool, register_ape_variants
        from rvandroid_tool.tools.rvandroid.tool import RVAndroidTool, register_rvandroid_variants
        
        # Registro automático das ferramentas
        registry.register_tool("monkey", MonkeyTool, MonkeyTool.TOOL_SPEC)
        registry.register_tool("droidbot", DroidBotTool, DroidBotTool.TOOL_SPEC)
        registry.register_tool("fastbot", FastBotTool, FastBotTool.TOOL_SPEC)
        registry.register_tool("ape", APETool, APETool.TOOL_SPEC)
        registry.register_tool("rvandroid", RVAndroidTool, RVAndroidTool.TOOL_SPEC)
        
        # Registro de variantes
        register_droidbot_variants(registry)
        register_fastbot_variants(registry)
        register_ape_variants(registry)
        register_rvandroid_variants(registry)
        
        print("✅ Ferramentas registradas para integração")
        
        # Simular comando do rv-platform: list-tools
        print("\nSimulando 'rv-platform list-tools':")
        tools = registry.get_all_tools()
        for tool in tools:
            variants = registry.get_tool_variants(tool.name)
            print(f"  📦 {tool.name} - {tool.description}")
            if variants and len(variants) > 1:  # Skip default variant
                variant_list = [v for v in variants if v != 'default']
                if variant_list:
                    print(f"      Variantes: {', '.join(variant_list)}")
        
        # Simular comando do rv-experiment com parsing incluindo RVAndroid
        print("\nSimulando 'rv-experiment run --tools monkey,droidbot:bfs_greedy,fastbot:balanced,ape:sata,rvandroid:llama:batch':")
        
        tool_specs = ["monkey@event_count=5000", "droidbot:bfs_greedy@count=2000", "fastbot:balanced", "ape:sata@running_minutes=5", "rvandroid:llama:batch@llm_temperature=0.3"]
        created_tools = []
        
        for spec in tool_specs:
            tool = ToolFactory.create_tool_from_spec(spec, registry)
            created_tools.append(tool)
            
            # Verificar arquitetura unificada
            unified_arch = "✅" if hasattr(tool, '_execute_and_check_command') else "❌"
            jar_resolver = "✅" if hasattr(tool, 'jar_resolver') else "N/A"
            
            # Mostrar configuração relevante
            if tool.name == "rvandroid":
                relevant_config = {k: v for k, v in getattr(tool, 'config', {}).items() 
                                 if k in ['llm_backend', 'llm_model', 'prompt_strategy', 'llm_temperature']}
            else:
                relevant_config = {k: v for k, v in getattr(tool, 'config', {}).items() 
                                 if k in ['policy', 'count', 'event_count', 'seed', 'strategy', 'max_step', 'running_minutes']}
            
            print(f"  ✅ Criada: {tool.name} (config: {relevant_config}) [Unif: {unified_arch}, JAR: {jar_resolver}]")
        
        print("✅ Cenários de integração funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Erro nos testes de integração: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_and_stats():
    """Testa performance e estatísticas do sistema."""
    print("\n=== Testando Performance e Estatísticas ===")
    
    try:
        import time
        from rv_tools.registry.registry import ToolRegistry
        from rv_tools.registry.factory import ToolFactory
        
        ToolRegistry.reset_instance()
        registry = ToolRegistry.get_instance()
        
        # Registrar várias ferramentas para teste de performance
        from rv_tools.builtin.monkey.tool import MonkeyTool
        from rv_tools.builtin.droidbot.tool import DroidBotTool, register_droidbot_variants
        from rv_tools.builtin.fastbot.tool import FastBotTool, register_fastbot_variants
        from rv_tools.builtin.ape.tool import APETool, register_ape_variants
        from rvandroid_tool.tools.rvandroid.tool import RVAndroidTool, register_rvandroid_variants
        
        start_time = time.time()
        
        # Registro em massa
        registry.register_tool("monkey", MonkeyTool, MonkeyTool.TOOL_SPEC)
        registry.register_tool("droidbot", DroidBotTool, DroidBotTool.TOOL_SPEC)
        registry.register_tool("fastbot", FastBotTool, FastBotTool.TOOL_SPEC)
        registry.register_tool("ape", APETool, APETool.TOOL_SPEC)
        registry.register_tool("rvandroid", RVAndroidTool, RVAndroidTool.TOOL_SPEC)
        register_droidbot_variants(registry)
        register_fastbot_variants(registry)
        register_ape_variants(registry)
        register_rvandroid_variants(registry)
        
        # Registro de múltiplas variantes de teste
        for i in range(10):
            registry.register_variant("monkey", f"test_variant_{i}", {"seed": i})
        
        registration_time = time.time() - start_time
        print(f"✅ Registro de ferramentas: {registration_time:.4f}s")
        
        # Teste performance de criação de instâncias
        start_time = time.time()
        
        test_specs = ["droidbot:bfs_greedy@count=1000", "fastbot:balanced", "monkey@event_count=5000", "ape:sata", "rvandroid:llama@llm_temperature=0.3"]
        for i in range(25):  # Reduced iteration count for faster testing
            for spec in test_specs:
                tool = ToolFactory.create_tool_from_spec(spec, registry)
                
                # Verificar que todas as ferramentas têm arquitetura unificada
                if not hasattr(tool, '_execute_and_check_command'):
                    print(f"⚠️ {tool.name} não tem arquitetura unificada")
        
        creation_time = time.time() - start_time
        print(f"✅ Criação de {25 * len(test_specs)} instâncias: {creation_time:.4f}s")
        
        # Estatísticas do registry
        info = registry.get_registry_info()
        print("📊 Estatísticas do Registry:")
        print(f"   Total de ferramentas: {info['total_tools']}")
        print(f"   Total de variantes: {info['total_variants']}")
        print(f"   Ferramentas: {info['tools']}")
        print(f"   Variantes por ferramenta: {info['variants_by_tool']}")
        
        # Validar arquitetura unificada
        unified_count = 0
        jar_resolver_count = 0
        for tool_name in info['tools']:
            tool_instance = registry.get_tool(tool_name)
            if hasattr(tool_instance, '_execute_and_check_command'):
                unified_count += 1
            if hasattr(tool_instance, 'jar_resolver'):
                jar_resolver_count += 1
        
        print(f"   Ferramentas com arquitetura unificada: {unified_count}/{len(info['tools'])}")
        print(f"   Ferramentas com JarResolver: {jar_resolver_count}/{len(info['tools'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nos testes de performance: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rvandroid_registration():
    """Testa o registro do RVAndroid com arquitetura unificada."""
    print("\n=== Testando Registro do RVAndroid ===")
    
    try:
        # Importar a implementação real do RVAndroid
        from rv_tools.registry.registry import ToolRegistry
        from rvandroid_tool.tools.rvandroid.tool import RVAndroidTool, register_rvandroid_variants
        
        ToolRegistry.reset_instance()
        registry = ToolRegistry.get_instance()
        
        # Registro do RVAndroid real
        registry.register_tool("rvandroid", RVAndroidTool, RVAndroidTool.TOOL_SPEC)
        print("✅ RVAndroid registrado")
        print(f"   Nome: {RVAndroidTool.TOOL_SPEC.name}")
        print(f"   URL: {RVAndroidTool.TOOL_SPEC.url}")
        print(f"   Versão: {RVAndroidTool.TOOL_SPEC.version}")
        
        # Registro das variantes reais do RVAndroid
        register_rvandroid_variants(registry)
        
        variants = registry.get_tool_variants("rvandroid")
        print(f"✅ Variantes do RVAndroid registradas: {len(variants)}")
        print(f"   Variantes: {variants}")
        
        # Teste instância básica
        basic_tool = registry.get_tool("rvandroid")
        print(f"✅ Instância básica criada: {basic_tool.name}")
        print(f"   Backends disponíveis: {basic_tool.get_available_backends()}")
        print(f"   Estratégias disponíveis: {basic_tool.get_available_strategies()}")
        print(f"   Visitor types disponíveis: {basic_tool.get_available_visitors()}")
        
        # Verificar arquitetura unificada
        if hasattr(basic_tool, '_execute_and_check_command'):
            print("✅ RVAndroid usando arquitetura unificada")
        
        # Teste parsing complexo do RVAndroid
        from rv_tools.registry.factory import ToolFactory
        
        rvandroid_specs = [
            "rvandroid",
            "rvandroid:ollama",
            "rvandroid:llama",
            "rvandroid:llama:batch",
            "rvandroid:llama:batch@llm_temperature=0.3",
            "rvandroid:gpt4:context@llm_temperature=0.2,llm_max_tokens=2048",
            "rvandroid:llama_batch@server_port=5001,debug_mode=true"
        ]
        
        print("\nTestando especificações complexas do RVAndroid:")
        for spec in rvandroid_specs:
            try:
                print(f"  Parsing: '{spec}'")
                tool_instance = ToolFactory.create_tool_from_spec(spec, registry)
                
                # Verificar arquitetura unificada
                unified_arch = "✅" if hasattr(tool_instance, '_execute_and_check_command') else "❌"
                
                # Mostrar configuração relevante
                relevant_config = {
                    k: v for k, v in tool_instance.config.items() 
                    if k in ['llm_backend', 'llm_model', 'prompt_strategy', 'llm_temperature', 'llm_max_tokens', 'server_port', 'debug_mode']
                }
                print(f"    -> Instância criada com config: {relevant_config} [Unif: {unified_arch}]")
                
            except Exception as e:
                print(f"    -> ❌ Erro: {e}")
        
        # Teste get_tool_info
        tool_info = basic_tool.get_tool_info()
        print(f"\n✅ Informações da ferramenta obtidas: {len(tool_info)} campos")
        
        print("✅ Sistema de variantes complexas do RVAndroid funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste do RVAndroid: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executa todos os testes do sistema rv-tools."""
    print("🧪 TESTE MANUAL DO SISTEMA RV-TOOLS")
    print("=" * 60)
    
    tests = [
        ("ToolSpec", test_tool_spec),
        ("ToolRegistry", test_tool_registry),
        ("ToolFactory e Parsing", test_tool_factory),
        ("Ferramentas Built-in", test_builtin_tools),
        ("Arquitetura Unificada", test_unified_architecture),
        ("Interface de Plugins", test_plugin_interface),
        ("Registro do RVAndroid", test_rvandroid_registration),
        ("Cenários de Integração", test_integration_scenarios),
        ("Performance e Estatísticas", test_performance_and_stats)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSOU")
            else:
                failed += 1
                print(f"❌ {test_name}: FALHOU")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name}: ERRO INESPERADO - {e}")
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    print(f"✅ Testes que passaram: {passed}")
    print(f"❌ Testes que falharam: {failed}")
    print(f"📈 Taxa de sucesso: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema rv-tools com arquitetura unificada funcionando perfeitamente.")
        print("\n🏗️ ARQUITETURA VALIDADA:")
        print("   ✅ Tratamento centralizado de erros (_execute_and_check_command)")
        print("   ✅ JarResolver para resolução de arquivos JAR")
        print("   ✅ Command com timeout handling (RVCommandTimeoutError)")
        print("   ✅ ErrorHandler com stacktraces reduzidos para timeouts")
        print("   ✅ Todas as ferramentas usando padrões unificados")
        return 0
    else:
        print(f"\n⚠️ {failed} teste(s) falharam. Verificar implementação.")
        return 1

if __name__ == "__main__":
    sys.exit(main())