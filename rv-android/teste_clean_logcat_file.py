import glob
import os

def execute(base_dir):
    for logcat_file in find_logcat_files(base_dir):
        clean_file(logcat_file)


def clean_file(logcat_file):
    print("***** Cleaning file: {}".format(logcat_file))
    data = set()

    with open(logcat_file, 'r') as file_in:
        for line in file_in.readlines():
            data.add(line)
    print("Quantidade de msgs: {}". format(len(data)))

    print("Salvando arquivo ...")
    with open(logcat_file, 'w') as file_out:
        file_out.writelines(data)
    print("Arquivo salvo!!!")


def find_logcat_files(base_dir):
    logcat_files = set()
    for filename in os.listdir(base_dir):
        if filename.endswith(".logcat"):
            filepath = os.path.join(base_dir, filename)
            logcat_files.add(filepath)
    return logcat_files


if __name__ == '__main__':
    apk_result_dir = "/home/pedro/desenvolvimento/RV_ANDROID/RESULTS_experimento01_novas_specs_new_tools/24/20240830173329/org.mupen64plusae.v3.alpha_246.apk"

    execute(apk_result_dir)
