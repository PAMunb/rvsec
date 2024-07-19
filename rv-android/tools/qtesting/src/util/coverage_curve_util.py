import os, shutil, xml, xml.dom.minidom, re, collections, configparser, sys
APP_SOURCE_FILE = ''
APK_NAME = ''
Benchmark = ''
MANIFEST_FILE = ''
TARGET_BASED_COVERAGE_FILE = ''
ORIGINAL_COVERAGE_FILE = ''
NEW_COVERAGE_FILE = ''
TIME_INTERVAL = 30
MAX_ID = 0

def copy_restart_coverage_file(target_based_coverage_file, original_coverage_file):
    file_list = os.listdir(target_based_coverage_file)
    if not file_list:
        return
    for f in file_list:
        if '.ec' in f:
            shutil.copy2(os.path.join(target_based_coverage_file, f), original_coverage_file)


def file_compare(file1, file2):
    global ORIGINAL_COVERAGE_FILE
    global TARGET_BASED_COVERAGE_FILE
    if 'curve' not in file1 and '.ec' in file1:
        print(('TARGET_BASED_COVERAGE_FILE', TARGET_BASED_COVERAGE_FILE))
        print((os.path.join(TARGET_BASED_COVERAGE_FILE, file1)))
        created_time_1 = os.path.getctime(os.path.join(TARGET_BASED_COVERAGE_FILE, file1))
    else:
        print((os.path.join(ORIGINAL_COVERAGE_FILE, file1)))
        created_time_1 = os.path.getctime(os.path.join(ORIGINAL_COVERAGE_FILE, file1))
    if 'curve' not in file2 and '.ec' in file2:
        print((os.path.join(TARGET_BASED_COVERAGE_FILE, file2)))
        created_time_2 = os.path.getctime(os.path.join(TARGET_BASED_COVERAGE_FILE, file2))
    else:
        print((os.path.join(ORIGINAL_COVERAGE_FILE, file2)))
        created_time_2 = os.path.getctime(os.path.join(ORIGINAL_COVERAGE_FILE, file2))
    return int(created_time_1 * 100) - int(created_time_2 * 100)


def get_curve_data(original_coverage_file, new_coverage_file, app_source_file):
    global MAX_ID
    instruction_coverage_data = {}
    branch_coverage_data = {}
    cxty_coverage_data = {}
    line_coverage_data = {}
    method_coverage_data = {}
    class_coverage_data = {}
    activity_coverage_data = {}
    file_list = os.listdir(original_coverage_file)
    if not file_list:
        return
    file_list.sort(file_compare)
    for f in file_list:
        if 'curve' not in f and '.ec' in f:
            print(('file_name: ' + f + ' created time: ' + str(os.path.getctime(os.path.join(TARGET_BASED_COVERAGE_FILE, f)))))
        else:
            print(('file_name: ' + f + ' created time: ' + str(os.path.getctime(os.path.join(original_coverage_file, f)))))

    for f in file_list:
        if '.log' in f:
            continue
        if '.DS_Store' in f:
            continue
        if 'curve' not in f:
            shutil.copy2(os.path.join(original_coverage_file, f), new_coverage_file)
            continue
        else:
            shutil.copy2(os.path.join(original_coverage_file, f), new_coverage_file)
            generate_test_report(new_coverage_file, app_source_file)
            instruction_coverage, branch_coverage, cxty_coverage, line_coverage, method_coverage, class_coverage, activity_coverage = get_coverage_data(app_source_file)
            pattern = re.compile('coverage_curve_(\\S+).ec')
            file_id = re.findall(pattern, f)[0]
            instruction_coverage_data[int(file_id)] = instruction_coverage
            branch_coverage_data[int(file_id)] = branch_coverage
            cxty_coverage_data[int(file_id)] = cxty_coverage
            line_coverage_data[int(file_id)] = line_coverage
            method_coverage_data[int(file_id)] = method_coverage
            class_coverage_data[int(file_id)] = class_coverage
            activity_coverage_data[int(file_id)] = activity_coverage
            if int(file_id) > MAX_ID:
                MAX_ID = int(file_id)
            else:
                continue

    generate_test_report(new_coverage_file, app_source_file)
    instruction_coverage, branch_coverage, cxty_coverage, line_coverage, method_coverage, class_coverage, activity_coverage = get_coverage_data(app_source_file)
    instruction_coverage_data['final'] = instruction_coverage
    branch_coverage_data['final'] = branch_coverage
    cxty_coverage_data['final'] = cxty_coverage
    line_coverage_data['final'] = line_coverage
    method_coverage_data['final'] = method_coverage
    class_coverage_data['final'] = class_coverage
    activity_coverage_data['final'] = activity_coverage
    print(('data_id: final' + ' instruction_coverage:' + str(instruction_coverage)))
    print(('data_id: final' + ' branch_coverage:' + str(branch_coverage)))
    print(('data_id: final' + ' cxty_coverage:' + str(cxty_coverage)))
    print(('data_id: final' + ' line_coverage:' + str(line_coverage)))
    print(('data_id: final' + ' method_coverage:' + str(method_coverage)))
    print(('data_id: final' + ' class_coverage:' + str(class_coverage)))
    print(('data_id: final' + ' activity_coverage:' + str(activity_coverage)))
    return (instruction_coverage_data, branch_coverage_data, cxty_coverage_data, line_coverage_data, method_coverage_data, class_coverage_data, activity_coverage_data)


