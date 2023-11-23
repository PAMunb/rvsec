import logging as logging_api

import utils
from commands.command import Command
from settings import *
from constants import *


logging = logging_api.getLogger(__name__)


class RVSec(object):
    """
    this class encapsulates some actions using rvsec
    """

    def __init__(self):
        pass

    def generate_monitors(self):
        logging.info("Generating Monitors ...")
        logging.debug("Recreating {}".format(MOP_OUT_DIR))
        utils.reset_folder(MOP_OUT_DIR)
        self.__java_mop()
        self.__rv_monitor()

    @staticmethod
    def __java_mop():
        logging.info("Executing JavaMOP")
        mop_files = os.path.join(MOP_DIR, '*' + EXTENSION_MOP)
        javamop_cmd = Command(JAVAMOP_BIN, ['-d', MOP_OUT_DIR, '-merge', mop_files])
        utils.execute_command(javamop_cmd, "javamop")
        # the option '-d' is not working 100% (moves generated *.aj to MOP_OUT_DIR, but not the rvm files)
        utils.move_files_by_extension(EXTENSION_RVM, MOP_DIR, MOP_OUT_DIR)
        # copy any custom aspectj file (from MOP_DIR) to MOP_OUT_DIR
        utils.copy_files_by_extension(EXTENSION_AJ, MOP_DIR, MOP_OUT_DIR, log_info=True)

    @staticmethod
    def __rv_monitor():
        logging.info("Executing RV-Monitor")
        rvm_files = os.path.join(MOP_OUT_DIR, '*' + EXTENSION_RVM)
        rvmonitor_cmd = Command(RV_MONITOR_BIN, ['-d', MOP_OUT_DIR, '-merge', rvm_files])
        utils.execute_command(rvmonitor_cmd, "rvmonitor")
        # delete the .rvm files generated and already used by rv-monitor
        utils.delete_files_by_extension(EXTENSION_RVM, MOP_OUT_DIR)
