import subprocess
import time
import json
import shutil
import uiautomator2 as u2
from droidbot.device import Device
from droidbot.app import App
from droidbot.device_state import DeviceState
import os
# https://github.com/ollama/ollama-python

HOST="http://localhost:11434"
MODEL="llama3.2:1b"


def execute(app_path, output_dir=None):
    
    device = create_device()
    app = App(app_path, output_dir=output_dir)
    
    cont = 1
    try:
        device.set_up()
        device.connect()
        device.install_app(app)
        device.start_app(app)
        
        while(True):
            input("\npressione ENTER para continuar ...")
            
            # 1. Capture o estado do DroidBot
            state = device.get_current_state()
            print(f"state_str={state.state_str}")
            print(f"structure_str={state.structure_str}")

            prefix = f"{cont:03}"
            cont += 1

            message = create_message(state)            
            state_file = os.path.join(out_dir, prefix+".state")
            with open(state_file, "w") as arquivo:
                json.dump(message, arquivo, indent=3)
            
            # 2. Capture screenshot usando DroidBot
            img_file = os.path.join(out_dir, prefix+".png")
            img_path = device.take_screenshot()
            print(f"img_path={img_path}")
            shutil.move(img_path, img_file)
            
            # 3. Capture o dump do UIAutomator usando ADB diretamente
            # Isso evita a necessidade de desconectar o DroidBot
            uiautomator_file = os.path.join(out_dir, prefix+".uiautomator")
            capture_uiautomator_dump(uiautomator_file)
            
    except KeyboardInterrupt:
        print("Keyboard interrupt.")
        pass
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        device.disconnect()
        print("Device disconnected")

def capture_uiautomator_dump(output_file):
    """
    Captura o dump do UIAutomator usando comandos ADB diretamente,
    sem depender da biblioteca uiautomator2
    """
    try:
        # Execute o comando para capturar o dump
        print("Capturando UIAutomator dump via ADB...")
        subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/window_dump.xml"], check=True)
        # Copie o arquivo para o computador
        subprocess.run(["adb", "pull", "/sdcard/window_dump.xml", output_file], check=True)
        # Limpe o arquivo do dispositivo
        subprocess.run(["adb", "shell", "rm", "/sdcard/window_dump.xml"], check=True)
        print(f"UIAutomator dump salvo via ADB: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Erro ao capturar UIAutomator dump via ADB: {e}")
        return False


def create_device(device_serial="emulator-5554",
         is_emulator=True,
         output_dir="/tmp/",
         cv_mode=False,
         grant_perm=True,
         enable_accessibility_hard=False,
         humanoid=None,
         ignore_ad=True):
    return Device(
        device_serial=device_serial,
        is_emulator=is_emulator,
        output_dir=output_dir,
        cv_mode=cv_mode,
        grant_perm=grant_perm,
        enable_accessibility_hard=enable_accessibility_hard,
        humanoid=humanoid,
        ignore_ad=ignore_ad)


def create_message(state: DeviceState):
    message = {
        "activity": state.foreground_activity,
        "stack": state.activity_stack,
        "screen_size": {
            "width": state.width,
            "height": state.height
        },
        "view_tree": state.view_tree
    }
    return message

if __name__ == "__main__":
    base_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "t20kdc.offlinepuzzlesolver_4.apk"
    out_dir = os.path.join(base_dir, apk)
    apk_path = os.path.join(out_dir, apk)
    execute(apk_path, out_dir)