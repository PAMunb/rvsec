import logging
import shutil
import subprocess
import sys

import utils
from app import App
from commands.command import Command
from commands.command_exception import CommandException
from settings import *

EXTENSION_AJ = ".aj"
EXTENSION_JAVA = ".java"
EXTENSION_JAR = ".jar"
EXTENSION_MOP = ".mop"
EXTENSION_RVM = ".rvm"


# class RvAndroidException(Exception):
#     pass


class RvAndroid(object):
    """
    this class encapsulates some actions using rvsec and other tools
    """

    def __init__(self):
        pass

    def instrument_apks(self, out_dir=INSTRUMENTED_DIR):
        # temporario
        erros = []

        self.__prepare_instrumentation()
        apks = utils.get_apks(APKS_DIR)
        logging.info("Instrumenting {} apks ...".format(len(apks)))
        for app in apks:
            try:
                # self.__clear([TMP_DIR, RVM_TMP_DIR])
                self.__instrument(app, out_dir)
                self.__check_if_istrumented(app, out_dir)
            except CommandException as ex:
                logging.error("Failed to instrument APK: {}. {}".format(app.name, ex))
                # TODO manda limpar???
                self.__clear([TMP_DIR, RVM_TMP_DIR])
                erros.append((app.name, ex))
            except Exception as ex:
                logging.error("Error while instrumenting APK: {}. {}".format(app.path, ex))

        print("ERROS: {}".format(len(erros)))
        for erro in erros:
            print("ERRO: {} :: {}".format(erro[0], erro[1].tool))

    # TODO deprecated ??? ... nao usar o metodo para instrumentar 1 app ... e sim o q instrumenta todos???
    def instrument(self, app_path: str, out_dir=INSTRUMENTED_DIR, force_intrumentation=False):
        self.__prepare_instrumentation()
        app = App(app_path)
        return self.__instrument(app, out_dir, force_intrumentation)

    def __prepare_instrumentation(self):
        self.clear()
        self.__execute_maven()

    def __instrument(self, app: App, out_dir=INSTRUMENTED_DIR, force_intrumentation=False):
        instrumented_apk = os.path.join(out_dir, app.name)
        if os.path.exists(instrumented_apk):
            if force_intrumentation:
                logging.info("Deleting APK: {}".format(instrumented_apk))
                os.remove(instrumented_apk)
            else:
                logging.info("Skipping APK already instrumented: {}".format(app.name))
                # TODO
                return None
        logging.info("Instrumenting: {}".format(app.name))
        self.__decompile(app)
        self.__include_generated_monitor()
        self.__compile(app)
        signed_apk = self.__create_apk(app, out_dir=out_dir)
        self.__clear([TMP_DIR, RVM_TMP_DIR])
        # TODO esta realmente instrumentado???
        logging.info("APK instrumented: {}".format(signed_apk))
        return signed_apk

    def clear(self):
        folders = [LIB_TMP_DIR, TMP_DIR, RVM_TMP_DIR]
        self.__clear(folders)

    def __clear(self, folders: list):
        for folder in folders:
            logging.info("Deleting folder: {}".format(folder))
            shutil.rmtree(folder, ignore_errors=True)
        # TODO atributo da classe ... ou arrumar outra forma de pegar o classes.dex aqui e no d8()
        dex_name = 'classes.dex'
        generated_dex = os.path.join(WORKING_DIR, dex_name)
        if os.path.exists(generated_dex):
            logging.info("Deleting: {}".format(generated_dex))
            os.remove(generated_dex)

    def __compile(self, app: App, work_dir=TMP_DIR):
        logging.info("Instrumenting: {}".format(work_dir))
        classpath = self.__get_classpath(app)
        classpath.append(work_dir)  # TODO precisa?
        logging.info("CLASSPATH={}".format(':'.join(classpath)))
        # TODO precisa do MOP_OUT_DIR?
        ajc_cmd = Command("ajc", ['-cp', ':'.join(classpath) + ':' + MOP_OUT_DIR, '-Xlint:ignore',
                                  '-inpath', work_dir, '-d', work_dir,
                                  '-source', '1.8', '-sourceroots', work_dir])
        self.__execute_command(ajc_cmd, "ajc")
        utils.delete_files_by_extension(EXTENSION_JAVA, work_dir)
        utils.delete_files_by_extension(EXTENSION_AJ, work_dir)

    def __decompile(self, app: App, out_dir=TMP_DIR):
        logging.info("Decompiling {}".format(app.name))
        utils.create_folder_if_not_exists(out_dir)
        no_monitor_jar_name = "no_monitor_{}.jar".format(app.name)
        no_monitor_jar = os.path.join(out_dir, no_monitor_jar_name)
        # TODO como o d2j lida com multidex? e como vamos lidar aqui?
        self.__d2j_dex2jar(app, no_monitor_jar)
        assert os.path.exists(no_monitor_jar)
        self.__d2j_asm_verify(no_monitor_jar, skip_verify=True)
        utils.unzip(no_monitor_jar, out_dir)
        utils.delete_file(no_monitor_jar)
        logging.info("Decompiled classes in: {}".format(out_dir))

    def __d2j_dex2jar(self, app: App, output_jar_file: str):
        dex2jar_cmd = Command(D2J_DEX2JAR, ['-f', '-o', output_jar_file, app.path])
        # skips the verification (last argument) of the stderr because dex2jar prints an valid output in stderr
        self.__execute_command(dex2jar_cmd, "dex2jar", True)

    def __d2j_asm_verify(self, jar_file, skip_verify=False):
        if skip_verify:
            return
        asm_verify_cmd = Command(D2J_ASM_VERIFY, [jar_file])
        self.__execute_command(asm_verify_cmd, "asm_verify")

    def __d2j_apk_sign(self, signed_apk: str, unsigned_apk: str):
        apk_sign_cmd = Command(D2J_APK_SIGN, ['-f', '-o', signed_apk, unsigned_apk])
        self.__execute_command(apk_sign_cmd, "apk_sign", True)

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
        utils.execute_command(cmd, tag, skip_stderr)
        # TODO alterar em todo codigo
        # cmd_result = cmd.invoke(stdout=sys.stdout)  # , stderr=sys.stderr)
        # cond = cmd_result.code != 0
        # if not skip_stderr:
        #     cond = cond or cmd_result.stderr
        # if cond:
        #     #raise CommandException("{0}: {1}. {2}".format(tag, cmd_result.code, cmd_result.stderr))
        #     raise CommandException(tag, cmd_result.code, cmd_result.stderr)

    def __include_generated_monitor(self, out_dir=TMP_DIR):
        logging.info("Including generated RV artifacts ...")
        utils.copy_files(MOP_OUT_DIR, out_dir)

    def __create_apk(self, app: App, work_dir=TMP_DIR, out_dir=INSTRUMENTED_DIR):
        logging.info("Creating instrumented APK ...")
        # Extract (RV-Monitor, RVSec, ...) support classes
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
            # utils.delete_file(jar)
        ## Remove manifests
        metainf_dir = os.path.join(RVM_TMP_DIR, "META-INF")
        utils.delete_dir(metainf_dir)
        # Merge RV-Monitor support classes
        shutil.copytree(RVM_TMP_DIR, out_dir, dirs_exist_ok=True)
        logging.info("Dependencies included in: {}".format(out_dir))
        shutil.rmtree(RVM_TMP_DIR)

    def __d8(self, app: App, monitored_jar: str, out_dir=INSTRUMENTED_DIR):
        # TODO acho q tem esse mesmo comando em outro canto ... ver onde deixar
        utils.create_folder_if_not_exists(out_dir)
        utils.create_folder_if_not_exists(TMP_DIR)

        logging.info("Compiling to DEX: {}".format(monitored_jar))
        # d8_cmd = Command('d8', [monitored_jar, '--release',
        #                         '--lib', self.__get_android_jar(),
        #                         '--min-api', '26',
        #                         '--output', TMP_DIR])
        d8_cmd = Command('d8', [monitored_jar, '--release',
                                '--lib', self.__get_android_jar(),
                                '--min-api', '26'])
        self.__execute_command(d8_cmd, "d8")

        dex_name = 'classes.dex'
        generated_dex = os.path.join(WORKING_DIR, dex_name)
        assert os.path.exists(generated_dex)

        # copy the original apk (as unsigned_apk)
        unsigned_apk_name = "unsigned_{}".format(app.name)
        unsigned_apk = os.path.join(TMP_DIR, unsigned_apk_name)
        logging.info("Copying original APK ({}) to {}".format(app.path, unsigned_apk))
        shutil.copy2(app.path, unsigned_apk)
        # subprocess.Popen(['ls', '-lh', TMP_DIR])
        # shutil.copyfile(app.path, unsigned_apk)
        assert os.path.exists(unsigned_apk)

        # Replace old/original classes.dex in APK with new/genereated classes.dex
        # TODO
        # zip_cmd = Command('zip', ['-r', unsigned_apk, generated_dex])
        # self.__execute_command(zip_cmd, "zip_d8")
        # TODO usar command ... customizar com o cwd
        logging.info("Replacing old 'classes.dex' in: {}".format(unsigned_apk_name))
        # print("out_dir={}".format(out_dir))
        current_dir = os.getcwd()
        print("current_dir={}".format(current_dir))
        # os.chdir(TMP_DIR)
        # print("dir_before={}".format(os.getcwd()))
        subprocess.Popen(['zip', '-u', unsigned_apk, dex_name])  # , cwd=out_dir)#, shell=True)
        # os.chdir(current_dir)
        # print("dir_after={}".format(os.getcwd()))
        # utils.delete_file(generated_dex)

        os.remove(generated_dex)

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

    def __check_if_istrumented(self, app: App, out_dir):
        # TODO checar se o apk foi realmente instrumentado (talvez checando o hash com o original)
        # isso pro caso do __execute_command() nao estar capturando os erros

        hash_original = utils.hash(os.path.join(app.path))
        hash_instrumented = utils.hash(os.path.join(out_dir, app.name))
        if hash_original == hash_instrumented:
            # TODO nao instrumentou ... lancar excecao?
            logging.error("NAO INSTRUMENTOU ....................................")

    def __is_app_already_instrumented(self, app: App, out_dir):
        instrumented_apk = os.path.join(out_dir, app.name)
        return os.path.exists(instrumented_apk)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.info("Executing")

    # apk = "./cryptoapp.apk"
    # apk = "apks/ar.rulosoft.mimanganu_75.apk"
    # apk = "apks/at.bitfire.davdroid_403060100.apk"
    # apk="apks/com.infomaniak.drive_40202501.apk"
    rv_android = RvAndroid()
    # rv_android.instrument(apk, generate_monitors=False)
    rv_android.instrument_apks()
