#!/bin/env python3
import os, sys, shutil, subprocess, re, time, socket, configparser, packaging, packaging.version, packaging.specifiers, packaging.requirements
from qlearning_final_coverage_multi import QLearning
from util.coverage_curve_util import calculate_coverage
TEST_INDEX = 1
APK_NAME = ''
APP_SOURCE_PATH = ''
Benchmark = ''
DEVICE_ID = ''

def start_apk(is_instrument):
    cmd = 'adb -s ' + DEVICE_ID + ' root'
    os.system(cmd)
    cmd = 'aapt dump badging ' + Benchmark + APK_NAME + '| grep "package"'
    package_info = subprocess.getoutput(cmd)
    print(('package_info is ' + package_info))
    pattern = re.compile("name='(\\S+)'")
    package_name = re.findall(pattern, package_info)[0]
    cmd = 'aapt dump badging ' + Benchmark + APK_NAME + '| grep "launchable"'
    activity_info = subprocess.getoutput(cmd)
    print(('activity_info is ' + activity_info))
    if activity_info == '':
        activity_info = "name='noactivityname'"
    pattern = re.compile("name='(\\S+)'")
    activity_name = re.findall(pattern, activity_info)[0]
    if is_instrument:
        cmd = 'adb -s ' + DEVICE_ID + ' shell am instrument ' + package_name + '/' + package_name + '.JacocoInstrumentation'
        os.system(cmd)
    else:
        cmd = 'adb -s ' + DEVICE_ID + ' shell am start -S -n ' + package_name + '/' + activity_name
        os.system(cmd)
    return (
     package_name, activity_name)


def setup_env():
    file_path = Benchmark + APK_NAME.split('.')[0] + '-output-' + str(TEST_INDEX)
    if os.path.isdir(file_path):
        shutil.rmtree(file_path)
    os.mkdir(file_path)
    os.mkdir(file_path + '/event_output')
    os.mkdir(file_path + '/coverage_merge_' + str(TEST_INDEX))
    os.mkdir(file_path + '/coverage_original_' + str(TEST_INDEX))
    os.mkdir(file_path + '/coverage_new_' + str(TEST_INDEX))


def start_log():
    log_file = Benchmark + APK_NAME.split('.')[0] + '-output-' + str(TEST_INDEX) + '/crash_log.txt'
    log_filter = 'AndroidRuntime:E CrashAnrDetector:D ActivityManager:E SQLiteDatabase:E WindowManager:E ActivityThread:E Parcel:E *:F *:S'
    cmd = 'adb -s ' + DEVICE_ID + ' logcat -c'
    os.system(cmd)
    cmd = 'adb -s ' + DEVICE_ID + ' logcat ' + log_filter + ' >> ' + log_file + ' &'
    os.system(cmd)


def start_dump_coverage(package_name):
    dumped_coverag_dir = Benchmark + APK_NAME.split('.')[0] + '-output-' + str(TEST_INDEX) + '/coverage_original_' + str(TEST_INDEX)
    cmd = './util/dumpCoverage.sh ' + dumped_coverag_dir + ' ' + DEVICE_ID + ' ' + package_name + '&>' + ' ' + dumped_coverag_dir + '/icoverage.log &'
    os.system(cmd)


def post_process(package_name):
    cmd = 'for pid in $(ps aux | grep "[-]s ' + DEVICE_ID + ' logcat" | awk \'{print $2}\'); do kill -9 $pid; done'
    os.system(cmd)
    cmd = 'for pid in $(ps aux | grep dumpCoverage | grep ' + DEVICE_ID + ' | grep -v grep' + " | awk '{print $2}'); do kill -9 $pid; done"
    os.system(cmd)


def main(is_instrument, config_file):
    setup_env()
    start_log()
    package_name, activity_name = start_apk(is_instrument)
    if is_instrument:
        start_dump_coverage(package_name)
    print(('app_name is ' + APK_NAME.split('.')[0]))
    qlearning = QLearning(package_name, APK_NAME.split('.')[0], activity_name, APP_SOURCE_PATH, Benchmark + APK_NAME, is_instrument, config_file)
    qlearning.qlearning_loop()
    post_process(package_name)


def print_error_msg(msg):
    print(msg)
    exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print_error_msg('[Error] Q-testing take 2 arguments')
    if sys.argv[1] != '-r' and sys.argv[1] != '-c':
        print_error_msg("[Error] first argument should be '-r' or '-c'")
    else:
        path_to_config = os.path.abspath(sys.argv[2])
        print(path_to_config)
        if not os.path.exists(path_to_config):
            print_error_msg('[Error] no such file ' + sys.argv[2])
    bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    path_to_config = os.path.abspath(sys.argv[2])
    config = configparser.ConfigParser()
    config.read(path_to_config)
    APK_NAME = config.get('Path', 'APK_NAME')
    Benchmark = config.get('Path', 'Benchmark')
    DEVICE_ID = config.get('Setting', 'DEVICE_ID')
    TEST_INDEX = int(config.get('Setting', 'TEST_INDEX'))
    if not Benchmark.endswith('/'):
        Benchmark = Benchmark + '/'
    if sys.argv[1] == '-r':
        apk_abs_path = os.path.join(Benchmark, APK_NAME)
        if not os.path.exists(apk_abs_path):
            print_error_msg('[Error] no such file ' + apk_abs_path)
        is_instrument = False
        apk_name = APK_NAME.split('.')[0]
        if len(apk_name) > 6 and apk_name.endswith('-debug'):
            is_instrument = True
            APP_SOURCE_PATH = config.get('Path', 'APP_SOURCE_PATH')
            if not os.path.exists(APP_SOURCE_PATH):
                print_error_msg('[Error] no such dir ' + APP_SOURCE_PATH)
        main(is_instrument, sys.argv[2])
    else:
        calculate_coverage()
