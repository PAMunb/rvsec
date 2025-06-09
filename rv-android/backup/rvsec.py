import logging as logging_api

from rvandroid.commands.command import Command
from rvandroid.constants import *
from settings import *

logging = logging_api.getLogger(__name__)


class RVSec(object):
    """
    The RVSec class encapsulates runtime verification (RV) techniques, integrating
    JavaMOP and RV-Monitor to analyze application behavior. It automates the process
    of generating and applying monitoring specifications to instrumented Android apps.

    ### Architectural Decisions:
    - Uses JavaMOP to generate runtime monitoring specifications.
    - Integrates RV-Monitor to enforce verification at runtime.
    - Ensures that all monitored behaviors are logged for analysis.

    ### Role in the System:
    - Enhances security testing by verifying runtime properties of Android applications.
    - Automates the instrumentation process, allowing real-time validation of app behavior.
    - Plays a crucial role in detecting policy violations in running applications.
    """

    def __init__(self):
        pass

    def generate_monitors(self):
        """
        Generates runtime verification monitors by executing JavaMOP and RV-Monitor.

        This method prepares the output directory, then invokes JavaMOP and RV-Monitor
        to create monitoring specifications for runtime verification of Android applications.
        It logs the process and resets the monitor output directory before generation.
        """
        logging.info("Generating Monitors ...")
        logging.debug("Recreating {}".format(MOP_OUT_DIR))
        utils.reset_folder(MOP_OUT_DIR)
        self.__java_mop()
        self.__rv_monitor()

    @staticmethod
    def __java_mop():
        logging.info("Executing JavaMOP")
        logging.info(f"MOP specs dir: {MOP_DIR}")
        mop_files = os.path.join(MOP_DIR, '*' + EXTENSION_MOP)
        javamop_cmd = Command(JAVAMOP_BIN, ['-d', MOP_OUT_DIR, '-merge', mop_files])
        utils.execute_command(javamop_cmd, "javamop")
        # the option '-d' is not working 100% (moves generated *.aj to MOP_OUT_DIR, but not the rvm files)
        utils.move_files_by_extension(EXTENSION_RVM, MOP_DIR, MOP_OUT_DIR)
        # copy any custom aspectj file (from MOP_DIR and ASPECTS_DIR) to MOP_OUT_DIR
        # utils.copy_files_by_extension(EXTENSION_AJ, MOP_DIR, MOP_OUT_DIR, log_info=True)
        utils.copy_files_by_extension(EXTENSION_AJ, ASPECTS_DIR, MOP_OUT_DIR, log_info=True)

    @staticmethod
    def __rv_monitor():
        logging.info("Executing RV-Monitor")
        rvm_files = os.path.join(MOP_OUT_DIR, '*' + EXTENSION_RVM)
        rvmonitor_cmd = Command(RV_MONITOR_BIN, ['-d', MOP_OUT_DIR, '-merge', rvm_files])
        utils.execute_command(rvmonitor_cmd, "rvmonitor")
        # delete the .rvm files generated and already used by rv-monitor
        utils.delete_files_by_extension(EXTENSION_RVM, MOP_OUT_DIR)
