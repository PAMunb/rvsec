import os
import sys
import logging

from settings import MOP_DIR, AVD_NAME, RESULTS_DIR, TIMESTAMP, INSTRUMENTED_DIR, APKS_DIR, WORKING_DIR
from commands.command import Command
from android import Android


TIMEOUTS = [60, 120]
POLICY = ["monkey"]

android = Android()


def execute(instrument=True):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    createFolder(RESULTS_DIR)

    logging.info("Executando")

    # Instrument apks
    if instrument:
        instrument_apks()

    # retrieve the instumented apks
    apks = _get_apks(INSTRUMENTED_DIR)  
    print("INSTRUMENTED ..........................")
    print(apks) 

    # for each instrumented apk
    for apk in apks:
        for timeout in TIMEOUTS:        
            logging.info("\nTIMEOUT: "+str(timeout))
            for policy in POLICY:
                logging.info("POLICY: "+policy)                
                run(apk, timeout, policy)


def instrument_apks():   
    #TODO recriar/zerar o diretorio de saida
    apks = _get_apks(APKS_DIR)               
    logging.info("Instrumenting {0} apks".format(len(apks)))
    for apk in apks:
        apk_path = os.path.join(APKS_DIR, apk)
        instrument(apk_path)
        #instrument(apk)


def run(apk, timeout, policy):
    logging.info("Running: APK={0}, timeout={1}, policy={2}".format(apk,timeout,policy))  
    
    apk_path = os.path.join(INSTRUMENTED_DIR, apk)
    logcat_file = ""

    android.start_emulator(AVD_NAME)

    configureLogcat()

    #android.install_apk(apk_path)

    runDroidbot(apk_path, timeout, policy)

    print("***********************************************")
    print("***********************************************")
    print("***********************************************")
    print("***********************************************")
    print("***********************************************")

    android.kill_emulator(AVD_NAME)


def instrument(apk):
    logging.info("Instrumenting: "+apk)
    instrument_cmd = Command('sh', [
                'mop.sh', 
                apk, 
                MOP_DIR
            ], 1200)
    #instrument_result = instrument_cmd.invoke(stdout=sys.stdout)
    instrument_result = instrument_cmd.invoke()
    if instrument_result.code != 0:
        raise Exception("Error while instrumenting")    


def configureLogcat():
    #TODO
    print("logcat .........")


def runDroidbot(apk_path, timeout, policy):
    logging.info("Running droidbot: "+apk_path)
    #droidbot -d emulator-5554 -a out/$APK -policy monkey -is_emulator -timeout 60
    exec_cmd = Command('droidbot', [
                '-d',
                'emulator-5554',
                '-a',
                apk_path,
                '-policy',
                'monkey',
                '-is_emulator'#,
                #'-timeout',
                #timeout
            ], timeout)
    exec_cmd.invoke(stdout=sys.stdout)


def _get_apks(dir):
    apks = []
    for file in os.listdir(dir):              
        if file.casefold().endswith(".apk"):            
            apks.append(file)
    return apks


def createFolder(folder_name):    
    if not os.path.exists(folder_name):
        try:
            logging.debug("Creating folder: "+folder_name)
            os.mkdir(folder_name)
        except OSError:
            error_msg = 'Error while creating folder {0}'.format(folder_name)
            logging.error(error_msg)
            raise Exception(error_msg)


def teste():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    apk = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/21-30-com.hwloc.lstopo_266.apk"

    #logcat_cmd = Command('adb', ['logcat', '-v', 'raw', '-s', 'hcai-intent-monitor', 'hcai-cg-monitor'])
    logcat_cmd = Command('adb', ['logcat', '-v', 'raw', '-s', 'RV-MONITOR'])
    logcat_file = "/home/pedro/tmp/teste_logcat.txt"

    with android.create_emulator(AVD_NAME) as emulator:
        with open(logcat_file, 'wb') as log_cat:
            proc = logcat_cmd.invoke_as_deamon(stdout=log_cat)
            
            print("Iniciando teste")
            runDroidbot(apk, 60, "monkey")

            proc.kill()


def teste01():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    apk = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/21-30-com.hwloc.lstopo_266.apk"
    with android.create_emulator(AVD_NAME) as emulator:
        print("Iniciando teste")
        runDroidbot(apk, 120, "monkey")



if __name__ == '__main__':            
    #execute(False)
    teste()
    logging.info('Finished !!!')