def generate_test_report(new_coverage_file, app_source_file):
    os.chdir(app_source_file)
    cmd = 'gradle jacocoTestReportMergeWithParameter -PnewCoverageFilePath=' + new_coverage_file
    os.system(cmd)


def get_coverage_data(app_source_file):
    global APP_SOURCE_FILE
    global MANIFEST_FILE
    instruction_coverage = 0.0
    branch_coverage = 0.0
    cxty_coverage = 0.0
    line_coverage = 0.0
    method_coverage = 0.0
    class_coverage = 0.0
    activity_coverage = 0.0
    file_path = app_source_file + '/build/reports/jacoco/jacocoTestReportMergeWithParameter' + '/jacocoTestReportMergeWithParameter.xml'
    if APP_SOURCE_FILE == '/home/tim/AndroidStudioProjects/Q-testing/runnerup':
        file_path = app_source_file + '/app/build/reports/jacoco/jacocoTestReportMergeWithParameter' + '/jacocoTestReportMergeWithParameter.xml'
    dom = xml.dom.minidom.parse(file_path)
    root = dom.documentElement
    children = root.childNodes
    for counter in children:
        if counter.getAttribute('type') == 'INSTRUCTION':
            missed = int(counter.getAttribute('missed'))
            covered = int(counter.getAttribute('covered'))
            instruction_coverage = float(covered) / float(missed + covered)
        if counter.getAttribute('type') == 'BRANCH':
            missed = int(counter.getAttribute('missed'))
            covered = int(counter.getAttribute('covered'))
            branch_coverage = float(covered) / float(missed + covered)
        if counter.getAttribute('type') == 'LINE':
            missed = int(counter.getAttribute('missed'))
            covered = int(counter.getAttribute('covered'))
            line_coverage = float(covered) / float(missed + covered)
        if counter.getAttribute('type') == 'COMPLEXITY':
            missed = int(counter.getAttribute('missed'))
            covered = int(counter.getAttribute('covered'))
            cxty_coverage = float(covered) / float(missed + covered)
        if counter.getAttribute('type') == 'METHOD':
            missed = int(counter.getAttribute('missed'))
            covered = int(counter.getAttribute('covered'))
            method_coverage = float(covered) / float(missed + covered)
        if counter.getAttribute('type') == 'CLASS':
            missed = int(counter.getAttribute('missed'))
            covered = int(counter.getAttribute('covered'))
            class_coverage = float(covered) / float(missed + covered)

    activity_names = []
    covered_activity_num = 0
    manifest_file = ''
    print(MANIFEST_FILE)
    if MANIFEST_FILE == '':
        manifest_file = app_source_file + '/app/src/main/AndroidManifest.xml'
    else:
        manifest_file = MANIFEST_FILE
    manifest_dom = xml.dom.minidom.parse(manifest_file)
    manifest_root = manifest_dom.documentElement
    application_node = manifest_root.getElementsByTagName('application')[0]
    activity_nodes = application_node.getElementsByTagName('activity')
    for activity_node in activity_nodes:
        name_str = activity_node.getAttribute('android:name')
        name_strs = name_str.split('.')
        activity_name = name_strs[len(name_strs) - 1]
        print(('activity name: ' + activity_name))
        activity_names.append(activity_name)

    package_nodes = root.getElementsByTagName('package')
    for package_node in package_nodes:
        class_nodes = package_node.getElementsByTagName('class')
        for class_node in class_nodes:
            class_name_str = class_node.getAttribute('name')
            name_strs = class_name_str.split('/')
            class_name = name_strs[len(name_strs) - 1]
            if class_name in activity_names:
                print(('class name: ' + class_name))
                for counter in class_node.childNodes:
                    if counter.getAttribute('type') == 'CLASS':
                        if int(counter.getAttribute('covered')) > 0:
                            print('covered')
                            covered_activity_num += 1
                        else:
                            print('not covered')

    activity_coverage = float(covered_activity_num) / float(len(activity_names))
    return (
     instruction_coverage, branch_coverage, cxty_coverage, line_coverage, method_coverage, class_coverage, activity_coverage)


