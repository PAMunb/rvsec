import logging
import shutil
import sys

import utils
from constants import *
from rvandroid import RvAndroid
from rvsec import RVSec
from settings import *


def execute(specs_dir):
    specs_to_visit = get_specs(specs_dir)
    selected_specs = set()
    specs_with_errors = set()

    while True:
        if len(specs_to_visit) == 0:
            break
        spec = specs_to_visit.pop()
        selected_specs.add(spec)
        copy_specs(selected_specs, specs_dir)
        results_dir = create_results_dir()
        try:
            generate_monitors()
            instrument_apks(results_dir)
        except Exception as ex:
            print("EXCEPTION: {}".format(ex))
            specs_with_errors.add(spec)
            selected_specs.remove(spec)
        finally:
            shutil.rmtree(INSTRUMENTED_DIR, ignore_errors=True)

    print("\n\nERRORS: {}".format(len(specs_with_errors)))
    with open('specs_with_errors.txt', 'w') as file:
        for spec in specs_with_errors:
            file.write(f"{spec}\n")
            print(spec)


def generate_monitors():
    rvsec = RVSec()
    rvsec.generate_monitors()


def instrument_apks(folder):
    rvandroid = RvAndroid()
    rvandroid.prepare_instrumentation()
    apks = utils.get_apks(APKS_DIR)
    total_apks = len(apks)
    cont = 0
    logging.info("Instrumenting {} apks ...".format(total_apks))
    for app in apks:
        cont = cont + 1
        try:
            logging.info("Starting instrumentation {}/{}".format(cont, total_apks))
            rvandroid.instrument(app, False)
            rvandroid.check_if_instrumented(app)
        finally:
            rvandroid.clear([TMP_DIR, RVM_TMP_DIR])
    rvandroid.clear([LIB_TMP_DIR])


def create_results_dir():
    results_dir = os.path.join(RESULTS_DIR, TIMESTAMP)
    utils.create_folder_if_not_exists(results_dir)
    return results_dir


def get_specs(specs_dir):
    specs = set()
    for spec in os.listdir(specs_dir):
        specs.add(spec)
    return specs


def copy_specs(selected_specs, specs_dir):
    utils.delete_files_by_extension(EXTENSION_MOP, MOP_DIR)
    for file_name in selected_specs:
        spec = os.path.join(specs_dir, file_name)
        # print("Copiando: {}".format(spec))
        shutil.copy2(spec, MOP_DIR)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    all_specs_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/mop_tmp"

    start = time.time()

    execute(all_specs_dir)

    end = time.time()
    elapsed = end - start
    logging.info('It took {0} to complete'.format(utils.to_readable_time(elapsed)))
