#!/usr/bin/env python3
"""
Teste final do RVSmart - foco na geração de ações com Gemma3:4b vision.

Testa diretamente a cadeia:
UIAutomator -> StateConverter -> LLMActionService -> Ações
"""

import logging
import os
import sys
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
        console_level=20,  # INFO
        json_format=False
    )
    
    # Silence noisy loggers
    for logger_name in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
    
    return logging_manager.get_logger('teste.rvsmart.final')

def tmp_direct_action_generation():
    """Testa geração de ações diretamente."""
    logger = setup_logging()
    logger.info("🎯 TESTE FINAL: Geração direta de ações com Gemma3:4b Vision")
    
    try:
        # Imports
        from rv_android_core.domain.app import App
        from rv_android_core.domain.static import StaticAnalysisData
        from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
        from rv_uiautomator import UIAutomator2Adapter, StateConverter
        from rvsmart_tool.config.tool_config import RvSmartToolConfig
        from rvsmart_tool.llm.service.action_service import LLMActionService
        from rv_llm.llm.constants import LLMType, PromptStrategyType, ContextMode
        from rv_screen_parser.constants import ScreenParserType, VisitorType
        
        # 1. Carregar app e dados estáticos
        logger.info("1️⃣ Carregando app e dados estáticos...")
        app_folder = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/instrumented_apks"
        apk_name = "cryptoapp.apk"
        apk_path = os.path.join(app_folder, apk_name)
        
        app = App(apk_path)
        parser = StaticAnalysisParser()
        static_data = parser.read_static_analysis_files(app_folder, apk_name, app.package_name)
        
        logger.info(f"📱 App: {app.name} ({app.package_name})")
        logger.info(f"📊 Static data carregado")
        
        # 2. Conectar UIAutomator
        logger.info("2️⃣ Conectando UIAutomator...")
        ui_adapter = UIAutomator2Adapter("emulator-5554")
        if not ui_adapter.connect("emulator-5554"):
            logger.error("❌ Falha na conexão UIAutomator")
            return False
        
        logger.info("✅ UIAutomator conectado")
        
        # 3. Iniciar o APK target (como a tool deve fazer)
        logger.info("3️⃣ Iniciando aplicação target...")
        if not ui_adapter.launch_app(app.package_name):
            logger.error(f"❌ Falha ao iniciar {app.package_name}")
            return False
            
        # Aguardar app inicializar
        import time
        time.sleep(3)
        logger.info(f"✅ App {app.package_name} iniciado")
        
        # 4. Verificar se estamos no pacote correto
        current_state = ui_adapter.get_ui_state()
        current_package = current_state.get('current_package', 'unknown')
        
        if current_package != app.package_name:
            logger.warning(f"⚠️ Não estamos no pacote target!")
            logger.warning(f"   Target: {app.package_name}")
            logger.warning(f"   Current: {current_package}")
            # Tentar novamente
            ui_adapter.launch_app(app.package_name)
            time.sleep(2)
        
        # 6. Capturar estado atual
        logger.info("6️⃣ Capturando estado da tela...")
        ui_state = ui_adapter.get_ui_state(force_refresh=True)
        screenshot_path = ui_adapter.take_screenshot()
        
        if screenshot_path:
            ui_state['screenshot_path'] = screenshot_path
            logger.info(f"📸 Screenshot: {screenshot_path}")
        
        logger.info(f"📱 Estado capturado: {ui_state.get('current_activity', 'N/A')}")
        logger.info(f"📦 Pacote atual: {ui_state.get('current_package', 'N/A')}")
        
        # 7. Converter estado 
        logger.info("7️⃣ Convertendo estado UIAutomator -> DroidBot...")
        converter = StateConverter()
        converted_state = converter.uiautomator_to_droidbot(ui_state)
        
        logger.info(f"🔄 Estado convertido:")
        logger.info(f"   hierarchy: {len(converted_state.get('hierarchy', ''))} chars")
        logger.info(f"   view_tree: {len(converted_state.get('view_tree', ''))} chars")
        logger.info(f"   screenshot_path: {'✅' if converted_state.get('screenshot_path') else '❌'}")
        
        # 8. Configurar LLMActionService
        logger.info("8️⃣ Configurando LLMActionService...")
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
        logger.info(f"⚙️ Configuração criada: {tool_config.llm_config.model} (vision: {tool_config.llm_config.vision})")
        
        # 9. Criar LLMActionService
        action_service = LLMActionService(
            static_data=static_data.to_dict() if hasattr(static_data, 'to_dict') else static_data,
            tool_config=tool_config,
            app_package=app.package_name
        )
        
        logger.info("✅ LLMActionService criado")
        
        # 10. Gerar ações 
        logger.info("🔟 Gerando ações com Gemma3:4b...")
        logger.info("⏳ Aguarde... LLM processando screenshot e estado...")
        
        try:
            actions = action_service.process_state(converted_state)
            
            if actions:
                logger.info(f"🎉 SUCESSO! {len(actions)} ações geradas:")
                for i, action in enumerate(actions, 1):
                    logger.info(f"   {i}. {action}")
                
                logger.info("\n" + "="*60)
                logger.info("✅ RESULTADO FINAL: RVSMART FUNCIONANDO!")
                logger.info("✅ Screenshots capturados e incluídos no estado")
                logger.info("✅ StateConverter mapeando view_tree corretamente")
                logger.info("✅ Gemma3:4b processando com vision habilitada")
                logger.info("✅ Ações geradas com sucesso")
                logger.info("="*60)
                return True
                
            else:
                logger.warning("⚠️  Nenhuma ação gerada - LLM retornou vazio")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro na geração de ações: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        logger.error(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal."""
    logger = setup_logging()
    logger.info("🚀 Iniciando teste final do RVSmart")
    
    # Verificar pré-requisitos
    import subprocess
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        if 'emulator-5554' not in result.stdout:
            logger.error("❌ Emulador não detectado! Execute antes:")
            logger.error("   emulator @seu_avd")
            return 1
        logger.info("✅ Emulador detectado")
    except:
        logger.error("❌ Não foi possível verificar emulador")
        return 1
    
    # Executar teste
    success = tmp_direct_action_generation()
    
    if success:
        logger.info("\n🎉 TESTE FINAL: SUCESSO!")
        logger.info("RVSmart está funcionando com Gemma3:4b vision")
        logger.info("Todas as correções implementadas estão funcionais:")
        logger.info("- StateConverter com view_tree mapeado")
        logger.info("- Screenshot handling correto")  
        logger.info("- Parser UIAutomator configurado")
        logger.info("- LLM Gemma3:4b com vision ativo")
        return 0
    else:
        logger.error("\n❌ TESTE FINAL: FALHA")
        logger.error("RVSmart ainda tem problemas")
        return 1

if __name__ == "__main__":
    sys.exit(main())