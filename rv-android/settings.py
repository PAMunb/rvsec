import os
import time

TIMESTAMP = time.strftime("%Y%m%d%H%M%S", time.localtime())

START = time.time()

WORKING_DIR = os.getcwd()

APKS_DIR = os.path.join(WORKING_DIR, 'apks_mini')
RESULTS_DIR = os.path.join(WORKING_DIR, 'results')
INSTRUMENTED_DIR = os.path.join(WORKING_DIR, 'out')
INSTRUMENTED_DIR_DROIDFAX = os.path.join(WORKING_DIR, 'instrumented-droidfax')
LIB_DIR = os.path.join(WORKING_DIR, 'lib')

TMP_DIR = os.path.join(WORKING_DIR, 'tmp')
LIB_TMP_DIR = os.path.join(WORKING_DIR, 'lib_tmp')
RVM_TMP_DIR = os.path.join(WORKING_DIR, 'rvm_tmp')

RVSEC_ROOT_DIR = os.path.join(WORKING_DIR, os.path.abspath('..'))
JAVAMOP_HOME = os.path.join(RVSEC_ROOT_DIR, 'javamop')
JAVAMOP_BIN = os.path.join(JAVAMOP_HOME, 'bin', 'javamop')
RV_MONITOR_HOME = os.path.join(RVSEC_ROOT_DIR, 'rv-monitor')
RV_MONITOR_BIN = os.path.join(RV_MONITOR_HOME, 'bin', 'rv-monitor')
RVSEC_DIR = os.path.join(RVSEC_ROOT_DIR, 'rvsec')

# MOP_DIR = os.path.join(RVSEC_DIR, 'rvsec-mop', 'src', 'main', 'resources')
MOP_DIR = os.path.join(WORKING_DIR, 'mop_mini')
MOP_OUT_DIR = os.path.join(WORKING_DIR, 'mop_out')

D2J_HOME = os.path.join(LIB_DIR, 'dex2jar')
D2J_DEX2JAR = os.path.join(D2J_HOME, 'd2j-dex2jar.sh')
D2J_ASM_VERIFY = os.path.join(D2J_HOME, 'd2j-asm-verify.sh')
D2J_APK_SIGN = os.path.join(D2J_HOME, 'd2j-apk-sign.sh')

AVD_NAME = "RVSec"

ANDROID_PLATFORM = 'android-29'
ANDROID_SDK_HOME = os.getenv('ANDROID_HOME')
ANDROID_PLATFORM_LIB = os.path.join(ANDROID_SDK_HOME, 'platforms', ANDROID_PLATFORM)
ANDROID_JAR_PATH = os.path.join(ANDROID_PLATFORM_LIB, 'android.jar')

KEYSTORE_FILE = os.path.join(WORKING_DIR, 'keystore.jks')
