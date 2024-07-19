import os
from uiautomator import Device
from shutil import copyfile
import socket, time, re, subprocess, random
from util.python_util import *
from event_extractor import EventExtractor
import xml.dom.minidom, xml.etree.ElementTree, os.path, numpy as np, sys, tensorflow as tf
from tensorflow.python.keras.models import Model, Sequential
from tensorflow.keras.initializers import Orthogonal
from tensorflow.keras.utils import get_custom_objects
from util.preprocess import *
from util.neural_network_util import ManDist
from util.preprocess import Preprocess
import configparser
ALPHA = 0.1
GAMMA = 0.99
EPSILON = 0.9
SYSTEM_THRESHOLD = 0.97
INIT_QVALUE = 1000.0
COVERAGE_RELATED_REWARD = False
MAX_REWARD = 500
STEP1 = 5000
STEP2 = 5000
DIFFERENCE_RATE_THRESHOLD = 0.5
TARGET_NUM = 2
CHANGE_TARGET_FREQUENCY = 50
SLEEP_AFTER_RESTART = 4
TEST_INDEX = 1
Benchmark = ''
DEVICE_ID = ''
TIME_LIMIT = 0
TEST_STATE = {}

class QLearning(object):

    def __init__(self, package_name, app_name, activity_name, app_source_path, apk_path, is_instrument, config_file):
        global Benchmark
        global DEVICE_ID
        global TEST_INDEX
        global TIME_LIMIT
        bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        path_to_config = os.path.abspath(config_file)
        config = configparser.ConfigParser()
        config.read(path_to_config)
        Benchmark = config.get('Path', 'Benchmark')
        if not Benchmark.endswith('/'):
            Benchmark = Benchmark + '/'
        DEVICE_ID = config.get('Setting', 'DEVICE_ID')
        TIME_LIMIT = int(config.get('Setting', 'TIME_LIMIT'))
        TEST_INDEX = int(config.get('Setting', 'TEST_INDEX'))
        self.package_name = package_name
        self.app_name = app_name
        self.launcher_activity_name = activity_name
        self.current_ui_file_path = ''
        self.current_command_file_path = ''
        self.current_package_name = ''
        self.current_activity_name = ''
        self.previous_activity_name = ''
        self.app_source_path = app_source_path
        self.bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        self.output_path = Benchmark + app_name + '-output-' + str(TEST_INDEX)
        self.is_instrument = is_instrument
        self.current_similarity = -1
        self.most_similar_state_id = -1
        self.q_table = {}
        self.error_table = {}
        self.state_entry_table = {}
        self.recency_time = 0
        self.activity_visited_count = {}
        self.method_coverage = {}
        self.coverage_result = []
        self.time_calculate_coverage = 0.0
        self.time_resolve_recycler_items = 0.0
        self.items_transition = {}
        self.items_count = {}
        self.items_map = {}
        self.resolve_recycler_flag = 0
        self.recycler_label = ''
        self.current_state_tree = None
        self.current_state_id = -1
        self.memory_buffer = {}
        self.state_features = []
        self.special_widgets_recyclerview = []
        self.previous_target_activities = []
        self.target_activities = []
        self.model = None
        self.intermediate_model = None
        self.system_flag = 0
        self.preprocess = Preprocess(DEVICE_ID)
        self.apk_path = apk_path
        rotate_cmd = 'python ' + self.bundle_dir + '/events/device.py ' + DEVICE_ID
        os.system(rotate_cmd)
        return

    def setup(self):
        #get_custom_objects().update({'Orthogonal': Orthogonal})
        self.model = tf.keras.models.load_model(self.bundle_dir + '/models/SiameseLSTM.h5', custom_objects={'ManDist': ManDist})
        #with open(self.bundle_dir + '/models/SiameseLSTM.json', 'r') as f:
        #    model = tf.keras.models.model_from_json(f.read(), custom_objects={'ManDist': ManDist})
        self.model.summary()
        x = Sequential()
        x.add(self.model.get_layer('lstm'))
        self.intermediate_model = x
        bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        path_to_state_feature = os.path.abspath(os.path.join(bundle_dir, self.bundle_dir + '/util/STATE-FEATURES.txt'))
        f = open(path_to_state_feature)
        for line in f.readlines():
            for i in range(10):
                self.state_features.append(line.rstrip('\n') + '@' + str(i))

    def update_recycler_info(self, action_string, current_state, next_state):
        if current_state not in self.q_table:
            self.resolve_recycler_flag = 0
            return
        q_table = self.q_table[current_state]
        value = 0
        if action_string in q_table:
            value = q_table[action_string]
        if '@"recycler items_' in action_string and value == INIT_QVALUE:
            self.resolve_recycler_flag = 1
            self.recycler_label = action_string[action_string.rindex('@') + 2:len(action_string) - 2]
            if self.current_similarity > DIFFERENCE_RATE_THRESHOLD and self.most_similar_state_id > 0:
                self.recycler_label = str(self.most_similar_state_id) + '_' + self.recycler_label
            else:
                self.recycler_label = str(self.current_state_id) + '_' + self.recycler_label
        else:
            self.resolve_recycler_flag = 0
        if self.resolve_recycler_flag == 1:
            if self.recycler_label not in self.items_transition:
                self.items_transition[self.recycler_label] = next_state
                self.items_count[self.recycler_label] = 1
            elif self.items_transition[self.recycler_label] == next_state and self.items_count[self.recycler_label] != -1:
                self.items_count[self.recycler_label] += 1
            else:
                self.items_count[self.recycler_label] = -1

    def resolve_recycler_items(self, parent_node, path_label):
        if 'RecyclerView' in str(parent_node.get('class')):
            print(('class type for the widget is ' + str(parent_node.get('class'))))
            if len(parent_node) == 0:
                return
            items_string = 'recycler items_' + self.current_activity_name + '_' + path_label
            for child in parent_node.iter('node'):
                child.set('text', items_string)

            if self.current_similarity > DIFFERENCE_RATE_THRESHOLD and self.most_similar_state_id > 0:
                checking_items_string = str(self.most_similar_state_id) + '_' + items_string
            else:
                checking_items_string = str(self.current_state_id) + '_' + items_string
            if checking_items_string in self.items_count and self.items_count[checking_items_string] >= 3:
                count = 0
                remove_list = []
                for child in parent_node:
                    if count > 0:
                        remove_list.append(child)
                        print('the items are removed1')
                    count += 1

                for child in remove_list:
                    parent_node.remove(child)

        else:
            for child in parent_node:
                self.resolve_recycler_items(child, path_label + child.get('index'))

    def refine_xml(self, parent_node):
        for child in parent_node:
            child.set('content-desc', 'default')
            child.set('text', 'default')
            child.set('bounds', 'default')
            child.set('checked', 'default')
            child.set('focused', 'default')
            self.refine_xml(child)

    def get_current_state_retry(self, episode):
        for tryTimes in range(2):
            next_state = self.get_current_state(episode)
            if 'WAITFORASECOND' != next_state and 'ERROR STATE' != next_state and 'UNKNOWN' != next_state:
                return next_state

        next_state = 'ERROR STATE'
        return next_state

    def get_widget_hierarchy_state(self):
        tree1 = xml.etree.ElementTree.parse(self.current_ui_file_path)
        root1 = tree1.getroot()
        system_node1 = []
        node_num = 0
        for child in root1:
            if child.get('class') == 'android.widget.LinearLayout' and child.get('package') == 'com.android.systemui' or child.get('class') == 'android.widget.FrameLayout' and child.get('package') == 'com.android.systemui':
                print(('the element important is ' + child.get('class')))
                system_node1.append(child)
            else:
                node_num += 1

        for node in system_node1:
            root1.remove(node)

        if node_num == 0:
            return 'WAITFORASECOND'
        else:
            self.resolve_recycler_items(root1, '0')
            self.current_state_tree = tree1
            tree1.write(self.current_ui_file_path)
            tree2 = xml.etree.ElementTree.parse(self.current_ui_file_path)
            root2 = tree2.getroot()
            self.refine_xml(root2)
            widget_hierarchy_state = xml.etree.ElementTree.tostring(root2).decode()
            if not widget_hierarchy_state == '':
                if len(widget_hierarchy_state) < 40:
                    print(('length is smaller than 40:' + widget_hierarchy_state))
                return widget_hierarchy_state
            print(widget_hierarchy_state)
            print('return ERROR STATE')
            return 'ERROR STATE'

    def get_current_state(self, episode):
        global TEST_STATE
        self.current_ui_file_path = Benchmark + self.app_name + '-output-' + str(TEST_INDEX) + '/event_output/' + 'ui_' + episode + '.xml'
        self.current_command_file_path = Benchmark + self.app_name + '-output-' + str(TEST_INDEX) + '/event_output/' + 'command_' + episode + '.txt'
        has_wait_for_jump = False
        try:
            t_0 = time.time()
            time.sleep(0.1)
            d = Device(DEVICE_ID)
            d.dump(self.current_ui_file_path)
            dump_time = time.time() - t_0
        except Exception:
            print(('UNKNOWN ' + 'uiautomator dump error'))
            self.current_package_name = 'UNKNOWN'
            self.previous_activity_name = self.current_activity_name
            self.current_activity_name = 'UNKNOWN'
            self.current_state_id = -1
            return 'UNKNOWN'

        cmd = 'adb -s ' + DEVICE_ID + ' shell dumpsys window | grep mCurrentFocus'
        info = subprocess.getoutput(cmd)
        print(('info is ' + info))
        if 'mCurrentFocus=null' in info:
            print(('UNKNOWN ' + info))
            self.current_package_name = 'UNKNOWN'
            self.previous_activity_name = self.current_activity_name
            self.current_activity_name = 'UNKNOWN'
            self.current_state_id = -1
            return 'UNKNOWN'
        if 'error: closed' in info or 'device offline' in info or '}' not in info:
            os.system('adb kill-server && adb start-server')
            info = subprocess.getoutput(cmd)
        if 'mCurrentFocus=Window' in info:
            self.current_package_name = self.package_name
        last_space_index = info.rindex(' ')
        last_paren_index = info.rindex('}')
        info = info[last_space_index + 1:last_paren_index]
        if '/' in info:
            self.current_package_name = info.split('/')[0]
            self.previous_activity_name = self.current_activity_name
            self.current_activity_name = info.split('/')[1]
            print(('current_activity_name is: ' + str(self.current_activity_name)))
            if self.previous_activity_name != self.current_activity_name:
                has_wait_for_jump = True
        else:
            print(('/ is not in info: ' + info))
        if self.package_name in self.current_package_name:
            self.current_package_name = self.package_name
        t0 = time.time()
        state = self.get_widget_hierarchy_state()
        refine_time = time.time() - t0
        if state == 'ERROR STATE' or state == 'WAITFORASECOND':
            self.current_state_id = -1
            return state
        if state not in self.q_table and self.current_package_name == self.package_name:
            if 'nexuslauncher' in state:
                print(('the state is added into Q-table mistakenly: ' + state))
                exit(1)
            action_table = {}
            self.q_table[state] = action_table
            TEST_STATE[state] = len(self.q_table)
            print(('current new state id :' + str(len(self.q_table))))
            self.current_state_id = len(self.q_table)
        elif self.current_package_name == self.package_name:
            state_id = TEST_STATE[state]
            print(('current existing state id :' + str(state_id)))
            self.current_state_id = state_id
        return state

    def get_random_action(self, current_state):
        e = EventExtractor(self.package_name, self.current_activity_name, self.current_ui_file_path, self.current_state_tree, self.output_path, self.launcher_activity_name, True)
        e.extract_event()
        e.detect_invokable_actions()
        e.output_file()
        events = e.get_events()
        action_table = self.q_table[current_state]
        for event in events:
            if event not in action_table and 'com.android.systemui:id/home_button' not in event and 'com.android.systemui:id/recent_apps' not in event:
                action_table[event] = INIT_QVALUE

        random_num = random.randint(1, len(events))
        action_string = events[random_num - 1]
        while 'com.android.systemui:id/home_button' in action_string or 'com.android.systemui:id/recent_apps' in action_string:
            random_num = random.randint(1, len(events))
            action_string = events[random_num - 1]

        return action_string

    def get_system_action(self):
        system_events = [
         'rotation\n', 'home\n']
        random_num = random.randint(1, len(system_events) + 1)
        if random_num <= len(system_events):
            self.system_flag = 1
            system_event = system_events[random_num - 1]
            print(('chosen system action is: ' + system_event))
            return system_event
        else:
            self.system_flag = 2
            print('chosen system action is from tester')
            cmd = 'python trigger/tester.py -s ' + DEVICE_ID + ' -f ' + self.apk_path + ' -p random'
            system_event = subprocess.getoutput(cmd)
            print(('chosen system action is: ' + system_event))
            return system_event

    def get_qlearning_action(self, current_state):
        random_num = random.uniform(0, 1)
        if random_num > SYSTEM_THRESHOLD:
            self.system_flag = 1
            return self.get_system_action()
        if random_num > EPSILON:
            return self.get_random_action(current_state)
        max_value = -100000
        action_sting = ''
        action_table = self.q_table[current_state]
        for k, v in list(action_table.items()):
            if action_table[k] >= max_value:
                max_value = action_table[k]
                action_sting = k

        return action_sting

    def get_action(self, current_state, episode):
        if self.current_package_name != self.package_name:
            if self.is_instrument:
                action_cmd = 'adb -s ' + DEVICE_ID + ' shell am instrument ' + self.package_name + '/' + self.package_name + '.JacocoInstrumentation'
            else:
                action_cmd = 'adb -s ' + DEVICE_ID + ' shell am start -S -n ' + self.package_name + '/' + self.launcher_activity_name
            print('the chosen action is restarting app')
            self.fix_error_state_cant_escape()
            return (
             action_cmd, action_cmd)
        if current_state == 'ERROR STATE':
            if self.is_instrument:
                action_cmd = 'adb -s ' + DEVICE_ID + ' shell am instrument ' + self.package_name + '/' + self.package_name + '.JacocoInstrumentation'
            else:
                action_cmd = 'adb -s ' + DEVICE_ID + ' shell am start -S -n ' + self.package_name + '/' + self.launcher_activity_name
            print('the chosen action is restarting app')
            self.fix_error_state_cant_escape()
            return (
             action_cmd, action_cmd)
        action_table = self.q_table[current_state]
        action_string = ''
        if not len(action_table) > 0:
            action_string = self.get_random_action(current_state)
            print('the action_table is empty since it has never been visited before')
        else:
            print('the state has been visited before')
            if action_string == '':
                action_string = self.get_qlearning_action(current_state)
                if self.system_flag != 0:
                    return (action_string, action_string)
        print(('the selected action string is ' + action_string.split('\n')[0]))
        action_id, action_cmd, view_type, view_text = parse_action_string(action_string)
        return (
         action_string, action_cmd)

    def record_action_cmd(self, action_count, action_cmd):
        action_cmd = action_cmd.replace('(', ' ').replace(')', ' ').replace('[', ' ').replace(']', ' ').replace('\n', ' ')
        cmd = 'echo action No.' + str(action_count) + ': ' + str(action_cmd) + ' >> ' + self.output_path + '/crash_log.txt'
        os.system(cmd)

    def execute_action(self, action_cmd):
        if self.system_flag == 2:
            return 'True'
        else:
            action_type = ''
            action_parameter = ''
            if str(action_cmd).startswith('adb'):
                cmd = str(action_cmd).replace('adb', 'adb -s ' + DEVICE_ID)
                os.system(cmd)
                time.sleep(SLEEP_AFTER_RESTART)
                return 'True'
            if str(action_cmd) == 'rotation\n':
                rotate_cmd = 'timeout 2s python ' + self.bundle_dir + '/events/rotation.py ' + DEVICE_ID
                os.system(rotate_cmd)
                time.sleep(1)
                rotate_cmd = 'timeout 2s python ' + self.bundle_dir + '/events/rotation_natural.py ' + DEVICE_ID
                os.system(rotate_cmd)
                return 'True'
            if str(action_cmd) == 'home\n':
                menu_cmd = 'timeout 2s python ' + self.bundle_dir + '/events/home.py ' + DEVICE_ID
                return subprocess.getoutput(menu_cmd)
            if str(action_cmd) == 'menu\n':
                menu_cmd = 'timeout 2s python ' + self.bundle_dir + '/events/menu.py ' + DEVICE_ID
                return subprocess.getoutput(menu_cmd)
            if str(action_cmd) == 'back\n' or str(action_cmd) == 'keyevent_back\n':
                back_cmd = 'timeout 2s python ' + self.bundle_dir + '/events/back.py ' + DEVICE_ID
                return subprocess.getoutput(back_cmd)
            if 'click(' in str(action_cmd):
                action_type = 'click'
            elif 'clickLong(' in str(action_cmd):
                action_type = 'long_click'
            elif 'edit(' in str(action_cmd):
                action_type = 'edit'
            elif 'scroll(' in str(action_cmd):
                action_type = 'scroll'
            if '(text=' in str(action_cmd):
                action_parameter = '_by_text'
            elif '(content-desc=' in str(action_cmd):
                action_parameter = '_by_content_desc'
            elif '(resource-id=' in str(action_cmd) and 'instance=' in str(action_cmd):
                action_parameter = '_by_resource_id_instance'
            elif '(resource-id=' in str(action_cmd):
                action_parameter = '_by_resource_id'
            elif 'direction=' in str(action_cmd):
                action_parameter = '_by_direction'
            elif 'className=' in str(action_cmd) and 'instance=' in str(action_cmd):
                action_parameter = '_by_classname_instance'
            if action_parameter == '_by_resource_id_instance':
                pattern = re.compile("resource-id='(.*)',")
                resource_id = re.findall(pattern, action_cmd)[0]
                pattern = re.compile("instance='(.*)'")
                instance = re.findall(pattern, action_cmd)[0]
                event_cmd = 'timeout 2s python ' + self.bundle_dir + '/events/' + action_type + action_parameter + '.py' + ' ' + DEVICE_ID + ' ' + resource_id + ' ' + instance
                return subprocess.getoutput(event_cmd)
            if action_parameter == '_by_classname_instance':
                pattern = re.compile("className='(.*)',")
                class_name = re.findall(pattern, action_cmd)[0]
                pattern = re.compile("instance='(.*)'")
                instance = re.findall(pattern, action_cmd)[0]
                event_cmd = 'timeout 2s python ' + self.bundle_dir + '/events/' + action_type + action_parameter + '.py' + ' ' + DEVICE_ID + ' ' + class_name + ' ' + instance
                return subprocess.getoutput(event_cmd)
            first_quote_index = str(action_cmd).index("'")
            last_quote_index = str(action_cmd).rindex("'")
            action_parameter_value = str(action_cmd)[first_quote_index:last_quote_index + 1]
            event_cmd = 'timeout 2s python ' + self.bundle_dir + '/events/' + action_type + action_parameter + '.py' + ' ' + DEVICE_ID + ' ' + action_parameter_value
            print(('the executation cmd is: ' + event_cmd))
            return subprocess.getoutput(event_cmd)

    def traverse_tree(self, node, level, feature_list):
        feature_list.append(str(node.get('class')) + '@' + str(level))
        for child in node.getchildren():
            self.traverse_tree(child, level + 1, feature_list)

    def get_memory_based_reward2(self, next_state, eposide):
        self.current_similarity = -1
        if self.system_flag != 0:
            return -1
        else:
            if next_state == 'UNKNOWN' or next_state == 'ERROR STATE':
                return -MAX_REWARD
            next_activity = self.current_activity_name
            next_state_vector = self.preprocess.extract_vectors(self.current_state_tree)
            next_feature_vector = self.intermediate_model.predict(np.array(next_state_vector))
            if next_activity not in self.memory_buffer:
                memory_states_vectors = {(self.current_state_id): next_feature_vector}
                self.memory_buffer[next_activity] = memory_states_vectors
                return MAX_REWARD
            memory_feature_vectors = self.memory_buffer[next_activity]
            similarity, self.most_similar_state_id = self.compare_states2(memory_feature_vectors, next_feature_vector)
            self.current_similarity = similarity
            difference_rate = 1 - similarity
            if difference_rate > DIFFERENCE_RATE_THRESHOLD:
                memory_feature_vectors[self.current_state_id] = next_feature_vector
                reward = MAX_REWARD
                return reward
            reward = -MAX_REWARD
            return reward

    @staticmethod
    def compare_states2(memory_feature_vectors, next_feature_vector):
        similarity = -1
        most_similar_id = -1
        for similar_id in memory_feature_vectors:
            memory_feature_vector = memory_feature_vectors[similar_id]
            temp_similarity = np.exp(-np.sum(np.abs(memory_feature_vector - next_feature_vector), axis=1))
            if temp_similarity > similarity:
                similarity = temp_similarity
                most_similar_id = similar_id

        return (
         similarity, most_similar_id)

    def update_qtable(self, current_state, next_state, action, reward):
        if self.system_flag != 0:
            self.system_flag = 0
            return
        if current_state not in self.q_table:
            print(('the current states is not in q_table and the current activity is ' + self.current_activity_name))
            return
        if 'nexuslauncher' in current_state:
            print('nexuslauncher is in current_state')
            exit(1)
        action_table = self.q_table[current_state]
        if action not in action_table:
            print(('the invalid state is ' + current_state))
            print(('the action ' + action + ' is not in current action_table'))
            return
        q_current = action_table[action]
        if q_current == INIT_QVALUE:
            q_current = 0
            print('q-current is assigned with 0')
        print(('the updated action is ' + action))
        updated_value = 0
        if self.current_package_name != self.package_name:
            if q_current > -950:
                reward = -500
                updated_value = ALPHA * 5 * (-500 + GAMMA * -500 - q_current)
                q_current = q_current + updated_value
            else:
                updated_value = -100
                q_current -= 100
            self.q_table[current_state][action] = q_current
        elif next_state not in self.q_table or len(self.q_table[next_state]) == 0:
            updated_value = ALPHA * (reward + GAMMA * 1000 - q_current)
            q_current = q_current + updated_value
            self.q_table[current_state][action] = q_current
        else:
            q_next = -1000000
            for k, v in list(self.q_table[next_state].items()):
                if self.q_table[next_state][k] > q_next:
                    q_next = self.q_table[next_state][k]

            updated_value = reward + GAMMA * q_next - q_current
            if updated_value < 0:
                updated_value = ALPHA * 5 * updated_value
                q_current = q_current + updated_value
            else:
                updated_value = ALPHA * updated_value
                q_current = q_current + updated_value
            self.q_table[current_state][action] = q_current

    def update_error_state(self, action_str, current_state):
        if current_state not in self.error_table:
            self.error_table[current_state] = {}
        current_error_table = self.error_table[current_state]
        if action_str not in current_error_table:
            current_error_table[action_str] = 1
        else:
            current_error_table[action_str] += 1

    def get_final_coverage(self):
        os.chdir(self.app_source_path)
        cmd = 'gradle jacocoTestReportMerge' + str(TEST_INDEX)
        os.system(cmd)
        cmd = 'adb -s ' + DEVICE_ID + ' shell rm -r data/data/' + self.package_name + '/files'
        os.system(cmd)
        file_path = self.app_source_path + '/build/reports/jacoco/jacocoTestReportMerge' + str(TEST_INDEX) + '/jacocoTestReportMerge' + str(TEST_INDEX) + '.xml'
        dom = xml.dom.minidom.parse(file_path)
        root = dom.documentElement
        children = root.childNodes
        for counter in children:
            if counter.getAttribute('type') == 'INSTRUCTION':
                missed = int(counter.getAttribute('missed'))
                covered = int(counter.getAttribute('covered'))
                covered_percent = float(covered) / float(missed + covered)
                self.coverage_result.append(covered_percent)

    def qlearning_loop(self):
        global startt
        time_get_state1 = 0.0
        time_get_action1 = 0.0
        time_execution_action1 = 0.0
        time_get_reward1 = 0.0
        time_update_qtable1 = 0.0
        time_get_coverage1 = 0.0
        time_update_recycler = 0.0
        action_count = 0
        print('==============start testing=============\n')
        self.setup()
        t11 = time.time()
        startt = t11
        t = time.time()
        episode = 0
        while episode < STEP1:
            if t - t11 > TIME_LIMIT:
                break
            print(('==============episode %s=============\n' % (str(episode) + '_')))
            current_state = self.get_current_state_retry(str(episode) + '_')
            for step in range(10):
                self.recency_time += 1
                print(('========episode %s========' % (str(episode) + '_' + str(step))))
                t1 = time.time()
                action_string, action_cmd = self.get_action(current_state, episode)
                t2 = time.time()
                c_get_action1 = t2 - t1
                time_get_action1 += c_get_action1
                self.record_action_cmd(action_count, action_string)
                t1 = time.time()
                self.execute_action(action_cmd)
                t2 = time.time()
                c_execution_action1 = t2 - t1
                time_execution_action1 += c_execution_action1
                t1 = time.time()
                next_state = self.get_current_state_retry(str(episode) + '_' + str(step))
                t2 = time.time()
                c_get_state1 = t2 - t1
                time_get_state1 += c_get_state1
                t1 = time.time()
                self.update_recycler_info(action_string, current_state, next_state)
                t2 = time.time()
                time_update_recycler += t2 - t1
                t1 = time.time()
                reward = self.get_memory_based_reward2(next_state, episode)
                t2 = time.time()
                c_get_reward1 = t2 - t1
                time_get_reward1 += c_get_reward1
                t1 = time.time()
                self.update_qtable(current_state, next_state, action_string, reward)
                t2 = time.time()
                c_update_qtable1 = t2 - t1
                time_update_qtable1 += c_update_qtable1
                current_state = next_state
                print(('the jumped state is ' + self.current_activity_name))
                print('\n')

            t = time.time()
            episode += 1

        t12 = time.time()
        if self.is_instrument:
            self.get_final_coverage()
        print('===========time information===========')
        print(('total time is: ' + str(t12 - t11)))
        print(('time_get_state is: ' + str(time_get_state1)))
        print(('time_get_action is: ' + str(time_get_action1)))
        print(('time_execute_action is: ' + str(time_execution_action1)))
        print(('time_get_reward is: ' + str(time_get_reward1)))
        print(('time_update_qtable is: ' + str(time_update_qtable1)))
        print(('time_update_recycler_view is: ' + str(time_update_recycler)))
        print(('time_calculate_coverage is: ' + str(time_get_coverage1)))
        print('===========memory buffer information===========')
        count = 0
        for k, v in list(self.memory_buffer.items()):
            count += len(v)
            print(('the states size in ' + str(k) + ' is ' + str(len(v))))

        print(('total states number in memory buffer is: ' + str(count)))
        print('===========Q-table information===========')
        print(('total states number in Q-table is: ' + str(len(self.q_table))))
        print('===========step information===========')
        print(('total number is: ' + str(episode * 10)))

    def fix_error_state_cant_escape(self):
        if self.current_package_name != self.package_name and self.current_activity_name == self.previous_activity_name:
            cmd = 'adb -s ' + DEVICE_ID + ' shell am force-stop ' + self.current_package_name
            print('get stuck in an error state that cannot launch main target activity, now release current error app first.')
            os.system(cmd)

    def fix_edittext(self, tree):
        root = tree.getroot()
        self.refine_edittext(root)
        return tree

    def refine_edittext(self, node):
        for child in node:
            if child.get('class') == 'android.widget.EditText':
                child.set('content-desc', 'default')
                child.set('text', 'default')
                child.set('focused', 'true')
            self.refine_edittext(child)
