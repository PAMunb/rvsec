import logging
import os
import time

from abc import abstractmethod
from app import App
from constants import KEYSTORE, KEYSTORE_PASSWORD, KEYSTORE_ALIAS
from settings import TIMESTAMP, START, ANDROID_JAR_PATH, RESULTS_DIR, WORKING_DIR
from commands.command import Command

class Instrumenter(object):
    """
    The base class of all events
    """
    def __init__(self):
        droidfax_libs = os.path.join(WORKING_DIR, 'lib', 'droidfax')
        libs = list(map(lambda dep: os.path.join(droidfax_libs, dep), os.listdir(droidfax_libs)))
        self.main_cp = ':'.join(libs)
        droidfax_jar = os.path.join(droidfax_libs, 'droidfax.jar')
        self.soot_cp = "{0}:{1}".format(droidfax_jar, ANDROID_JAR_PATH)

    def instrument(self, app: App, out_dir: str):
        raise NotImplementedError

class DroidFaxInstrumenter(Instrumenter):

    def instrument(self, app: App, out_dir: str):
        start = time.time()

        # Instrument app
        instrument_cmd_args = [
            '-Xmx14g',
            '-ea',
            '-cp',
            self.main_cp,
            'dynCG.sceneInstr',
            '-w',
            '-cp',
            self.soot_cp,
            '-p',
            'cg',
            'verbose:false,implicit-entry:true',
            '-p',
            'cg.spark',
            'verbose:false,on-fly-cg:true,rta:false',
            '-d',
            os.path.join(out_dir),
            '-instr3rdparty',
            '-process-dir',
            os.path.join(app.path)
        ]

        # if catch_arguments:
        #     logging.info('Selected instrumentation will add argument catching')
        #     instrument_cmd_args.extend([
        #         '-monitorApiCalls',
        #         '-catsink',
        #         os.path.join(WORKING_DIR, 'data', 'catsinks.txt.final'),
        #     ])
        instrument_cmd = Command('java', instrument_cmd_args, 1200)
        instrument_result = instrument_cmd.invoke()

        end = time.time()
        logging.info('Static analisys finished. Elapsed time: {0}'.format(end - start))

        # Signing instrumented app
        logging.info('Signing {0}'.format(app.name))
        sign_cmd = Command('jarsigner', [
            '-verbose',
            '-sigalg',
            'SHA1withRSA',
            '-digestalg',
            'SHA1',
            '-storepass',
            KEYSTORE_PASSWORD,
            '-keystore',
            KEYSTORE,
            os.path.join(out_dir, app.name),
            KEYSTORE_ALIAS
        ])
        sign_result = sign_cmd.invoke()

        logging.info('Verify the signature just added')
        verify_cmd = Command('jarsigner', [
            '-verify',
            '-verbose',
            '-certs',
            os.path.join(out_dir, app.name)
        ])
        verify_result = verify_cmd.invoke()


# class JavaMOPInstrumenter(Instrumenter):
#
#     def instrument(self, app: App, out_dir: str):