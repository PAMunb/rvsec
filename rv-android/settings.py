import os
import time

TIMESTAMP = time.strftime("%Y%m%d%H%M%S", time.localtime())

START = time.time()

WORKING_DIR = os.getcwd()
MOP_DIR = os.path.join(WORKING_DIR, 'mop')
APKS_DIR = os.path.join(WORKING_DIR, 'apks')
RESULTS_DIR = os.path.join(WORKING_DIR, 'results')
INSTRUMENTED_DIR = os.path.join(WORKING_DIR, 'out')

AVD_NAME = "RVSec"
