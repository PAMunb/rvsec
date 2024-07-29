import utils
from app import App
from commands.command import Command

def teste01():
    check_emulator_cmd = Command('adb', ['-s', 'emulator-5554', 'shell', 'getprop', 'init.svc.bootanim'], timeout)
    check_result = check_emulator_cmd.invoke()
    utils.execute_command(check_emulator_cmd, "", False)
    pass


if __name__ == '__main__':
    # base_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples"
    # apk = "cryptoapp.apk"

    base_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini"
    apk = "com.jonbanjo.cupsprintservice_23.apk"