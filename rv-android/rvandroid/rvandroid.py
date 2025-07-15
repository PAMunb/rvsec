import json
import logging as logging_api
import shutil
import sys
from typing import Dict, Any

from rvandroid.app import App
from rvandroid.commands.command import Command
from rvandroid.commands.command_exception import CommandException
from rvandroid.experiment.event.bus import EventType, EventBus
from rvandroid.util.error import handle_errors
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.exceptions import InstrumentationError
from settings import *

# TODO rever o q eh usado nesse modulo ... talvez jogar tudo em constants.py
EXTENSION_AJ = ".aj"
EXTENSION_DEX = ".dex"
EXTENSION_JAVA = ".java"
EXTENSION_JAR = ".jar"
EXTENSION_MOP = ".mop"
EXTENSION_RVM = ".rvm"

logging = logging_api.getLogger(__name__)


class RvAndroid(object):
    """
    A specialized system for instrumenting and preparing Android APKs for runtime verification and security analysis.

    ### Architectural Decisions:
    - Implements a comprehensive APK instrumentation pipeline
    - Uses advanced decompilation and recompilation techniques
    - Integrates multiple tools for static and dynamic code modification
    - Provides a robust mechanism for injecting monitoring capabilities

    ### Role in the System:
    - Serves as the core instrumentation engine for Android application analysis
    - Transforms standard APKs into instrumentable test artifacts
    - Enables runtime verification by injecting monitoring components
    - Supports automated security and behavior analysis workflows
    - Provides a critical preprocessing step for experimental testing

    ### Key Considerations:
    - Handles complex APK decompilation and recompilation processes
    - Manages library and dependency integration
    - Supports multiple instrumentation strategies
    - Implements comprehensive error handling for instrumentation workflows
    - Ensures minimal disruption to original application behavior

    ### Integration Strategy:
    - Deeply integrated with runtime verification and testing frameworks
    - Compatible with various Android development and testing tools
    - Supports flexible instrumentation configuration
    - Enables seamless injection of monitoring and analysis components
    - Provides standardized instrumentation workflows

    ### Performance and Scalability:
    - Designed for efficient APK transformation
    - Minimizes performance overhead during instrumentation
    - Supports batch processing of multiple APKs
    - Adaptable to different application complexities
    - Provides robust error recovery and reporting mechanisms
    """

    def __init__(self):
        pass

    def instrument_apks(self, results_dir: str, force_instrumentation=False, apks_dir=APKS_DIR) -> Dict[
        str, Dict[str, Any]]:
        """
        Batch instruments multiple APKs with improved error tracking and handling.

        Args:
            results_dir: Directory where instrumented APKs and error logs will be saved
            force_instrumentation: If True, re-instruments APKs even if already processed
            apks_dir: Directory containing APKs to instrument

        Returns:
            Dictionary of instrumentation errors, keyed by APK name, with error details
        """
        errors = {}
        error_handler = ErrorHandler.get_instance()

        # Clean directories, copy libraries and create INSTRUMENTED_DIR (if not exists)
        try:
            self.prepare_instrumentation(results_dir)
        except Exception as e:
            logging.error(f"Failed to prepare instrumentation: {e}")
            error_handler.handle_error(
                InstrumentationError("Failed to prepare instrumentation environment", e),
                {"results_dir": results_dir}
            )
            return {"setup_error": {"code": -1, "message": str(e), "phase": "preparation"}}

        # Retrieve the APKs to be instrumented
        try:
            apks = utils.get_apks(apks_dir)
        except Exception as e:
            logging.error(f"Failed to retrieve APKs: {e}")
            error_handler.handle_error(
                InstrumentationError("Failed to retrieve APKs", e),
                {"apks_dir": apks_dir}
            )
            return {"apk_retrieval_error": {"code": -1, "message": str(e), "phase": "retrieval"}}

        total_apks = len(apks)
        cont = 0
        logging.info(f"Instrumenting {total_apks} apks ...")

        event_bus = EventBus.get_instance()

        for app in apks:
            cont = cont + 1
            logging.info(f"Starting instrumentation {cont}/{total_apks}")

            # Publish instrumentation started event
            # event_bus.publish_experiment_event(
            #     EventType.TOOL_STARTED,
            #     {
            #         "tool_name": "RvAndroid",
            #         "app_name": app.name,
            #         "phase": "instrumentation",
            #         "progress": f"{cont}/{total_apks}"
            #     }
            # )

            try:
                # Instrument the APK with error handling
                with handle_errors({"app_name": app.name, "phase": "instrumentation"}):
                    # Re-instrument if force flag is set or not already instrumented
                    self.instrument(app, results_dir, force_instrumentation)

                    # Check if successfully instrumented
                    self.check_if_instrumented(app)

                    # Publish instrumentation completed event
                    # event_bus.publish_event(
                    #     EventType.TOOL_STOPPED,  # Changed from TOOL_COMPLETED to TOOL_STOPPED
                    #     {
                    #         "tool_name": "RvAndroid",
                    #         "app_name": app.name,
                    #         "phase": "instrumentation",
                    #         "status": "success"
                    #     }
                    # )

            except CommandException as ex:
                logging.error(f"Failed to instrument APK: {app.name}. {ex}")
                errors[app.name] = {"code": ex.code, "tool": ex.tool, "message": ex.message,
                                    "phase": "command_execution"}

                # Handle the error with context
                error_handler.handle_error(
                    InstrumentationError(f"Command execution failed: {ex.message}", ex),
                    {"app_name": app.name, "tool": ex.tool}
                )

                # Publish instrumentation failed event
                # event_bus.publish_event(
                #     EventType.TASK_FAILED,  # Changed from TOOL_FAILED to TASK_FAILED
                #     {
                #         "tool_name": "RvAndroid",
                #         "app_name": app.name,
                #         "phase": "instrumentation",
                #         "error": f"{ex.tool}: {ex.message}"
                #     }
                # )

            except Exception as ex:
                logging.error(f"Error while instrumenting APK: {app.path}. {ex}")
                errors[app.name] = {"code": -1, "message": str(ex), "phase": "general_error"}

                # Handle the general error
                error_handler.handle_error(
                    InstrumentationError(f"Failed to instrument APK: {app.name}", ex),
                    {"app_name": app.name}
                )

                # Publish instrumentation failed event
                # event_bus.publish_event(
                #     EventType.TASK_FAILED,  # Changed from TOOL_FAILED to TASK_FAILED
                #     {
                #         "tool_name": "RvAndroid",
                #         "app_name": app.name,
                #         "phase": "instrumentation",
                #         "error": str(ex)
                #     }
                # )

            finally:
                self.clear([TMP_DIR, RVM_TMP_DIR])

        self.clear([LIB_TMP_DIR])

        if errors:
            logging.warning(f"ERRORS: {len(errors)}")
            errors_file = os.path.join(results_dir, "instrument_errors.json")
            with open(errors_file, 'w') as outfile:
                outfile.write(json.dumps(errors))
                logging.info(f"Errors saved in: {errors_file}")
            for error in errors:
                logging.warning(f"ERROR: {error}, tool={errors[error].get('tool', 'unknown')}")
        return errors

    def prepare_instrumentation(self, results_dir=INSTRUMENTED_DIR):
        self.clear([LIB_TMP_DIR, TMP_DIR, RVM_TMP_DIR])
        self.__execute_maven()
        utils.create_folder_if_not_exists(results_dir)

    def instrument(self, app: App, result_dir=INSTRUMENTED_DIR, force_instrumentation=False):
        """
        Instrument an APK with improved resource management.

        Args:
            app: App to instrument
            result_dir: Directory to store the instrumented APK
            force_instrumentation: Whether to re-instrument if already instrumented
        """
        # check if the APK exists in 'out' dir and whether it is to be instrumented
        instrumented_apk = os.path.join(result_dir, app.name)
        if os.path.exists(instrumented_apk):
            if force_instrumentation:
                logging.info(f"Deleting previously instrumented APK: {instrumented_apk}")
                os.remove(instrumented_apk)
            else:
                logging.info(f"Skipping APK already instrumented: {app.name}")
                return

        start = time.time()
        logging.info(f"Instrumenting: {app.name}")

        # Use a try-finally block to ensure cleanup happens
        try:
            # Create temporary directories if needed
            for directory in [TMP_DIR, RVM_TMP_DIR]:
                if not os.path.exists(directory):
                    os.makedirs(directory)

            self.__decompile_apk(app)
            self.__include_generated_monitors()
            self.__weave_monitors(app)
            signed_apk = self.__create_apk(app)

            if not os.path.exists(signed_apk):
                raise Exception(f"Failed to create signed APK: {signed_apk}")

            end = time.time()
            elapsed = end - start
            logging.info(f'APK instrumented in {utils.to_readable_time(elapsed)}')
            logging.debug(f"APK instrumented: {signed_apk}")

        except Exception as e:
            logging.error(f"Error instrumenting {app.name}: {e}")
            raise

        finally:
            # Clean up temporary directories
            self.clear([TMP_DIR, RVM_TMP_DIR])

    def __decompile_apk(self, app: App):
        """
        Decompile an Android APK into its constituent Java classes.

        This method converts the APK's DEX file to a JAR file, verifies its structure,
        and extracts the classes into a temporary directory for further processing.

        Args:
            app (App): The Android application to be decompiled.
        """
        logging.info("Decompiling: {}".format(app.name))
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
        """
        Weave AspectJ monitors into the application's compiled classes.

        This method uses the AspectJ compiler (ajc) to integrate generated monitor aspects
        into the application's compiled classes. It prepares the classpath, executes the
        AspectJ weaving process, and then cleans up temporary source files.

        Args:
            app (App): The application being instrumented with monitors.
        """
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
        """
        Compile the monitored JAR to DEX format and create an unsigned APK.

        Converts the instrumented JAR to DEX bytecode, copies the original APK,
        replaces the original classes.dex with the new instrumented classes.dex,
        and performs a basic verification of the APK.

        Args:
            app (App): The Android application being processed
            monitored_jar (str): Path to the JAR file containing instrumented classes

        Returns:
            str: Path to the unsigned APK with instrumented classes
        """
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
        # TODO
        self.__d2j_apk_sign(signed_apk, unsigned_apk)
        os.remove(unsigned_apk)
        assert os.path.exists(signed_apk)

        zip_cmd = Command('zip', ['-q', '-d', signed_apk, "META-INF*"])
        utils.execute_command(zip_cmd, "zip_sign_apk")

        self.__jarsigner(signed_apk)
        self.__jarsigner_verify(signed_apk)

        return signed_apk

    @staticmethod
    def clear(folders: list):
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
    def check_if_instrumented(app: App):
        # checks if the apk was actually instrumented, in case __execute_command() is not capturing all errors
        # and ends up returning the original apk as being instrumented
        # TODO resolver problema com tipos
        hash_original = utils.file_hash(os.path.join(app.path))
        hash_instrumented = utils.file_hash(os.path.join(INSTRUMENTED_DIR, app.name))
        if hash_original == hash_instrumented:
            raise CommandException("check", "-1", "App {} was not instrumented.".format(app.name))


if __name__ == '__main__':
    logging_api.basicConfig(stream=sys.stdout, level=logging_api.DEBUG)
    logging_api.info("Executing")

    rv_android = RvAndroid()
    rv_android.instrument_apks(".", force_instrumentation=True)
