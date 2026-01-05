#!/usr/bin/env python3
"""
RVAgent Test 007: Simple CryptoApp Test

Teste simples e direto do RVAgent MVP com CryptoApp.
Foca em validar o funcionamento básico sem complexidade.
"""

import sys
import time
import logging
from pathlib import Path

# Add current path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_cryptoapp_simple():
    """Teste simples com CryptoApp."""

    print("🚀 RVAgent Test 007: Simple CryptoApp Validation")
    print("=" * 60)
    print("📱 Target: br.unb.cic.cryptoapp")
    print("📂 APK: /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk")
    print("📂 Source: /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/examples/cryptoapp")
    print()

    # Configure logging for test
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        force=True
    )

    try:
        # Test 1: Verificar imports básicos
        print("📦 TESTE 1: Validando imports básicos...")

        from rv_agent.constants import RVAgentConstants
        from rv_agent.core.rv_agent import RVAgent

        print("✅ Imports básicos: OK")
        print(f"   🧠 Modelo padrão: {RVAgentConstants.DEFAULT_MODEL}")
        print(f"   📱 Device padrão: {RVAgentConstants.DEFAULT_DEVICE_ID}")
        print()

        # Test 2: Verificar se o emulador está rodando
        print("📱 TESTE 2: Verificando emulador...")

        import subprocess
        adb_devices = subprocess.run(['adb', 'devices'], capture_output=True, text=True)

        if 'emulator-5554' in adb_devices.stdout:
            print("✅ Emulador emulator-5554: ONLINE")
        else:
            print("❌ Emulador emulator-5554: OFFLINE")
            print("   Use: emulator -avd Pixel_3_API_30 -no-snapshot &")
            return False

        # Test 3: Verificar se CryptoApp está instalado
        print("\n📦 TESTE 3: Verificando CryptoApp...")

        adb_packages = subprocess.run(
            ['adb', '-s', 'emulator-5554', 'shell', 'pm', 'list', 'packages', 'br.unb.cic.cryptoapp'],
            capture_output=True, text=True
        )

        if 'br.unb.cic.cryptoapp' in adb_packages.stdout:
            print("✅ CryptoApp: INSTALADO")
        else:
            print("❌ CryptoApp: NÃO INSTALADO")
            print("   Use: adb install /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk")
            return False

        # Test 4: Inicialização básica do RVAgent
        print("\n🤖 TESTE 4: Inicializando RVAgent...")

        try:
            agent = RVAgent(timeout=30)  # Timeout curto para teste
            print("✅ RVAgent inicializado")
            print(f"   📱 Device Interface: {type(agent.device_interface).__name__}")
            print(f"   🧠 LLM Service: {type(agent.llm_service).__name__}")
            print(f"   🔄 React Engine: {type(agent.react_engine).__name__}")

        except Exception as e:
            print(f"❌ Erro na inicialização: {e}")
            print("   Possível problema: Ollama não está rodando ou modelo não disponível")
            return False

        # Test 5: Teste de conexão com device
        print("\n📱 TESTE 5: Testando conexão com device...")

        try:
            connected = agent.connect_to_device()
            if connected:
                print("✅ Conexão com device: SUCCESS")
            else:
                print("❌ Conexão com device: FAILED")
                return False

        except Exception as e:
            print(f"❌ Erro na conexão: {e}")
            return False

        # Test 6: Teste de launch do app
        print("\n🚀 TESTE 6: Testando launch do CryptoApp...")

        try:
            launched = agent.start_testing_session("br.unb.cic.cryptoapp", "simple_test")
            if launched:
                print("✅ CryptoApp launch: SUCCESS")
                time.sleep(2)  # Aguardar app carregar
            else:
                print("❌ CryptoApp launch: FAILED")
                return False

        except Exception as e:
            print(f"❌ Erro no launch: {e}")
            return False

        # Test 7: Teste de captura de UI state
        print("\n📋 TESTE 7: Testando captura de UI state...")

        try:
            ui_state = agent.device_interface.get_current_ui_state()
            if ui_state and 'clickable_elements' in ui_state:
                element_count = len(ui_state['clickable_elements'])
                activity = ui_state.get('activity', 'unknown')
                package = ui_state.get('current_package', 'unknown')

                print("✅ UI state capturado:")
                print(f"   📱 Activity: {activity}")
                print(f"   📦 Package: {package}")
                print(f"   🔘 Elementos clicáveis: {element_count}")

                # Mostrar alguns elementos
                if element_count > 0:
                    print("   📋 Elementos encontrados:")
                    for i, element in enumerate(ui_state['clickable_elements'][:3]):
                        desc = element.get('description', 'No description')[:30]
                        coords = element.get('coordinates', [])
                        print(f"      {i+1}. {desc}... at {coords}")

            else:
                print("❌ UI state: EMPTY")
                return False

        except Exception as e:
            print(f"❌ Erro na captura de UI: {e}")
            return False

        # Test 8: Cleanup
        print("\n🧹 TESTE 8: Cleanup...")

        try:
            agent.stop_session()
            print("✅ Session stopped")

        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

        # Final result
        print("\n🏆 RESULTADO FINAL")
        print("=" * 60)
        print("✅ RVAgent MVP: FUNCIONANDO")
        print("✅ CryptoApp: CONECTADO")
        print("✅ UI State: CAPTURADO")
        print()
        print("🎯 PRÓXIMOS PASSOS:")
        print("   1. Testar tool-calling com ações simples")
        print("   2. Executar autonomia completa")
        print("   3. Validar métricas MVP")
        print()
        print("💻 COMANDO COMPLETO:")
        print("   poetry run rv-agent run --package br.unb.cic.cryptoapp --timeout 120 --debug")

        return True

    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False


if __name__ == "__main__":
    success = test_cryptoapp_simple()
    sys.exit(0 if success else 1)