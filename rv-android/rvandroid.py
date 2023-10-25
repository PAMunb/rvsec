import logging
import shutil
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


class RvAndroid(object):
    """
    this class encapsulates some actions using rvsec and other tools
    """

    def __init__(self):
        pass

    def instrument_apks(self, force_instrumentation=False):
        # temporario
        #TODO salvar os erros (completo) em arquivo separado, via logging
        erros = []

        # clean directories and copy libraries
        self.__prepare_instrumentation()
        # retrieves the APKs to be instrumented
        apks = utils.get_apks(APKS_DIR)
        logging.info("Instrumenting {} apks ...".format(len(apks)))
        for app in apks:
            try:
                # instruments the APK. 'force_instrumentation' indicates whether the APK
                # should be re-instrumented if it is already instrumented
                self.__instrument(app, force_instrumentation)
                # TODO ver se eh realmente necessario
                # compara os hashs do apk original e do instrumentado
                self.__check_if_instrumented(app)
            except CommandException as ex:
                logging.error("Failed to instrument APK: {}. {}".format(app.name, ex))
                erros.append((app.name, ex))
            except Exception as ex:
                logging.error("Error while instrumenting APK: {}. {}".format(app.path, ex))
            finally:
                self.__clear([TMP_DIR, RVM_TMP_DIR])

        print("ERROS: {}".format(len(erros)))
        for erro in erros:
            print("ERRO: {} :: {}".format(erro[0], erro[1].tool))

    def __prepare_instrumentation(self):
        self.__clear([LIB_TMP_DIR, TMP_DIR, RVM_TMP_DIR])
        self.__execute_maven()

    def __instrument(self, app: App, force_instrumentation=False):
        # check if the APK exists in 'out' dir and whether it is to be instrumented
        instrumented_apk = os.path.join(INSTRUMENTED_DIR, app.name)
        if os.path.exists(instrumented_apk):
            if force_instrumentation:
                logging.info("Deleting APK: {}".format(instrumented_apk))
                os.remove(instrumented_apk)
            else:
                logging.info("Skipping APK already instrumented: {}".format(app.name))
                return

        start = time.time()
        logging.info("Instrumenting: {}".format(app.name))
        self.__decompile_apk(app)
        self.__include_generated_monitors()
        self.__weave_monitors(app)
        signed_apk = self.__create_apk(app)
        assert os.path.exists(signed_apk)
        end = time.time()
        elapsed = end - start
        logging.info('APK instrumented in {0}'.format(utils.to_readable_time(elapsed)))
        logging.debug("APK instrumented: {}".format(signed_apk))

    @staticmethod
    def __clear(folders: list):
        for folder in folders:
            logging.debug("Deleting folder: {}".format(folder))
            shutil.rmtree(folder, ignore_errors=True)
        # TODO atributo da classe ... ou arrumar outra forma de pegar o classes.dex aqui e no d8()
        dex_name = 'classes.dex'
        generated_dex = os.path.join(WORKING_DIR, dex_name)
        if os.path.exists(generated_dex):
            logging.debug("Deleting: {}".format(generated_dex))
            os.remove(generated_dex)

    def __weave_monitors(self, app: App):
        logging.info("Weaving monitors")
        logging.debug("AJC inpath: {}".format(TMP_DIR))
        classpath = self.__get_classpath(app)
        logging.debug("CLASSPATH={}".format(':'.join(classpath)))
        ajc_cmd = Command("ajc", ['-cp', ':'.join(classpath), '-Xlint:ignore',
                                  '-inpath', TMP_DIR, '-d', TMP_DIR,
                                  '-source', '1.8', '-sourceroots', TMP_DIR])
        utils.execute_command(ajc_cmd, "ajc")
        utils.delete_files_by_extension(EXTENSION_JAVA, TMP_DIR)
        utils.delete_files_by_extension(EXTENSION_AJ, TMP_DIR)

    def __decompile_apk(self, app: App):
        logging.info("Decompiling {}".format(app.name))
        utils.reset_folder(TMP_DIR)
        no_monitor_jar_name = "no_monitor_{}.jar".format(app.name)
        no_monitor_jar = os.path.join(TMP_DIR, no_monitor_jar_name)
        # TODO como o d2j lida com multidex? e como vamos lidar aqui?
        self.__d2j_dex2jar(app, no_monitor_jar)
        assert os.path.exists(no_monitor_jar)
        self.__d2j_asm_verify(no_monitor_jar, skip_verify=True)
        utils.unzip(no_monitor_jar, TMP_DIR)
        utils.delete_file(no_monitor_jar)
        logging.debug("Decompiled classes in: {}".format(TMP_DIR))

    @staticmethod
    def __d2j_dex2jar(app: App, output_jar_file: str):
        dex2jar_cmd = Command(D2J_DEX2JAR, ['-f', '-o', output_jar_file, app.path])
        # skips the verification (last argument) of the stderr because dex2jar prints an 'valid' output in stderr
        utils.execute_command(dex2jar_cmd, "dex2jar", True)

    @staticmethod
    def __d2j_asm_verify(jar_file: str, skip_verify=False):
        if skip_verify:
            return
        asm_verify_cmd = Command(D2J_ASM_VERIFY, [jar_file])
        utils.execute_command(asm_verify_cmd, "asm_verify")

    @staticmethod
    def __d2j_apk_sign(signed_apk: str, unsigned_apk: str):
        apk_sign_cmd = Command(D2J_APK_SIGN, ['-f', '-o', signed_apk, unsigned_apk])
        # utils.execute_command(apk_sign_cmd, "apk_sign", True)
        utils.execute_command(apk_sign_cmd, "apk_sign")

    @staticmethod
    def __execute_maven():
        # run maven to copy the libraries (dependencies) to LIB_TMP_DIR
        # pom.xml must be in sync with settings.py (pointing to the same dir)
        maven_cmd = Command('mvn', ['clean', 'compile'])
        utils.execute_command(maven_cmd, "maven")

    def __get_classpath(self, app: App):
        # TODO pegar o android.jar dinamicamente de acordo com o target_sdk do app?
        classpath = [self.__get_android_jar()]
        for lib in os.listdir(LIB_TMP_DIR):
            if lib.lower().endswith(EXTENSION_JAR):
                classpath.append(os.path.join(LIB_TMP_DIR, lib))
        return classpath

    @staticmethod
    def __include_generated_monitors():
        logging.info("Including generated RV artifacts")
        utils.copy_files(MOP_OUT_DIR, TMP_DIR)

    def __create_apk(self, app: App):
        logging.info("Creating instrumented APK ...")
        # Extract/include (RV-Monitor, RVSec, aspectj, ...) support classes
        self.__merge_support_classes()

        # Compress resulting transformed classes to Jar
        utils.reset_folder(RVM_TMP_DIR)
        monitored_jar_name = "monitored_{}.jar".format(app.name)
        monitored_jar = os.path.join(RVM_TMP_DIR, monitored_jar_name)
        # TODO rever esse balaio de gato
        utils.zip_dir_content(monitored_jar, TMP_DIR)
        shutil.move(monitored_jar, TMP_DIR)
        shutil.rmtree(RVM_TMP_DIR)
        monitored_jar = os.path.join(TMP_DIR, monitored_jar_name)
        logging.debug("Classes compressed: {}".format(monitored_jar))

        # Compile classes in Jar to Dex format
        unsigned_apk = self.__d8(app, monitored_jar)
        assert os.path.exists(unsigned_apk)

        # TODO: zipalign?

        # Sign the apk
        return self.__sign_apk(app, unsigned_apk)

    @staticmethod
    def __merge_support_classes():
        # (temp) directory where the libraries will be unzipped
        utils.reset_folder(RVM_TMP_DIR)
        jars = ["rv-monitor-rt.jar", "rvsec-core.jar", "rvsec-logger-logcat.jar", "aspectjrt.jar"]
        logging.info("Including runtime dependencies")
        for jar_name in jars:
            logging.debug("Including: {}".format(jar_name))
            jar = os.path.join(LIB_TMP_DIR, jar_name)
            utils.unzip(jar, RVM_TMP_DIR)
        # Remove manifests
        metainf_dir = os.path.join(RVM_TMP_DIR, "META-INF")
        utils.delete_dir(metainf_dir)
        # Merge support classes
        shutil.copytree(RVM_TMP_DIR, TMP_DIR, dirs_exist_ok=True)
        logging.debug("Dependencies included in: {}".format(TMP_DIR))
        shutil.rmtree(RVM_TMP_DIR)

    def __d8(self, app: App, monitored_jar: str):
        logging.info("Compiling to DEX")
        # d8_cmd = Command('d8', [monitored_jar, '--release',
        #                         '--lib', self.__get_android_jar(),
        #                         '--min-api', '26',
        #                         '--output', TMP_DIR])
        # TODO setar --min-api com os dados do apk???
        d8_cmd = Command('d8', [monitored_jar, '--release',
                                '--lib', self.__get_android_jar(),
                                '--min-api', '26'])
        utils.execute_command(d8_cmd, "d8")

        dex_name = 'classes.dex'
        generated_dex = os.path.join(WORKING_DIR, dex_name)
        assert os.path.exists(generated_dex)

        # copy the original apk (as unsigned_apk)
        unsigned_apk_name = "unsigned_{}".format(app.name)
        unsigned_apk = os.path.join(TMP_DIR, unsigned_apk_name)
        logging.debug("Copying original APK ({}) to {}".format(app.path, unsigned_apk))
        shutil.copy2(app.path, unsigned_apk)
        # subprocess.Popen(['ls', '-lh', TMP_DIR])
        # shutil.copyfile(app.path, unsigned_apk)
        assert os.path.exists(unsigned_apk)

        # Replace old/original classes.dex in APK with new/genereated classes.dex
        # TODO
        # zip_cmd = Command('zip', ['-r', unsigned_apk, generated_dex])
        # utils.execute_command(zip_cmd, "zip_d8")
        # TODO usar command ... customizar com o cwd
        logging.info("Replacing old 'classes.dex' in: {}".format(unsigned_apk_name))
        # print("out_dir={}".format(out_dir))
        # current_dir = os.getcwd()
        # print("current_dir={}".format(current_dir))
        # os.chdir(TMP_DIR)
        # print("dir_before={}".format(os.getcwd()))
        # subprocess.Popen(['zip', '-u', unsigned_apk, dex_name])  # , cwd=out_dir)#, shell=True)
        d8_zip_cmd = Command('zip', ['-u', unsigned_apk, dex_name])
        utils.execute_command(d8_zip_cmd, "d8_zip")
        # os.chdir(current_dir)
        # print("dir_after={}".format(os.getcwd()))
        # utils.delete_file(generated_dex)

        os.remove(generated_dex)

        # Verify and sign the Jar with debug key, repairing any inconsistent manifests
        self.__d2j_asm_verify(unsigned_apk)

        return unsigned_apk

    def __sign_apk(self, app: App, unsigned_apk: str):
        utils.create_folder_if_not_exists(INSTRUMENTED_DIR)

        logging.info("Signing APK")
        logging.debug("APK: {}".format(unsigned_apk))
        # Sign debug Jar with final key
        signed_apk = os.path.join(INSTRUMENTED_DIR, app.name)
        self.__d2j_apk_sign(signed_apk, unsigned_apk)
        os.remove(unsigned_apk)
        assert os.path.exists(signed_apk)

        zip_cmd = Command('zip', ['-q', '-d', signed_apk, "META-INF*"])
        utils.execute_command(zip_cmd, "zip_sign_apk")

        self.__jarsigner(signed_apk)
        self.__jarsigner_verify(signed_apk)

        return signed_apk

    @staticmethod
    def __get_android_jar() -> str:
        # TODO pegar o android.jar dinamicamente de acordo com o target_sdk do app
        return ANDROID_JAR_PATH

    @staticmethod
    def __jarsigner(signed_apk):
        jarsigner_cmd = Command('jarsigner',
                                ['-sigalg', 'SHA256withRSA', '-digestalg', 'SHA-256', '-keystore', KEYSTORE_FILE,
                                 signed_apk, 'server', '-storepass', KEYSTORE_PASSWORD])
        utils.execute_command(jarsigner_cmd, "jarsigner")

    @staticmethod
    def __jarsigner_verify(signed_apk):
        jarsigner_cmd = Command('jarsigner', ['-verify', '-certs', signed_apk])
        utils.execute_command(jarsigner_cmd, "jarsigner_verify")

    @staticmethod
    def __check_if_instrumented(app: App):
        # TODO checar se o apk foi realmente instrumentado (talvez checando o hash com o original)
        # isso pro caso do __execute_command() nao estar capturando os erros

        hash_original = utils.file_hash(os.path.join(app.path))
        hash_instrumented = utils.file_hash(os.path.join(INSTRUMENTED_DIR, app.name))
        if hash_original == hash_instrumented:
            # TODO nao instrumentou ... lancar excecao?
            logging.error("NAO INSTRUMENTOU ....................................")


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.info("Executing")

    rv_android = RvAndroid()
    rv_android.instrument_apks(force_instrumentation=True)
