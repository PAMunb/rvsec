import os
import time
from pathlib import Path

from rvandroid import utils
from rvandroid.constants import ENV_JCA_SPEC, ENV_RT_JAR, ENV_RVANDROID_URL

TIMESTAMP = time.strftime("%Y%m%d%H%M%S", time.localtime())

START = time.time()

WORKING_DIR = os.getcwd()

# APKS_DIR = os.path.join(WORKING_DIR, "apks")
# APKS_DIR = os.path.join(WORKING_DIR, "apks_mini")
APKS_DIR = os.path.join(WORKING_DIR, "apks_examples")
RESULTS_DIR = os.path.join(WORKING_DIR, "results")
INSTRUMENTED_DIR = os.path.join(WORKING_DIR, "out")
LIB_DIR = os.path.join(WORKING_DIR, "lib")
TOOLS_DIR = os.path.join(WORKING_DIR, "rvandroid", "tools")

TMP_DIR = os.path.join(WORKING_DIR, "tmp")
LIB_TMP_DIR = os.path.join(WORKING_DIR, "lib_tmp")
RVM_TMP_DIR = os.path.join(WORKING_DIR, "rvm_tmp")

RVSEC_ROOT_DIR = os.path.join(WORKING_DIR, os.path.abspath(".."))
JAVAMOP_HOME = os.path.join(RVSEC_ROOT_DIR, "javamop")
JAVAMOP_BIN = os.path.join(JAVAMOP_HOME, "bin", "javamop")
RV_MONITOR_HOME = os.path.join(RVSEC_ROOT_DIR, "rv-monitor")
RV_MONITOR_BIN = os.path.join(RV_MONITOR_HOME, "bin", "rv-monitor")
RVSEC_DIR = os.path.join(RVSEC_ROOT_DIR, "rvsec")

MOP_BASE_DIR = os.path.join(RVSEC_DIR, "rvsec-mop", "src", "main", "resources")
MOP_JCA_DIR = os.path.join(MOP_BASE_DIR, "jca")
MOP_GENERIC_DIR = os.path.join(MOP_BASE_DIR, "generic")
IS_JCA = utils.get_env_or_default(ENV_JCA_SPEC, True, bool)
MOP_DIR = MOP_JCA_DIR if IS_JCA else MOP_GENERIC_DIR
# MOP_DIR = MOP_GENERIC_DIR
ASPECTS_DIR = os.path.join(MOP_BASE_DIR, "aspect")
MOP_OUT_DIR = os.path.join(WORKING_DIR, "mop_out")
# TODO (coverage.aj)
MOP_INCLUDE_DIR = os.path.join(WORKING_DIR, "mop-include")

D2J_HOME = os.path.join(LIB_DIR, "dex2jar")
D2J_DEX2JAR = os.path.join(D2J_HOME, "d2j-dex2jar.sh")
D2J_ASM_VERIFY = os.path.join(D2J_HOME, "d2j-asm-verify.sh")
D2J_APK_SIGN = os.path.join(D2J_HOME, "d2j-apk-sign.sh")

AVD_NAME = "RVSec"

ANDROID_PLATFORM = "android-29"
ANDROID_SDK_HOME = os.getenv("ANDROID_HOME")
ANDROID_PLATFORMS_DIR = os.path.join(ANDROID_SDK_HOME, "platforms")
ANDROID_PLATFORM_LIB = os.path.join(ANDROID_PLATFORMS_DIR, ANDROID_PLATFORM)
ANDROID_JAR_PATH = os.path.join(ANDROID_PLATFORM_LIB, "android.jar")

KEYSTORE_FILE = os.path.join(WORKING_DIR, "keystore.jks")
KEYSTORE_PASSWORD = "password"

#RT_JAR = os.path.join(Path.home(), ".sdkman", "candidates", "java", "8.0.302-open", "jre", "lib", "rt.jar")
RT_JAR = utils.get_env_or_default(ENV_RT_JAR, os.path.join(Path.home(), ".sdkman", "candidates", "java", "8.0.302-open", "jre", "lib", "rt.jar"), str)
RVANDROID_URL = utils.get_env_or_default(ENV_RVANDROID_URL, "http://127.0.0.1:5000", str)
