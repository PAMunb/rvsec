import re
import shutil
import tempfile

temp_dirs = []


def make_temp_dir(prefix=''):
    global temp_dirs
    directory = tempfile.mkdtemp(prefix=prefix)
    temp_dirs.append(directory)
    return directory


def remove_temp_dirs():
    global temp_dirs
    for directory in temp_dirs:
        shutil.rmtree(directory, ignore_errors=True)
        

def extract_number(cur_line):
    pattern = r'\d+'
    result = re.search(pattern, cur_line)
    if result:
        return int(result.group())
    else:
        return -1


def extract_target_api(yml_path):
    with open(yml_path, 'r') as fd:
        for line in fd.readlines():
            if 'targetSdkVersion' in line:               
                return extract_number(line)
    return -1
