import json
import logging as logging_api
import shutil
import sys

import utils
from app import App
from commands.command import Command
from commands.command_exception import CommandException
from settings import *

#TODO rever o q eh usado nesse modulo ... talvez jogar tudo em constants.py
EXTENSION_AJ = ".aj"
EXTENSION_DEX = ".dex"
EXTENSION_JAVA = ".java"
EXTENSION_JAR = ".jar"
EXTENSION_MOP = ".mop"
EXTENSION_RVM = ".rvm"

logging = logging_api.getLogger(__name__)

class RvAndroid(object):

    def __init__(self):
        pass

    def instrument_apks(self, results_dir: str, force_instrumentation=False):
        errors = {}

        # clean directories and copy libraries
        self.__prepare_instrumentation()
        # retrieves the APKs to be instrumented
        apks = utils.get_apks(APKS_DIR)

        total_apks = len(apks)
        cont = 0
        logging.info("Instrumenting {} apks ...".format(total_apks))
        for app in apks:
            cont = cont + 1
            try:
                logging.info("Starting instrumentation {}/{}".format(cont, total_apks))
                # instruments the APK. 'force_instrumentation' indicates whether the APK
                # should be re-instrumented if it is already instrumented
                self.__instrument(app, force_instrumentation)
                # checks if the apk was instrumented
                self.__check_if_instrumented(app)
            except CommandException as ex:
                logging.error("Failed to instrument APK: {}. {}".format(app.name, ex))
                errors[app.name] = {"code": ex.code, "tool": ex.tool, "message": ex.message}
            except Exception as ex:
                logging.error("Error while instrumenting APK: {}. {}".format(app.path, ex))
            finally:
                self.__clear([TMP_DIR, RVM_TMP_DIR])
        self.__clear([LIB_TMP_DIR])

        if errors:
            logging.warning("ERRORS: {}".format(len(errors)))
            errors_file = os.path.join(results_dir, "instrument_errors.json")
            with open(errors_file, 'w') as outfile:
                outfile.write(json.dumps(errors))
                logging.info("Errors saved in 'instrument_errors.json'")
            for error in errors:
                logging.warning("ERROR: {}, tool={}".format(error, errors[error]["tool"]))

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
        # TODO mudar nome do metodo pois nao decompila ... parece q transforma/converte
        self.__decompile_apk(app)
        self.__include_generated_monitors()
        self.__weave_monitors(app)
        signed_apk = self.__create_apk(app)
        assert os.path.exists(signed_apk)
        end = time.time()
        elapsed = end - start
        logging.info('APK instrumented in {0}'.format(utils.to_readable_time(elapsed)))
        logging.debug("APK instrumented: {}".format(signed_apk))

    def __decompile_apk(self, app: App):
        logging.info("Decompiling {}".format(app.name))
        utils.reset_folder(TMP_DIR)
        no_monitor_jar_name = "no_monitor_{}.jar".format(app.name)
        no_monitor_jar = os.path.join(TMP_DIR, no_monitor_jar_name)
        self.__d2j_dex2jar(app, no_monitor_jar)
        assert os.path.exists(no_monitor_jar)
        self.__d2j_asm_verify(no_monitor_jar, skip_verify=True)
        utils.unzip(no_monitor_jar, TMP_DIR)
        utils.delete_file(no_monitor_jar)
        logging.debug("Decompiled classes in: {}".format(TMP_DIR))

    @staticmethod
    def __d2j_dex2jar(app: App, output_jar_file: str):
        tag = "dex2jar"
        exception_file_name = "exception_{}.zip".format(app.name)
        exception_file = os.path.join(TMP_DIR, exception_file_name)
        dex2jar_cmd = Command(D2J_DEX2JAR, ['-f', '-o', output_jar_file, '-e', exception_file, app.path])
        # skips the verification (last argument) of the stderr because dex2jar prints a 'valid' output in stderr
        utils.execute_command(dex2jar_cmd, tag, True)
        if os.path.exists(exception_file):
            raise CommandException(tag, "-1", "See error in {}".format(exception_file))


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
        classpath = [self.__get_android_jar(app)]
        for lib in os.listdir(LIB_TMP_DIR):
            if lib.lower().endswith(EXTENSION_JAR):
                classpath.append(os.path.join(LIB_TMP_DIR, lib))
        return classpath

    @staticmethod
    def __include_generated_monitors():
        logging.info("Including generated RV artifacts")
        utils.copy_files(MOP_OUT_DIR, TMP_DIR)

    def __weave_monitors(self, app: App):
        logging.info("Weaving monitors")
        classpath = self.__get_classpath(app)
        logging.debug("CLASSPATH={}".format(':'.join(classpath)))
        ajc_cmd = Command("ajc", ['-cp', ':'.join(classpath), '-Xlint:ignore',
                                  '-inpath', TMP_DIR, '-d', TMP_DIR,
                                  '-source', '1.8', '-sourceroots', TMP_DIR])
        utils.execute_command(ajc_cmd, "ajc")
        utils.delete_files_by_extension(EXTENSION_JAVA, TMP_DIR)
        utils.delete_files_by_extension(EXTENSION_AJ, TMP_DIR)

    def __create_apk(self, app: App):
        logging.info("Creating instrumented APK ...")
        # Extract/include (RV-Monitor, RVSec, aspectj, ...) support classes
        self.__merge_support_classes()

        # Compress resulting transformed classes to Jar
        utils.reset_folder(RVM_TMP_DIR)
        monitored_jar_name = "monitored_{}.jar".format(app.name)
        monitored_jar = os.path.join(RVM_TMP_DIR, monitored_jar_name)

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

        # TODO setar --min-api com os dados do app???
        d8_cmd = Command('d8', [monitored_jar, '--release',
                                '--lib', self.__get_android_jar(app),
                                '--min-api', '26'])
        # d8_cmd = Command('d8', [monitored_jar, '--release',
        #                         '--lib', self.__get_android_jar(app),
        #                         '--min-api', app.min_api])
        utils.execute_command(d8_cmd, "d8")

        # copy the original apk (as unsigned_apk)
        unsigned_apk_name = "unsigned_{}".format(app.name)
        unsigned_apk = os.path.join(TMP_DIR, unsigned_apk_name)
        logging.debug("Copying original APK ({}) to {}".format(app.path, unsigned_apk))
        shutil.copy2(app.path, unsigned_apk)
        assert os.path.exists(unsigned_apk)

        # Replace old/original classes.dex in APK with new/instrumented classes.dex
        logging.info("Replacing old 'classes.dex' in: {}".format(unsigned_apk_name))
        d8_zip_cmd = Command('zip', ['-u', unsigned_apk, '*' + EXTENSION_DEX])
        utils.execute_command(d8_zip_cmd, "d8_zip")

        # Verify and sign the Jar with debug key, repairing any inconsistent manifests
        self.__d2j_asm_verify(unsigned_apk, skip_verify=True)

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
    def __clear(folders: list):
        for folder in folders:
            logging.debug("Deleting folder: {}".format(folder))
            shutil.rmtree(folder, ignore_errors=True)
        utils.delete_files_by_extension(EXTENSION_DEX, WORKING_DIR)

    @staticmethod
    def __get_android_jar(app: App) -> str:
        # TODO pegar o android.jar dinamicamente de acordo com o target_sdk do app
        # --> baixar dinamicamente a plataforma? ou limitar o range de plataformas possiveis?

        return ANDROID_JAR_PATH

        # platform = "android-{}".format(app.sdk_target)
        # android_jar = os.path.join(ANDROID_PLATFORMS_DIR, platform, 'android.jar')
        #
        # target = str(app.sdk_target)
        # from android import Android
        # if target not in Android.list_installed_platforms():
        #     Android.install_platform(target)
        #
        # if os.path.exists(android_jar):
        #     return android_jar
        # else:
        #     return ANDROID_JAR_PATH

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
        # checks if the apk was actually instrumented, in case __execute_command() is not capturing all errors
        # and ends up returning the original apk as being instrumented
        hash_original = utils.file_hash(os.path.join(app.path))
        hash_instrumented = utils.file_hash(os.path.join(INSTRUMENTED_DIR, app.name))
        if hash_original == hash_instrumented:
            raise CommandException("check", "-1", "App {} was not instrumented.".format(app.name))


if __name__ == '__main__':
    logging_api.basicConfig(stream=sys.stdout, level=logging_api.DEBUG)
    logging_api.info("Executing")

    rv_android = RvAndroid()
    rv_android.instrument_apks(".", force_instrumentation=True)
