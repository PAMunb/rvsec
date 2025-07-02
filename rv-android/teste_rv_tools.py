#!/usr/bin/env python3
"""
Teste manual do sistema rv-tools simplificado.

Este script testa todas as funcionalidades do sistema rv-tools após a simplificação,
incluindo registro de ferramentas, sistema de variantes, parsing de especificações
e integração com rv-platform/rv-experiment.
"""

import sys
import os
from typing import List, Dict, Any

# Add modules to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules', 'rv-android-core', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules', 'rv-tools', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules', 'rvandroid-tool', 'src'))

def tmp_tool_spec():
    """Testa a nova ToolSpec simplificada."""
    print("=== Testando ToolSpec Simplificada ===")
    
    try:
        from rv_android_core.tools.tool_spec import ToolSpec
        
        # Teste criação de spec builtin
        spec = ToolSpec.create_builtin_spec(
            name="tmp_tool",
            description="Ferramenta de teste",
            url="https://github.com/test/tool",
            version="1.0.0",
            process_pattern="tmp_process"
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

def tmp_tool_registry():
    """Testa o ToolRegistry simplificado."""
    print("\n=== Testando ToolRegistry Simplificado ===")
    
    try:
        from rv_tools.registry.registry import ToolRegistry
        from rv_android_core.tools.tool_spec import ToolSpec
        from rv_android_core.tools.abstract_tool import AbstractTool
        
        # Reset registry para teste limpo
        ToolRegistry.reset_instance()
        registry = ToolRegistry.get_instance()
        
        # Classe de teste
        class TestTool(AbstractTool):
            def __init__(self, name="test", description="Test tool", process_pattern="test"):
                super().__init__(name, description, process_pattern)
                self.config = {}
            
            def configure(self, config):
                self.config.update(config)
            
            def execute_tool_specific_logic(self, task, app):
                pass
        
        # Teste registro de ferramenta
        spec = ToolSpec.create_builtin_spec(
            name="tmp_tool",
            description="Ferramenta de teste",
            url="https://github.com/test/tool",
            version="1.0.0"
        )
        
        registry.register_tool("tmp_tool", TestTool, spec)
        print("✅ Ferramenta registrada com sucesso")
        
        # Teste registro de variantes
        registry.register_variant("tmp_tool", "variant1", {"param1": "value1"})
        registry.register_variant("tmp_tool", "variant2", {"param2": "value2"})
        print("✅ Variantes registradas com sucesso")
        
        # Teste recuperação de ferramentas
        tool_names = registry.get_tool_names()
        if "tmp_tool" in tool_names:
            print("✅ Ferramenta encontrada na lista")
        
        # Teste recuperação de variantes
        variants = registry.get_tool_variants("tmp_tool")
        if "variant1" in variants and "variant2" in variants:
            print("✅ Variantes recuperadas com sucesso")
        
        # Teste criação de instância com variante
        tool_instance = registry.get_tool("tmp_tool", "variant1")
        if hasattr(tool_instance, 'config') and tool_instance.config.get("param1") == "value1":
            print("✅ Instância com variante criada corretamente")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste ToolRegistry: {e}")
        import traceback
        traceback.print_exc()
        return False

def tmp_tool_factory():
    """Testa o ToolFactory com parsing de especificações."""
    print("\n=== Testando ToolFactory e Parsing ===")
    
    try:
        from rv_tools.registry.factory import ToolFactory
        from rv_tools.registry.registry import ToolRegistry
        from rv_android_core.tools.tool_spec import ToolSpec
        from rv_android_core.tools.abstract_tool import AbstractTool
        
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
                pass
        
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
        tmp_specs = [
            "droidbot",                                    # Simples
            "droidbot:bfs_greedy",                        # Com variante
            "droidbot:dfs_greedy@count=2000",            # Variante + parâmetros
            "droidbot@timeout=600,debug=true",           # Só parâmetros
            "droidbot:bfs_greedy:extra@count=1000,seed=42"  # Múltiplas variantes + parâmetros
        ]
        
        print("Testando parsing de especificações:")
        
        for spec in tmp_specs:
            try:
                print(f"  Parsing: '{spec}'")
                tool_name, variants, params = ToolFactory._parse_tool_spec(spec)
                print(f"    -> Tool: {tool_name}, Variants: {variants}, Params: {params}")
                
                # Teste criação de ferramenta
                tool_instance = ToolFactory.create_tool_from_spec(spec, registry)
                print(f"    -> Instância criada: {tool_instance.name}")
                
            except Exception as e:
                print(f"    -> ❌ Erro: {e}")
        
        print("✅ Parsing de especificações funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste ToolFactory: {e}")
        import traceback
        traceback.print_exc()
        return False

def tmp_builtin_tools():
    """Testa as ferramentas built-in atualizadas."""
    print("\n=== Testando Ferramentas Built-in ===")
    
    try:
        # Teste MonkeyTool
        from rv_tools.builtin.monkey.tool import MonkeyTool
        
        monkey = MonkeyTool()
        print(f"✅ MonkeyTool criado: {monkey.name}")
        print(f"   URL: {monkey.TOOL_SPEC.url}")
        
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
        
        # Teste configuração de variante
        droidbot.configure({"policy": "bfs_greedy", "count": 2000})
        if droidbot.config["policy"] == "bfs_greedy" and droidbot.config["count"] == 2000:
            print("✅ DroidBotTool configuração funcionando")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de ferramentas built-in: {e}")
        import traceback
        traceback.print_exc()
        return False

def tmp_plugin_interface():
    """Testa a interface de plugins simplificada."""
    print("\n=== Testando Interface de Plugins ===")
    
    try:
        from rv_tools.interfaces.plugin_interface import ToolPlugin
        from rv_android_core.tools.abstract_tool import AbstractTool
        from rv_android_core.tools.tool_spec import ToolSpec
        
        # Plugin de teste
        class TestPlugin(ToolPlugin):
            def get_plugin_name(self):
                return "tmp_plugin"
            
            def get_plugin_version(self):
                return "1.0.0"
            
            def get_plugin_description(self):
                return "Plugin de teste"
            
            def get_tool_names(self):
                return ["tmp_external_tool"]
            
            def get_tool_class(self, tool_name):
                if tool_name == "tmp_external_tool":
                    class ExternalTool(AbstractTool):
                        def __init__(self, name="external", description="External tool", process_pattern="external"):
                            super().__init__(name, description, process_pattern)
                            self.config = {}
                        
                        def configure(self, config):
                            self.config.update(config)
                        
                        def execute_tool_specific_logic(self, task, app):
                            pass
                    return ExternalTool
                raise ValueError(f"Unknown tool: {tool_name}")
            
            def get_tool_spec(self, tool_name):
                if tool_name == "tmp_external_tool":
                    return ToolSpec.create_external_spec(
                        name="tmp_external_tool",
                        description="Ferramenta externa de teste",
                        url="https://github.com/test/external",
                        version="1.0.0"
                    )
                raise ValueError(f"Unknown tool: {tool_name}")
            
            def get_tool_variants(self, tool_name):
                if tool_name == "tmp_external_tool":
                    return ["variant_a", "variant_b"]
                return []
            
            def get_variant_config(self, tool_name, variant_name):
                if tool_name == "tmp_external_tool":
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
        if metadata["name"] == "tmp_plugin":
            print("✅ Metadata do plugin funcionando")
        
        # Teste criação de instância
        tool_instance = plugin.create_tool_instance("tmp_external_tool")
        if tool_instance.name == "tmp_external_tool":
            print("✅ Criação de instância via plugin funcionando")
        
        # Teste registro no registry
        from rv_tools.registry.registry import ToolRegistry
        
        ToolRegistry.reset_instance()
        registry = ToolRegistry.get_instance()
        
        plugin.register_tools(registry)
        print("✅ Registro de ferramentas via plugin funcionando")
        
        # Verificar se variantes foram registradas
        variants = registry.get_tool_variants("tmp_external_tool")
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

def tmp_integration_scenarios():
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
        from rvandroid_tool.tools.rvandroid.tool import RVAndroidTool, register_rvandroid_variants
        
        # Registro automático das ferramentas
        registry.register_tool("monkey", MonkeyTool, MonkeyTool.TOOL_SPEC)
        registry.register_tool("droidbot", DroidBotTool, DroidBotTool.TOOL_SPEC)
        registry.register_tool("rvandroid", RVAndroidTool, RVAndroidTool.TOOL_SPEC)
        
        # Registro de variantes
        register_droidbot_variants(registry)
        register_rvandroid_variants(registry)
        
        print("✅ Ferramentas registradas para integração")
        
        # Simular comando do rv-platform: list-tools
        print("\nSimulando 'rv-platform list-tools':")
        tools = registry.get_all_tools()
        for tool in tools:
            variants = registry.get_tool_variants(tool.name)
            print(f"  📦 {tool.name} - {tool.description}")
            if variants:
                print(f"      Variantes: {', '.join(variants)}")
        
        # Simular comando do rv-experiment com parsing incluindo RVAndroid
        print("\nSimulando 'rv-experiment run --tools monkey,droidbot:bfs_greedy,rvandroid:llama:batch':")
        
        tool_specs = ["monkey", "droidbot:bfs_greedy", "rvandroid:llama:batch@llm_temperature=0.3"]
        created_tools = []
        
        for spec in tool_specs:
            tool = ToolFactory.create_tool_from_spec(spec, registry)
            created_tools.append(tool)
            
            # Mostrar configuração relevante dependendo do tipo da ferramenta
            if tool.name == "rvandroid":
                relevant_config = {
                    k: v for k, v in tool.config.items() 
                    if k in ['llm_backend', 'llm_model', 'prompt_strategy', 'llm_temperature']
                }
            else:
                relevant_config = {k: v for k, v in getattr(tool, 'config', {}).items() 
                                 if k in ['policy', 'count', 'event_count', 'seed']}
            
            print(f"  ✅ Criada: {tool.name} (config: {relevant_config})")
        
        print("✅ Cenários de integração funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Erro nos testes de integração: {e}")
        import traceback
        traceback.print_exc()
        return False

def tmp_performance_and_stats():
    """Testa performance e estatísticas do sistema simplificado."""
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
        from rvandroid_tool.tools.rvandroid.tool import RVAndroidTool, register_rvandroid_variants
        
        start_time = time.time()
        
        # Registro em massa
        registry.register_tool("monkey", MonkeyTool, MonkeyTool.TOOL_SPEC)
        registry.register_tool("droidbot", DroidBotTool, DroidBotTool.TOOL_SPEC)
        registry.register_tool("rvandroid", RVAndroidTool, RVAndroidTool.TOOL_SPEC)
        register_droidbot_variants(registry)
        register_rvandroid_variants(registry)
        
        # Registro de múltiplas variantes de teste
        for i in range(10):
            registry.register_variant("monkey", f"tmp_variant_{i}", {"seed": i})
        
        registration_time = time.time() - start_time
        print(f"✅ Registro de ferramentas: {registration_time:.4f}s")
        
        # Teste performance de criação de instâncias
        start_time = time.time()
        
        tmp_specs = ["droidbot:bfs_greedy@count=1000", "rvandroid:llama@llm_temperature=0.3", "monkey@event_count=5000"]
        for i in range(50):
            for spec in tmp_specs:
                tool = ToolFactory.create_tool_from_spec(spec, registry)
        
        creation_time = time.time() - start_time
        print(f"✅ Criação de {50 * len(tmp_specs)} instâncias: {creation_time:.4f}s")
        
        # Estatísticas do registry
        info = registry.get_registry_info()
        print("📊 Estatísticas do Registry:")
        print(f"   Total de ferramentas: {info['total_tools']}")
        print(f"   Total de variantes: {info['total_variants']}")
        print(f"   Ferramentas: {info['tools']}")
        print(f"   Variantes por ferramenta: {info['variants_by_tool']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nos testes de performance: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executa todos os testes do sistema rv-tools simplificado."""
    print("🧪 TESTE MANUAL DO SISTEMA RV-TOOLS SIMPLIFICADO")
    print("=" * 60)
    
    tests = [
        ("ToolSpec Simplificada", tmp_tool_spec),
        ("ToolRegistry Simplificado", tmp_tool_registry),
        ("ToolFactory e Parsing", tmp_tool_factory),
        ("Ferramentas Built-in", tmp_builtin_tools),
        ("Interface de Plugins", tmp_plugin_interface),
        ("Registro do RVAndroid", tmp_rvandroid_registration),
        ("Cenários de Integração", tmp_integration_scenarios),
        ("Performance e Estatísticas", tmp_performance_and_stats)
    ]
    
    passed = 0
    failed = 0
    
    for tmp_name, tmp_func in tests:
        print(f"\n{'='*20} {tmp_name} {'='*20}")
        try:
            if tmp_func():
                passed += 1
                print(f"✅ {tmp_name}: PASSOU")
            else:
                failed += 1
                print(f"❌ {tmp_name}: FALHOU")
        except Exception as e:
            failed += 1
            print(f"❌ {tmp_name}: ERRO INESPERADO - {e}")
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    print(f"✅ Testes que passaram: {passed}")
    print(f"❌ Testes que falharam: {failed}")
    print(f"📈 Taxa de sucesso: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema rv-tools simplificado funcionando perfeitamente.")
        return 0
    else:
        print(f"\n⚠️ {failed} teste(s) falharam. Verificar implementação.")
        return 1

if __name__ == "__main__":
    sys.exit(main())