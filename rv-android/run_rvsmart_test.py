#!/usr/bin/env python3
"""
Execução real do RVSmart com TestOrchestrator.

Simula o fluxo normal de execução:
- Inicia o app
- Captura estado
- Gera ações com LLM
- Executa ações no dispositivo
- Repete até timeout

🚨 PRÉ-REQUISITOS:
- Emulador rodando (emulator-5554)
- APK instalado (cryptoapp)
- Ollama serve ativo
- Modelo gemma3:4b disponível
"""

import logging
import os
import sys
import time
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvsmart-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-static-analysis" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-uiautomator" / "src"))

# Environment setup
from rv_android_core import constants
parent_directory = os.path.dirname(os.getcwd())
os.environ[constants.ENV_RVSEC_HOME] = parent_directory

def setup_logging():
    """Setup logging."""
    from rv_android_core.util.logging.manager import LoggingManager
    
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10,  # DEBUG
        json_format=False
    )
    
    # Setup file logging manually
    import logging
    file_handler = logging.FileHandler('./rvsmart_detailed_test.log', mode='w')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)
    
    # Silence noisy loggers
    for logger_name in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
    
    return logging_manager.get_logger('run.rvsmart.test')

def run_rvsmart_orchestrator(timeout_minutes=5):
    """
    Executa RVSmart com TestOrchestrator.
    
    Args:
        timeout_minutes: Tempo de execução em minutos (default: 5)
    """
    logger = setup_logging()
    logger.info(f"🚀 Iniciando execução do RVSmart com timeout de {timeout_minutes} minutos")
    
    try:
        # Imports necessários
        from rv_android_core.domain.app import App
        from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
        from rvsmart_tool.config.tool_config import RvSmartToolConfig
        from rvsmart_tool.orchestration.test_orchestrator import TestOrchestrator
        from rv_llm.llm.constants import LLMType, PromptStrategyType, ContextMode
        from rv_screen_parser.constants import ScreenParserType, VisitorType
        
        # Configurações do app
        app_folder = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/instrumented_apks"
        apk_name = "cryptoapp.apk"
        apk_path = os.path.join(app_folder, apk_name)
        
        # Verificar se APK existe
        if not os.path.exists(apk_path):
            logger.error(f"❌ APK não encontrado: {apk_path}")
            return False
        
        # Carregar app e dados estáticos
        logger.info("📱 Carregando aplicação e dados estáticos...")
        app = App(apk_path)
        parser = StaticAnalysisParser()
        static_data = parser.read_static_analysis_files(app_folder, apk_name, app.package_name)
        
        logger.info(f"   App: {app.name} ({app.package_name})")
        logger.info(f"   Static data carregado com sucesso")
        
        # Configuração do RVSmart com Gemma3:4b vision
        variant_config = {
            "llm_type": LLMType.OLLAMA,
            "llm_model": "gemma3:4b",
            "temperature": 0.3,
            "top_p": 0.9,
            "max_tokens": 800,
            "vision": True,
            "prompt_strategy": PromptStrategyType.VISION,
            "parser_type": ScreenParserType.UIAUTOMATOR,
            "visitor_type": VisitorType.BASIC,
            "context_mode": ContextMode.STATELESS,
            "debug_mode": True
        }
        
        tool_config = RvSmartToolConfig.create_from_variant(variant_config)
        
        logger.info("⚙️ Configuração RVSmart:")
        logger.info(f"   LLM: {tool_config.llm_config.llm_type} / {tool_config.llm_config.model}")
        logger.info(f"   Vision: {tool_config.llm_config.vision}")
        logger.info(f"   Parser: {tool_config.prompt_config.parser_type}")
        logger.info(f"   Strategy: {tool_config.prompt_config.strategy_type}")
        logger.info(f"   Timeout: {timeout_minutes} minutos")
        
        # Criar TestOrchestrator
        logger.info("🎬 Criando TestOrchestrator...")
        orchestrator = TestOrchestrator(
            static_data=static_data.to_dict() if hasattr(static_data, 'to_dict') else static_data,
            tool_config=tool_config,
            app=app,
            device_id="emulator-5554",
            results_dir="./rvsmart_test_results"
        )
        
        # Executar teste com timeout configurado
        timeout_seconds = timeout_minutes * 60
        logger.info(f"▶️ Iniciando execução por {timeout_minutes} minutos ({timeout_seconds} segundos)...")
        logger.info("="*60)
        
        start_time = time.time()
        
        try:
            # Executar o ciclo de teste
            orchestrator.execute_test_cycle(timeout=timeout_seconds)
            
            execution_time = time.time() - start_time
            logger.info("="*60)
            logger.info(f"✅ Execução completada em {execution_time:.1f} segundos")
            
        except KeyboardInterrupt:
            logger.info("\n⚠️ Execução interrompida pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro durante execução: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Obter métricas finais
            metrics = orchestrator.metrics
            
            logger.info("\n📊 MÉTRICAS FINAIS:")
            logger.info(f"   Total de ações executadas: {metrics.total_actions}")
            logger.info(f"   Ações bem-sucedidas: {metrics.successful_actions}")
            logger.info(f"   Ações falhadas: {metrics.failed_actions}")
            logger.info(f"   Taxa de sucesso: {(metrics.successful_actions/max(1,metrics.total_actions))*100:.1f}%")
            logger.info(f"   Navegações externas: {metrics.external_navigation_count}")
            logger.info(f"   Reinicializações do app: {metrics.app_restarts}")
            logger.info(f"   Total de erros: {metrics.error_count}")
            logger.info(f"   Tempo total: {metrics.execution_time:.1f}s")
            
            # Cleanup
            logger.info("\n🧹 Limpando recursos...")
            orchestrator.cleanup()
            
            # Resultado final
            success = metrics.successful_actions > 0
            
            if success:
                logger.info("\n🎉 SUCESSO: RVSmart executou ações com sucesso!")
            else:
                logger.warning("\n⚠️ AVISO: Nenhuma ação foi executada com sucesso")
            
            return success
            
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal."""
    logger = setup_logging()
    logger.info("🧪 RVSmart Test Runner")
    logger.info("="*60)
    
    # Verificar pré-requisitos
    import subprocess
    
    # 1. Verificar emulador
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        if 'emulator-5554' not in result.stdout:
            logger.error("❌ Emulador não detectado!")
            logger.error("   Execute: emulator @seu_avd")
            return 1
        logger.info("✅ Emulador detectado")
    except:
        logger.error("❌ Não foi possível verificar emulador")
        return 1
    
    # 2. Verificar Ollama
    try:
        result = subprocess.run(['pgrep', '-f', 'ollama'], capture_output=True, text=True, timeout=5)
        if not result.stdout.strip():
            logger.warning("⚠️ Ollama pode não estar rodando")
            logger.warning("   Execute: ollama serve")
        else:
            logger.info("✅ Ollama detectado")
    except:
        logger.warning("⚠️ Não foi possível verificar Ollama")
    
    # 3. Perguntar timeout ao usuário
    try:
        timeout_input = input("\n⏱️ Por quantos minutos deseja executar o teste? (padrão: 5): ").strip()
        timeout = int(timeout_input) if timeout_input else 5
        
        if timeout < 1:
            logger.warning("Timeout mínimo é 1 minuto. Usando 1 minuto.")
            timeout = 1
        elif timeout > 60:
            logger.warning("Timeout máximo é 60 minutos. Usando 60 minutos.")
            timeout = 60
            
    except ValueError:
        logger.info("Usando timeout padrão de 5 minutos")
        timeout = 5
    
    logger.info(f"\n🎯 Executando teste por {timeout} minutos...")
    logger.info("   Pressione Ctrl+C para interromper a qualquer momento\n")
    
    # Executar teste
    success = run_rvsmart_orchestrator(timeout_minutes=timeout)
    
    # Resultado final
    logger.info("\n" + "="*60)
    if success:
        logger.info("🎉 TESTE COMPLETO: RVSmart funcionando com sucesso!")
        logger.info("   - Ações foram geradas pelo LLM")
        logger.info("   - Ações foram executadas no dispositivo")
        logger.info("   - Screenshots processados com vision")
        logger.info("   - Parser UIAutomator funcionando")
        return 0
    else:
        logger.error("❌ TESTE FALHOU: Verifique os logs para detalhes")
        return 1

if __name__ == "__main__":
    sys.exit(main())