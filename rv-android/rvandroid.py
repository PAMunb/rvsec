import logging
import os
import sys
import shutil

from app import App
from commands.command import Command
from commands.command_exception import CommandException
from settings import JAVAMOP_BIN, RV_MONITOR_BIN, MOP_DIR, MOP_OUT_DIR, ANDROID_JAR_PATH, LIB_TMP_DIR, TMP_DIR
import utils

EXTENSION_AJ = "*.aj"
EXTENSION_MOP = "*.mop"
EXTENSION_RVM = "*.rvm"


class RvAndroid(object):
    """
    this class encapsulates some actions using rvsec
    """
    def __init__(self):
        pass

    def instrument(self, apk: str):
        self.clear()
        self.__execute_maven()
        # self.__runtime_verification()

        app = App(apk)
        self.__decompile(app)
        self.__include_generated_monitor()
        self.__compile(app)
        self.__create_apk()

    def clear(self):
        folders = [MOP_OUT_DIR, LIB_TMP_DIR, TMP_DIR]
        for folder in folders:
            logging.info("Deleting folder: {}".format(folder))
            shutil.rmtree(folder, ignore_errors=True)

    def __compile(self, app: App):
        logging.info("Instrumenting {}".format(app.name))


    def __decompile(self, app: App):
        logging.info("Decompiling {}".format(app.name))
        self.__d2j_dex2jar()
        self.__d2j_asm_verify()

        utils.create_folder_if_not_exists(TMP_DIR)
        # Extract application classes, remove temporary application Jar
        # unzip - q $TMP_DIR /$NO_MONITOR_JAR - d $TMP_DIR
        # rm $TMP_DIR /$NO_MONITOR_JAR

    def __d2j_dex2jar(self):
        logging.info("dex2jar")

    def __d2j_asm_verify(self):
        logging.info("asm-verify")


    def __runtime_verification(self):
        utils.create_folder_if_not_exists(MOP_OUT_DIR)
        self.__java_mop()
        self.__rv_monitor()

    def __java_mop(self):
        logging.info("Executing JavaMOP ")
        mop_files = os.path.join(MOP_DIR, EXTENSION_MOP)
        javamop_cmd = Command(JAVAMOP_BIN, [ '-d', MOP_OUT_DIR, '-merge', mop_files])
        self.__execute_command(javamop_cmd, "javamop")
        # the option '-d' is not working 100% (moves generated *.aj to MOP_OUT_DIR, but not the rvm files)
        utils.move_files_by_extension(".rvm", MOP_DIR, MOP_OUT_DIR)
        # copy any custom aspectj file
        utils.copy_files_by_extension(".aj", MOP_DIR, MOP_OUT_DIR)


    def __rv_monitor(self):
        logging.info("Executing RV-Monitor")
        rvm_files = os.path.join(MOP_OUT_DIR, EXTENSION_RVM)
        rvmonitor_cmd = Command(RV_MONITOR_BIN, [ '-d', MOP_OUT_DIR, '-merge', rvm_files])
        self.__execute_command(rvmonitor_cmd, "rvmonitor")
        # delete the .rvm files generated and already used by rv-monitor
        utils.delete_files_by_extension(EXTENSION_RVM, MOP_OUT_DIR)


    def __execute_maven(self):
        maven_cmd = Command('mvn', ['clean', 'compile'])
        self.__execute_command(maven_cmd, "maven")


    def __get_classpath(self):
        classpath = [ANDROID_JAR_PATH]
        for x in os.listdir(LIB_TMP_DIR):
            if x.endswith(".jar"):
                classpath.append(os.path.join(LIB_TMP_DIR, x))
        return ':'.join(classpath)

    def __execute_command(self, cmd: Command, tag: str):
        cmd_result = cmd.invoke(stdout=sys.stdout)  # , stderr=sys.stderr)
        if cmd_result.stderr or cmd_result.code != 0:
            raise CommandException("{0}: {1}. {2}".format(tag, cmd_result.code, cmd_result.stderr))

    def __include_generated_monitor(self):
        logging.info("__include_generated_monitor")

    def __create_apk(self):
        logging.info("__create_apk")
        self.__merge_support_classes()
        self.__d8()
        self.__sign_apk()

    def __merge_support_classes(self):
        logging.info("__merge_support_classes")

    def __d8(self):
        logging.info("__d8")

    def __sign_apk(self):
        logging.info("__sign_apk")


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.info("Executing")

    apk = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/cryptoapp.apk"
    rv_android = RvAndroid()
    rv_android.instrument(apk)