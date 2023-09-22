import logging
import os
import shutil
import subprocess
import sys

import utils
from app import App
from commands.command import Command
from commands.command_exception import CommandException
from settings import JAVAMOP_BIN, RV_MONITOR_BIN, MOP_DIR, MOP_OUT_DIR, ANDROID_JAR_PATH, LIB_TMP_DIR, TMP_DIR, \
    APKS_DIR, D2J_DEX2JAR, D2J_ASM_VERIFY, INSTRUMENTED_DIR, RVM_TMP_DIR, WORKING_DIR, D2J_APK_SIGN, KEYSTORE_FILE

EXTENSION_AJ = ".aj"
EXTENSION_JAR = ".jar"
EXTENSION_MOP = ".mop"
EXTENSION_RVM = ".rvm"


class RvAndroid(object):
    """
    this class encapsulates some actions using rvsec
    """

    def __init__(self):
        pass

    def instrument_apks(self, out_dir=INSTRUMENTED_DIR):
        self.__prepare_instrumentation()
        apks = utils.get_apks(APKS_DIR)
        logging.info("Instrumenting {} apks ...".format(len(apks)))
        for app in apks:
            self.__instrument(app, out_dir)

    def instrument(self, app_path: str, out_dir=INSTRUMENTED_DIR, generate_monitor=True):
        self.__prepare_instrumentation(generate_monitor)
        app = App(app_path)
        return self.__instrument(app, out_dir)

    def __prepare_instrumentation(self, generate_monitor=True):
        self.clear()
        self.__execute_maven()
        if generate_monitor:
            self.__runtime_verification()

    def __instrument(self, app: App, out_dir=INSTRUMENTED_DIR):
        logging.info("Instrumenting: {}".format(app.name))
        self.__decompile(app)
        self.__include_generated_monitor()
        self.__compile(app)
        signed_apk = self.__create_apk(app, out_dir=out_dir)
        # TODO esta limpando tudo?
        # self.clear()
        logging.info("APK instrumented: {}".format(signed_apk))
        return signed_apk

    def clear(self):
        folders = [LIB_TMP_DIR, TMP_DIR, RVM_TMP_DIR]
        for folder in folders:
            logging.info("Deleting folder: {}".format(folder))
            shutil.rmtree(folder, ignore_errors=True)

    def __compile(self, app: App, work_dir=TMP_DIR):
        logging.info("Instrumenting: {}".format(work_dir))
        classpath = self.__get_classpath(app)
        classpath.append(work_dir)
        logging.info("CLASSPATH={}".format(':'.join(classpath)))
        ajc_cmd = Command("ajc", ['-cp', ':'.join(classpath), '-Xlint:ignore',
                                  '-inpath', work_dir, '-d', work_dir,
                                  '-source', '1.8', '-sourceroots', work_dir])
        self.__execute_command(ajc_cmd, "ajc")

    def __decompile(self, app: App, out_dir=TMP_DIR):
        logging.info("Decompiling {}".format(app.name))
        utils.create_folder_if_not_exists(out_dir)
        no_monitor_jar_name = "no_monitor_{}.jar".format(app.name)
        no_monitor_jar = os.path.join(out_dir, no_monitor_jar_name)
        self.__d2j_dex2jar(app, no_monitor_jar)
        assert os.path.exists(no_monitor_jar)
        self.__d2j_asm_verify(no_monitor_jar)
        utils.unzip(no_monitor_jar, out_dir)
        utils.delete_file(no_monitor_jar)
        logging.info("Decompiled classes in: {}".format(out_dir))

    def __d2j_dex2jar(self, app: App, output_jar_file: str):
        dex2jar_cmd = Command(D2J_DEX2JAR, ['-f', '-o', output_jar_file, app.path])
        # skips the verification (last argument) of the stderr because dex2jar prints an valid output in stderr
        self.__execute_command(dex2jar_cmd, "dex2jar", True)

    def __d2j_asm_verify(self, jar_file):
        asm_verify_cmd = Command(D2J_ASM_VERIFY, [jar_file])
        # TODO testar um caso de erro para verificar se esta capturando
        self.__execute_command(asm_verify_cmd, "asm_verify")

    def __d2j_apk_sign(self, signed_apk: str, unsigned_apk: str):
        apk_sign_cmd = Command(D2J_APK_SIGN, ['-f', '-o', signed_apk, unsigned_apk])
        self.__execute_command(apk_sign_cmd, "apk_sign", True)

    def __runtime_verification(self):
        utils.create_folder_if_not_exists(MOP_OUT_DIR)
        self.__java_mop()
        self.__rv_monitor()

    def __java_mop(self):
        logging.info("Executing JavaMOP")
        mop_files = os.path.join(MOP_DIR, '*' + EXTENSION_MOP)
        javamop_cmd = Command(JAVAMOP_BIN, ['-d', MOP_OUT_DIR, '-merge', mop_files])
        self.__execute_command(javamop_cmd, "javamop")
        # the option '-d' is not working 100% (moves generated *.aj to MOP_OUT_DIR, but not the rvm files)
        utils.move_files_by_extension(EXTENSION_RVM, MOP_DIR, MOP_OUT_DIR)
        # copy any custom aspectj file (from MOP_DIR) to MOP_OUT_DIR
        utils.copy_files_by_extension(EXTENSION_AJ, MOP_DIR, MOP_OUT_DIR)

    def __rv_monitor(self):
        logging.info("Executing RV-Monitor")
        rvm_files = os.path.join(MOP_OUT_DIR, '*' + EXTENSION_RVM)
        rvmonitor_cmd = Command(RV_MONITOR_BIN, ['-d', MOP_OUT_DIR, '-merge', rvm_files])
        self.__execute_command(rvmonitor_cmd, "rvmonitor")
        # delete the .rvm files generated and already used by rv-monitor
        utils.delete_files_by_extension(EXTENSION_RVM, MOP_OUT_DIR)

    def __execute_maven(self):
        # run maven to copy the libraries (dependencies) to LIB_TMP_DIR
        maven_cmd = Command('mvn', ['clean', 'compile'])
        self.__execute_command(maven_cmd, "maven")

    def __get_classpath(self, app: App):
        # TODO pegar o android.jar dinamicamente de acordo com o target_sdk do app
        classpath = [self.__get_android_jar()]
        for x in os.listdir(LIB_TMP_DIR):
            if x.lower().endswith(EXTENSION_JAR):
                classpath.append(os.path.join(LIB_TMP_DIR, x))
        return classpath

    def __execute_command(self, cmd: Command, tag: str, skip_stderr=False):
        cmd_result = cmd.invoke(stdout=sys.stdout)  # , stderr=sys.stderr)
        cond = cmd_result.code != 0
        if not skip_stderr:
            cond = cond or cmd_result.stderr
        if cond:
            raise CommandException("{0}: {1}. {2}".format(tag, cmd_result.code, cmd_result.stderr))

    def __include_generated_monitor(self, out_dir=TMP_DIR):
        logging.info("Including generated RV artifacts ...")
        utils.copy_files(MOP_OUT_DIR, out_dir)

    def __create_apk(self, app: App, work_dir=TMP_DIR, out_dir=INSTRUMENTED_DIR):
        logging.info("Creating instrumented APK ...")
        # Extract RV-Monitor support classes
        self.__merge_support_classes(work_dir)

        # Compress resulting transformed classes to Jar
        utils.create_folder_if_not_exists(RVM_TMP_DIR)
        monitored_jar_name = "monitored_{}.jar".format(app.name)
        monitored_jar = os.path.join(RVM_TMP_DIR, monitored_jar_name)
        # TODO rever esse balaio de gato
        utils.zip_dir_content(monitored_jar, work_dir)
        shutil.move(monitored_jar, work_dir)
        shutil.rmtree(RVM_TMP_DIR)
        monitored_jar = os.path.join(work_dir, monitored_jar_name)
        logging.info("Classes compressed: {}".format(monitored_jar))

        # Compile classes in Jar to Dex format
        unsigned_apk = self.__d8(app, monitored_jar, out_dir=out_dir)
        # Sign the apk
        return self.__sign_apk(app, unsigned_apk, out_dir=out_dir)

    def __merge_support_classes(self, out_dir=TMP_DIR):
        # directory where the libraries will be unzipped
        utils.create_folder_if_not_exists(RVM_TMP_DIR)
        jars = ["rv-monitor-rt.jar", "rvsec-core.jar", "rvsec-logger-logcat.jar", "aspectjrt.jar"]
        logging.info("Including runtime dependencies: {}".format(jars))
        for jar_name in jars:
            jar = os.path.join(LIB_TMP_DIR, jar_name)
            utils.unzip(jar, RVM_TMP_DIR)
            utils.delete_file(jar)
        ## Remove rv-monitor-rt's manifest
        metainf_dir = os.path.join(RVM_TMP_DIR, "META-INF")
        utils.delete_dir(metainf_dir)
        # Merge RV-Monitor support classes
        shutil.copytree(RVM_TMP_DIR, out_dir, dirs_exist_ok=True)
        logging.info("Dependencies included in: {}".format(out_dir))
        shutil.rmtree(RVM_TMP_DIR)

    def __d8(self, app: App, monitored_jar: str, out_dir=INSTRUMENTED_DIR):
        # TODO acho q tem esse mesmo comando em outro canto ... ver onde deixar
        utils.create_folder_if_not_exists(out_dir)

        logging.info("Compiling to DEX: {}".format(monitored_jar))
        d8_cmd = Command('d8', [monitored_jar, '--release',
                                '--lib', self.__get_android_jar(),
                                '--min-api', '26'])
        self.__execute_command(d8_cmd, "d8")

        dex_name = 'classes.dex'
        generated_dex = os.path.join(WORKING_DIR, dex_name)
        assert os.path.exists(generated_dex)
        # shutil.copy2(generated_dex, out_dir)
        shutil.move(generated_dex, out_dir)

        # copy the original apk (as unsigned_apk)
        unsigned_apk_name = "unsigned_{}".format(app.name)
        unsigned_apk = os.path.join(out_dir, unsigned_apk_name)
        shutil.copy2(app.path, unsigned_apk)
        logging.info("Copying original APK ({}) to {}".format(app.name, unsigned_apk))

        # Replace old/original classes.dex in APK with new/genereated classes.dex
        # zip_cmd = Command('zip', ['-r', unsigned_apk, generated_dex])
        # self.__execute_command(zip_cmd, "zip_d8")
        # TODO usar command ... customizar com o cwd
        logging.info("Replacing old 'classes.dex' in: {}".format(unsigned_apk_name))
        subprocess.Popen(['zip', '-r', unsigned_apk_name, dex_name], cwd=out_dir)

        # Verify and sign the Jar with debug key, repairing any inconsistent manifests
        self.__d2j_asm_verify(unsigned_apk)

        return unsigned_apk

    def __sign_apk(self, app: App, unsigned_apk: str, out_dir=INSTRUMENTED_DIR):
        logging.info("Signing APK: {}".format(unsigned_apk))
        # Sign debug Jar with final key
        signed_apk = os.path.join(out_dir, app.name)
        self.__d2j_apk_sign(signed_apk, unsigned_apk)
        os.remove(unsigned_apk)
        assert os.path.exists(signed_apk)

        zip_cmd = Command('zip', ['-q', '-d', signed_apk, "META-INF*"])
        self.__execute_command(zip_cmd, "zip_sign_apk")

        self.__jarsigner(signed_apk)
        self.__jarsigner_verify(signed_apk)

        return signed_apk

    def __get_android_jar(self):
        # TODO pegar o android.jar dinamicamente de acordo com o target_sdk do app
        return ANDROID_JAR_PATH

    def __jarsigner(self, signed_apk):
        jarsigner_cmd = Command('jarsigner',
                                ['-sigalg', 'SHA256withRSA', '-digestalg', 'SHA-256', '-keystore', KEYSTORE_FILE,
                                 signed_apk, 'server', '-storepass', 'password'])
        self.__execute_command(jarsigner_cmd, "jarsigner")

    def __jarsigner_verify(self, signed_apk):
        jarsigner_cmd = Command('jarsigner', ['-verify', '-certs', signed_apk])
        self.__execute_command(jarsigner_cmd, "jarsigner_verify")


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.info("Executing")

    apk = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/cryptoapp.apk"
    rv_android = RvAndroid()
    rv_android.instrument(apk)