def save_curve_data(instruction_coverage_data, branch_coverage_data, cxty_coverage_data, line_coverage_data, method_coverage_data, class_coverage_data, activity_coverage_data, new_coverage_file):
    f = open(new_coverage_file + '/curve_data_all.txt', 'w')
    sorted_instruction_data = collections.OrderedDict(instruction_coverage_data)
    sorted_branch_data = collections.OrderedDict(branch_coverage_data)
    sorted_cxty_data = collections.OrderedDict(cxty_coverage_data)
    sorted_line_data = collections.OrderedDict(line_coverage_data)
    sorted_method_data = collections.OrderedDict(method_coverage_data)
    sorted_class_data = collections.OrderedDict(class_coverage_data)
    sorted_activity_data = collections.OrderedDict(activity_coverage_data)
    for data_id in list(sorted_instruction_data.keys()):
        if data_id == 'final':
            f.write('time: final\t' + 'instruction_coverage: ' + str(round(sorted_instruction_data[data_id], 4)) + '\t')
            f.write('branch_coverage: ' + str(round(sorted_branch_data[data_id], 4)) + '\t')
            f.write('cxty_coverage: ' + str(round(sorted_cxty_data[data_id], 4)) + '\t')
            f.write('line_coverage: ' + str(round(sorted_line_data[data_id], 4)) + '\t')
            f.write('method_coverage: ' + str(round(sorted_method_data[data_id], 4)) + '\t')
            f.write('class_coverage: ' + str(round(sorted_class_data[data_id], 4)) + '\t')
            f.write('activity_coverage: ' + str(round(sorted_activity_data[data_id], 4)) + '\n')
        else:
            f.write('time: ' + str(int(data_id) * TIME_INTERVAL) + '\t' + 'instruction_coverage: ' + str(round(sorted_instruction_data[data_id], 4)) + '\t')
            f.write('branch_coverage: ' + str(round(sorted_branch_data[data_id], 4)) + '\t')
            f.write('cxty_coverage: ' + str(round(sorted_cxty_data[data_id], 4)) + '\t')
            f.write('line_coverage: ' + str(round(sorted_line_data[data_id], 4)) + '\t')
            f.write('method_coverage: ' + str(round(sorted_method_data[data_id], 4)) + '\t')
            f.write('class_coverage: ' + str(round(sorted_class_data[data_id], 4)) + '\t')
            f.write('activity_coverage: ' + str(round(sorted_activity_data[data_id], 4)) + '\n')

    f.write('===========================\n')
    f.write('30min:\t' + 'instruction_coverage: ' + str(round(sorted_instruction_data[MAX_ID / 2], 4)) + '\t')
    f.write('branch_coverage: ' + str(round(sorted_branch_data[MAX_ID / 2], 4)) + '\t')
    f.write('cxty_coverage: ' + str(round(sorted_cxty_data[MAX_ID / 2], 4)) + '\t')
    f.write('line_coverage: ' + str(round(sorted_line_data[MAX_ID / 2], 4)) + '\t')
    f.write('method_coverage: ' + str(round(sorted_method_data[MAX_ID / 2], 4)) + '\t')
    f.write('class_coverage: ' + str(round(sorted_class_data[MAX_ID / 2], 4)) + '\t')
    f.write('activity_coverage: ' + str(round(sorted_activity_data[MAX_ID / 2], 4)) + '\n')
    f.write('60min:\t' + 'instruction_coverage: ' + str(round(sorted_instruction_data['final'], 4)) + '\t')
    f.write('branch_coverage: ' + str(round(sorted_branch_data['final'], 4)) + '\t')
    f.write('cxty_coverage: ' + str(round(sorted_cxty_data['final'], 4)) + '\t')
    f.write('line_coverage: ' + str(round(sorted_line_data['final'], 4)) + '\t')
    f.write('method_coverage: ' + str(round(sorted_method_data['final'], 4)) + '\t')
    f.write('class_coverage: ' + str(round(sorted_class_data['final'], 4)) + '\t')
    f.write('activity_coverage: ' + str(round(sorted_activity_data['final'], 4)) + '\n')
    f.close()


def calculate_coverage():
    global APP_SOURCE_FILE
    global Benchmark
    global MANIFEST_FILE
    global NEW_COVERAGE_FILE
    global ORIGINAL_COVERAGE_FILE
    global TARGET_BASED_COVERAGE_FILE
    bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    path_to_config = os.path.abspath(os.path.join(bundle_dir, './Config.txt'))
    config = configparser.ConfigParser()
    config.read(path_to_config)
    APP_SOURCE_FILE = config.get('Path', 'APP_SOURCE_PATH')
    APK_NAME = config.get('Path', 'APK_NAME')
    Benchmark = config.get('Path', 'Benchmark')
    if not Benchmark.endswith('/'):
        Benchmark = Benchmark + '/'
    MANIFEST_FILE = config.get('Path', 'MANIFEST_FILE')
    TARGET_BASED_COVERAGE_FILE = Benchmark + APK_NAME.split('.')[0] + '-output-1/coverage_merge_1'
    ORIGINAL_COVERAGE_FILE = Benchmark + APK_NAME.split('.')[0] + '-output-1/coverage_original_1'
    NEW_COVERAGE_FILE = Benchmark + APK_NAME.split('.')[0] + '-output-1/coverage_new_1'
    copy_restart_coverage_file(TARGET_BASED_COVERAGE_FILE, ORIGINAL_COVERAGE_FILE)
    instruction_data, branch_data, cxty_data, line_data, method_data, class_data, activity_data = get_curve_data(ORIGINAL_COVERAGE_FILE, NEW_COVERAGE_FILE, APP_SOURCE_FILE)
    save_curve_data(instruction_data, branch_data, cxty_data, line_data, method_data, class_data, activity_data, NEW_COVERAGE_FILE)


if __name__ == '__main__':
    calculate_coverage()
