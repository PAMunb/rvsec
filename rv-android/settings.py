import os
import time

TIMESTAMP = time.strftime("%Y%m%d%H%M%S", time.localtime())

START = time.time()

WORKING_DIR = os.getcwd()

APKS_DIR = os.path.join(WORKING_DIR, 'apks')
RESULTS_DIR = os.path.join(WORKING_DIR, 'results')
INSTRUMENTED_DIR = os.path.join(WORKING_DIR, 'out')

MOP_DIR = os.path.join(WORKING_DIR, 'mop_mini')
MOP_OUT_DIR = os.path.join(WORKING_DIR, 'mop_out')

RVSEC_DIR=os.path.join(WORKING_DIR, os.path.abspath('..'))
JAVAMOP_HOME=os.path.join(RVSEC_DIR, 'javamop')
JAVAMOP_BIN=os.path.join(JAVAMOP_HOME, 'bin', 'javamop')
RV_MONITOR_HOME=os.path.join(RVSEC_DIR, 'rv-monitor')
RV_MONITOR_BIN=os.path.join(RV_MONITOR_HOME, 'bin', 'rv-monitor')


AVD_NAME = "RVSec"
