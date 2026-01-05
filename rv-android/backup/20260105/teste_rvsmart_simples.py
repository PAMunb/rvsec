#!/usr/bin/env python3
"""
Teste simples e focado para RVSmart - Gemma3:4b com visão.

Testa especificamente:
1. Captura de screenshot via UIAutomator
2. Conversão de estado UIAutomator -> DroidBot compatibility 
3. Processamento com LLM Gemma3:4b vision
4. Geração de ações

🚨 PRÉ-REQUISITOS:
- Emulador rodando (emulator-5554)
- Ollama serve
- gemma3:4b disponível
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

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

# Imports
from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.llm.constants import LLMType, PromptStrategyType, ContextMode
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rvsmart_tool.config.tool_config import RvSmartToolConfig
from rvsmart_tool.orchestration.test_orchestrator import TestOrchestrator
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
from rv_uiautomator import UIAutomator2Adapter, StateConverter

def setup_logging():
    """Setup logging."""
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
    
    return logging_manager.get_logger('teste.rvsmart.simples')

def test_screenshot_and_state_conversion():
    """Teste focado em captura de screenshot e conversão de estado."""
    logger = setup_logging()
    logger.info("🔍 Testando captura de screenshot e conversão de estado")
    
    # 1. Conectar UIAutomator
    ui_adapter = UIAutomator2Adapter("emulator-5554")
    if not ui_adapter.connect("emulator-5554"):
        logger.error("❌ Falha ao conectar UIAutomator")
        return False
    
    logger.info("✅ UIAutomator conectado")
    
    # 2. Capturar estado atual
    ui_state = ui_adapter.get_ui_state(force_refresh=True)
    logger.info(f"📱 Estado capturado: {list(ui_state.keys())}")
    
    # 3. Capturar screenshot
    screenshot_path = ui_adapter.take_screenshot()
    if screenshot_path and os.path.exists(screenshot_path):
        ui_state['screenshot_path'] = screenshot_path
        logger.info(f"📸 Screenshot capturado: {screenshot_path}")
    else:
        logger.warning("⚠️  Screenshot não capturado")
    
    # 4. Testar StateConverter
    converter = StateConverter()
    converted_state = converter.uiautomator_to_droidbot(ui_state)
    
    logger.info("🔄 Estado convertido:")
    logger.info(f"   hierarchy: {'SIM' if converted_state.get('hierarchy') else 'NÃO'}")
    logger.info(f"   view_tree: {'SIM' if converted_state.get('view_tree') else 'NÃO'}")
    logger.info(f"   activity: {converted_state.get('activity', 'N/A')}")
    logger.info(f"   package_name: {converted_state.get('package_name', 'N/A')}")
    logger.info(f"   screenshot_path: {'SIM' if converted_state.get('screenshot_path') else 'NÃO'}")
    
    # 5. Validar campos críticos
    success = True
    if not converted_state.get('view_tree'):
        logger.error("❌ ERRO: view_tree vazio - parser UIAutomator não terá dados XML")
        success = False
    
    if not converted_state.get('hierarchy'):
        logger.error("❌ ERRO: hierarchy vazio - compatibilidade DroidBot falhou")
        success = False
    
    if not converted_state.get('screenshot_path'):
        logger.warning("⚠️  Screenshot não incluído no estado")
    
    return success

def test_rvsmart_gemma3_vision():
    """Teste completo RVSmart com Gemma3:4b vision."""
    logger = setup_logging()
    logger.info("🚀 Testando RVSmart com Gemma3:4b Vision")
    
    # Dados do app
    app_folder = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/instrumented_apks"
    apk_name = "cryptoapp.apk"
    apk_path = os.path.join(app_folder, apk_name)
    
    if not os.path.exists(apk_path):
        logger.error(f"❌ APK não encontrado: {apk_path}")
        return False
    
    try:
        # Carregar app e dados estáticos
        app = App(apk_path)
        logger.info(f"📱 App: {app.name} ({app.package_name})")
        
        parser = StaticAnalysisParser()
        static_data = parser.read_static_analysis_files(app_folder, apk_name, app.package_name)
        logger.info("📊 Dados estáticos carregados")
        
        # Configuração Gemma3:4b vision
        variant_config = {
            "llm_type": LLMType.OLLAMA,
            "llm_model": "gemma3:4b",
            "temperature": 0.3,
            "top_p": 0.9,
            "max_tokens": 800,
            "vision": True,
            "prompt_strategy": PromptStrategyType.VISION,
            "parser_type": ScreenParserType.UIAUTOMATOR,  # CRÍTICO: parser correto
            "visitor_type": VisitorType.BASIC,
            "context_mode": ContextMode.STATELESS,
            "debug_mode": True
        }
        
        # Criar configuração da ferramenta
        tool_config = RvSmartToolConfig.create_from_variant(variant_config)
        
        logger.info("⚙️ Configuração:")
        logger.info(f"   LLM: {tool_config.llm_config.llm_type} / {tool_config.llm_config.model}")
        logger.info(f"   Vision: {tool_config.llm_config.vision}")
        logger.info(f"   Parser: {tool_config.prompt_config.parser_type}")
        logger.info(f"   Strategy: {tool_config.prompt_config.strategy_type}")
        
        # Criar TestOrchestrator
        orchestrator = TestOrchestrator(
            static_data=static_data.to_dict() if hasattr(static_data, 'to_dict') else static_data,
            tool_config=tool_config,
            app=app,
            device_id="emulator-5554",
            results_dir="./teste_rvsmart_results"
        )
        
        # Executar teste curto (30 segundos)
        logger.info("🎬 Iniciando teste (30s timeout)...")
        
        try:
            orchestrator.execute_test_cycle(timeout=30)
            
            # Verificar métricas
            metrics = orchestrator.metrics
            logger.info("📊 Resultados:")
            logger.info(f"   Total ações: {metrics.total_actions}")
            logger.info(f"   Ações bem-sucedidas: {metrics.successful_actions}")
            logger.info(f"   Ações falhadas: {metrics.failed_actions}")
            logger.info(f"   Navegação externa: {metrics.external_navigation_count}")
            logger.info(f"   Reinicializações: {metrics.app_restarts}")
            logger.info(f"   Erros: {metrics.error_count}")
            
            success = metrics.total_actions > 0
            if success:
                logger.info("✅ RVSmart funcionou - ações foram geradas!")
            else:
                logger.warning("⚠️  RVSmart não gerou ações")
            
            return success
            
        finally:
            orchestrator.cleanup()
            
    except Exception as e:
        logger.error(f"❌ Erro durante teste: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Função principal."""
    logger = setup_logging()
    logger.info("🧪 Iniciando testes focados do RVSmart")
    
    # Verificar pré-requisitos
    import subprocess
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        if 'emulator-5554' not in result.stdout:
            logger.error("❌ Emulador não está rodando! Execute: emulator @seu_avd")
            return 1
        logger.info("✅ Emulador detectado")
    except:
        logger.error("❌ Não foi possível verificar emulador")
        return 1
    
    # Teste 1: Screenshot e conversão de estado
    logger.info(f"\n{'='*60}")
    logger.info("🧪 TESTE 1: Screenshot e Conversão de Estado")
    logger.info(f"{'='*60}")
    
    conversion_ok = test_screenshot_and_state_conversion()
    
    # Teste 2: RVSmart completo
    logger.info(f"\n{'='*60}")
    logger.info("🧪 TESTE 2: RVSmart com Gemma3:4b Vision")
    logger.info(f"{'='*60}")
    
    rvsmart_ok = test_rvsmart_gemma3_vision()
    
    # Resultado final
    logger.info(f"\n{'='*60}")
    logger.info("🎯 RESULTADO FINAL")
    logger.info(f"{'='*60}")
    
    if conversion_ok and rvsmart_ok:
        logger.info("✅ SUCESSO: RVSmart está funcionando com screenshot e visão!")
        return 0
    elif conversion_ok:
        logger.info("⚠️  Conversão OK, mas RVSmart teve problemas")
        return 1
    else:
        logger.error("❌ FALHA: Problemas básicos na conversão de estado")
        return 1

if __name__ == "__main__":
    sys.exit(main())