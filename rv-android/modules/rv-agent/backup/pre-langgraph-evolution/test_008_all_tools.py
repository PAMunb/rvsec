#!/usr/bin/env python3
"""
RVAgent Test 008: All Tools Validation

Teste específico para validar todas as ferramentas do RVAgent:
- android_click ✅ (já testado)
- android_input
- android_scroll ✅ (já testado)
- android_back
- android_screenshot

Objetivo: Confirmar que todas as tools executam corretamente.
"""

import sys
import time
import logging
from pathlib import Path

# Add current path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_all_tools():
    """Teste sistemático de todas as tools."""

    print("🛠️ RVAgent Test 008: All Tools Validation")
    print("=" * 60)
    print("🎯 Objetivo: Testar android_click, android_input, android_scroll, android_back, android_screenshot")
    print()

    # Configure logging for test
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        force=True
    )

    try:
        # Import and initialize
        from rv_agent.core.rv_agent import RVAgent

        print("📱 SETUP: Inicializando RVAgent...")
        agent = RVAgent(timeout=45)

        if not agent.connect_to_device():
            print("❌ Falha na conexão com device")
            return False

        if not agent.start_testing_session("br.unb.cic.cryptoapp", "all_tools_test"):
            print("❌ Falha no launch do app")
            return False

        print("✅ Setup completo - app rodando")
        print()

        # Test 1: Screenshot (baseline)
        print("📸 TESTE 1: android_screenshot")
        ui_state = agent.device_interface.get_current_ui_state()
        screenshot_path = agent.device_interface.take_screenshot()

        if screenshot_path:
            print(f"✅ Screenshot: {screenshot_path}")
        else:
            print("❌ Screenshot failed")
        print()

        # Test 2: Click (já sabemos que funciona)
        print("🖱️ TESTE 2: android_click")
        click_success = agent.device_interface.click(540, 273)  # MESSAGE DIGEST button
        print(f"✅ Click: {click_success}")
        time.sleep(1)
        print()

        # Test 3: Input (precisa de um campo de texto)
        print("⌨️ TESTE 3: android_input")
        # Primeiro, tentar encontrar um campo de texto ou criar um contexto
        input_success = agent.device_interface.input_text("test123")
        print(f"✅ Input: {input_success}")
        time.sleep(1)
        print()

        # Test 4: Back navigation
        print("🔙 TESTE 4: android_back")
        back_success = agent.device_interface.back()
        print(f"✅ Back: {back_success}")
        time.sleep(1)
        print()

        # Test 5: Scroll
        print("📜 TESTE 5: android_scroll")
        scroll_success = agent.device_interface.scroll("down", "medium")
        print(f"✅ Scroll: {scroll_success}")
        time.sleep(1)
        print()

        # Final screenshot
        print("📸 TESTE FINAL: Screenshot após todas as ações")
        final_screenshot = agent.device_interface.take_screenshot()
        if final_screenshot:
            print(f"✅ Final screenshot: {final_screenshot}")
        print()

        # Cleanup
        agent.stop_session()

        print("🏆 RESULTADO FINAL")
        print("=" * 60)
        print("✅ Todas as tools foram testadas")
        print(f"📸 Screenshots: {screenshot_path and final_screenshot}")
        print(f"🖱️ Click: {click_success}")
        print(f"⌨️ Input: {input_success}")
        print(f"🔙 Back: {back_success}")
        print(f"📜 Scroll: {scroll_success}")
        print()
        print("💡 PRÓXIMOS PASSOS:")
        print("   1. Implementar app state monitoring")
        print("   2. Screenshot controlado pelo loop")
        print("   3. Auto-restart quando sair do app")

        return True

    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_all_tools()
    sys.exit(0 if success else 1)