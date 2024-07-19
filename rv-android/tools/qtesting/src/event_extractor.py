import xml.etree.ElementTree
from UILayoutObject import UILayoutObject
from UIExecutableObject import UIExecutableObject
from Action import Action
from ActionConstValue import ActionConstValue
import os, sys
import importlib
importlib.reload(sys)
#sys.setdefaultencoding('utf-8')

class EventExtractor(object):

    def __init__(self, package_name, activity_name, ui_file_path, ui_tree, out_path, entry_activity_name, extra_invokable_actions):
        self.debug = '[EventExtractor] '
        self.package_name = package_name
        self.activity_name = activity_name
        self.entry_activity_name = entry_activity_name
        self.ui_file_path = ui_file_path
        episode = self.ui_file_path.split('/')[-1][3:-4]
        self.ui_tree = ui_tree
        self.command_file_path = out_path + '/event_output/' + 'command_' + episode + '.txt'
        self.output_path = out_path
        self.index_list = []
        self.isScrollable = False
        self.CIS = ''
        self.ui_layout_objects = []
        self.ui_executable_objects = []
        self.textViewCnt = -1
        self.buttonCnt = -1
        self.imageViewCnt = -1
        self.imageButtonCnt = -1
        self.toggleButtonCnt = -1
        self.editTextCnt = -1
        self.checkBoxCnt = -1
        self.radioButtonCnt = -1
        self.checkedTextViewCnt = -1
        self.seekbarCnt = -1
        self.viewCnt = -1
        self.actionIDCounter = 0
        self.invokable_actions = []
        self.disabled_actions = []
        self.extra_invokable_actions = extra_invokable_actions
        self.logs = []
        self.idMap = {}

    def extract_event(self):
        self.logs.append('I: start android app static analysis to detect actions.... ')
        tree = self.ui_tree
        tree_root = tree.getroot()
        if len(tree_root):
            self.analyze_node(tree_root, False, False, False, False)
        else:
            self.logs.append('E: the root element "hierarchy" has no child nodes?? ')
            exit(0)

    def getCIS(self):
        output = ''
        for index in self.index_list:
            output += str(index)

        return output

    def str2bool(self, string):
        if string == 'true':
            return True
        else:
            return False

    def get_id_instance(self, resource_id):
        if resource_id is None or '' == resource_id:
            return 0
        if resource_id in self.idMap:
            self.idMap[resource_id] += 1
        else:
            self.idMap[resource_id] = 0
        return self.idMap[resource_id]

    def get_view_instance(self, class_name):
        if class_name == 'android.widget.TextView':
            self.textViewCnt += 1
            return self.textViewCnt
        else:
            if class_name == 'android.widget.Button':
                self.buttonCnt += 1
                return self.buttonCnt
            if class_name == 'android.widget.ImageView':
                self.imageButtonCnt += 1
                return self.imageButtonCnt
            if class_name == 'android.widget.ToggleButton':
                self.toggleButtonCnt += 1
                return self.toggleButtonCnt
            if class_name == 'android.widget.EditText':
                self.editTextCnt += 1
                return self.editTextCnt
            if class_name == 'android.widget.CheckBox':
                self.checkBoxCnt += 1
                return self.checkBoxCnt
            if class_name == 'android.widget.RadioButton':
                self.radioButtonCnt += 1
                return self.radioButtonCnt
            if class_name == 'android.widget.CheckedTextView':
                self.checkedTextViewCnt += 1
                return self.checkedTextViewCnt
            if class_name == 'android.widget.SeekBar':
                self.seekbarCnt += 1
                return self.seekbarCnt
            self.logs.append(self.debug + 'the widget type is not handled??')
            return 0

    def analyze_node(self, node_list, parent_clickable, parent_long_clickable, parent_checkable, parent_scrollable):
        for node in node_list:
            if node.tag == 'node':
                self.logs.append('node   [open]')
                attrib = node.attrib
                if 'index' in list(attrib.keys()):
                    self.index_list.append(int(attrib['index']))
                else:
                    self.logs.append('E: has not find "index" attribute ??')
                    exit(0)
                if len(node):
                    cis = self.getCIS()
                    self.logs.append('non-leaf node ok!!')
                    UIlo = UILayoutObject(cis, attrib['package'], attrib['class'])
                    if attrib['class'] == 'android.widget.ListView':
                        UIlo.setIsListView(True)
                    else:
                        UIlo.setIsListView(False)
                    if attrib['scrollable'] == 'true':
                        self.logs.append(self.debug + ': this page is scrollable.')
                        self.isScrollable = True
                        self.CIS = cis
                    self.ui_layout_objects.append(UIlo)
                    self.analyze_node(node, parent_clickable or self.str2bool(attrib['clickable']), parent_long_clickable or self.str2bool(attrib['long-clickable']), parent_checkable or self.str2bool(attrib['checkable']), parent_scrollable or self.str2bool(attrib['scrollable']))
                else:
                    cis = self.getCIS()
                    self.logs.append('leaf node ok!!')
                    executable_obj = UIExecutableObject(cis, attrib['package'], attrib['class'])
                    executable_obj.set_event_property(attrib['clickable'], attrib['long-clickable'], attrib['scrollable'], attrib['checkable'], attrib['text'], attrib['resource-id'], attrib['content-desc'], attrib['index'], attrib['enabled'], self.get_view_instance(attrib['class']), self.get_id_instance(attrib['resource-id']))
                    self.logs.append('cis = ' + cis)
                    if parent_long_clickable:
                        self.logs.append("parent node's long-clickable is true, set its own's long-clickable as true")
                        executable_obj.set_long_clickable('true')
                    if parent_clickable:
                        self.logs.append("parent node's clickable is true, set its own's clickable as true")
                        executable_obj.set_clickable('true')
                    if parent_checkable:
                        self.logs.append("parent node's checkable is true, set its own's checkable as true")
                        executable_obj.set_checkable('true')
                    self.ui_executable_objects.append(executable_obj)
                    self.index_list = self.index_list[:-1]
                    self.logs.append('node   [close]')

    def add_invokable_action(self, action):
        self.logs.append(self.debug + 'I: add an action <id: ' + str(action.action_id) + "> into the app state's invokable actions list")
        if self.extra_invokable_actions:
            self.invokable_actions.append(action)
        else:
            self.disabled_actions.append(action)

    def generate_click_action(self, executable_obj, action_type):
        action = Action()
        self.actionIDCounter += 1
        action.set_action_property(self.actionIDCounter, executable_obj.cis, executable_obj.text, action_type, self.activity_name)
        if executable_obj.text != '':
            action_cmd = action_type + "(className='" + executable_obj.class_name + "',instance='" + str(executable_obj.instance) + "')\n"
        elif executable_obj.resource_id != '':
            action_cmd = action_type + "(resource-id='" + executable_obj.resource_id + "', instance='" + str(executable_obj.id_instance) + "')\n"
        elif executable_obj.content_desc != '':
            action_cmd = action_type + "(content-desc='" + executable_obj.content_desc + "')\n"
        else:
            return ''
        action.set_action_cmd(action_cmd, executable_obj.class_name)
        self.add_invokable_action(action)
        if action_type == 'click':
            self.logs.append(self.debug + 'I: create a *Click* Action!')
        else:
            self.logs.append(self.debug + 'I: create a *Long Click* Action!')

    def generate_click_image_action(self, executable_obj, action_type):
        action = Action()
        self.actionIDCounter += 1
        action.set_action_property(self.actionIDCounter, executable_obj.cis, executable_obj.text, action_type, self.activity_name)
        if executable_obj.resource_id != '':
            action_cmd = action_type + "(resource-id='" + executable_obj.resource_id + "', instance='" + str(executable_obj.id_instance) + "')\n"
        elif executable_obj.content_desc != '':
            action_cmd = action_type + "(content-desc='" + executable_obj.content_desc + "')\n"
        elif executable_obj.text != '':
            action_cmd = action_type + "(className='" + executable_obj.class_name + "',instance='" + str(executable_obj.instance) + "')\n"
        else:
            return ''
        action.set_action_cmd(action_cmd, executable_obj.class_name)
        self.add_invokable_action(action)
        if action_type == 'click':
            self.logs.append(self.debug + 'I: create a *Click Image* Action!')
        else:
            self.logs.append(self.debug + 'I: create a *Long Click Image* Action!')

    def generate_edit_text_action(self, executable_obj):
        action = Action()
        self.actionIDCounter += 1
        action.set_action_property(self.actionIDCounter, executable_obj.cis, executable_obj.text, action.editText, self.activity_name)
        if executable_obj.resource_id != '':
            action_cmd = action.editText + "(resource-id='" + executable_obj.resource_id + "',instance='" + str(executable_obj.id_instance) + "')\n"
        elif executable_obj.content_desc != '':
            action_cmd = action.editText + "(content-desc='" + executable_obj.resource_id + "')\n"
        else:
            action_cmd = action.editText + "(className='" + executable_obj.class_name + "',instance='" + str(executable_obj.instance) + "')\n"
        action.set_action_cmd(action_cmd, executable_obj.class_name)
        self.add_invokable_action(action)
        self.logs.append(self.debug + 'I: create an *EditText* Action!')

    def generate_check_action(self, executable_obj):
        action = Action()
        self.actionIDCounter += 1
        action.set_action_property(self.actionIDCounter, executable_obj.cis, executable_obj.text, action.click, self.activity_name)
        if executable_obj.resource_id != '':
            action_cmd = action.click + "(resource-id='" + executable_obj.resource_id + "', instance='" + str(executable_obj.id_instance) + "')\n"
        elif executable_obj.text != '':
            if executable_obj.has_multi_lines_text():
                action_cmd = action.click + "(textContains='" + executable_obj.get_first_line_text() + "')\n"
            else:
                action_cmd = action.click + "(text='" + executable_obj.text + "')\n"
        elif executable_obj.content_desc != '':
            action_cmd = action.click + "(content-desc='" + executable_obj.resource_id + "')\n"
        else:
            action_cmd = action.click + "(className='" + executable_obj.class_name + "',instance='" + str(executable_obj.instance) + "')\n"
        action.set_action_cmd(action_cmd, executable_obj.class_name)
        self.add_invokable_action(action)
        self.logs.append(self.debug + 'I: create an *CheckBox/RadioButton* Action!')

    def generate_check_textview_action(self, executable_obj):
        action = Action()
        self.actionIDCounter += 1
        action.set_action_property(self.actionIDCounter, executable_obj.cis, executable_obj.text, action.click, self.activity_name)
        if executable_obj.text != '':
            action_cmd = action.click + "(className='" + executable_obj.class_name + "',instance='" + str(executable_obj.instance) + "')\n"
        elif executable_obj.resource_id != '':
            action_cmd = action.click + "(resource-id='" + executable_obj.resource_id + "', instance='" + str(executable_obj.id_instance) + "')\n"
        elif executable_obj.content_desc != '':
            action_cmd = action.click + "(content-desc='" + executable_obj.content_desc + "')\n"
        else:
            return ''
        action.set_action_cmd(action_cmd, executable_obj.class_name)
        self.add_invokable_action(action)
        self.logs.append(self.debug + 'I: create a *Check TextView* Action!')

    def generate_seekbar_action(self, executable_obj):
        action = Action()
        self.actionIDCounter += 1
        action.set_action_property(self.actionIDCounter, executable_obj.cis, executable_obj.text, action.click, self.activity_name)
        if executable_obj.resource_id != '':
            action_cmd = action.click + "(resource-id='" + executable_obj.resource_id + "', instance='" + str(executable_obj.id_instance) + "')\n"
        elif executable_obj.content_desc != '':
            action_cmd = action.click + "(content-desc='" + executable_obj.resource_id + "')\n"
        else:
            action_cmd = action.click + "(className='" + executable_obj.class_name + "',instance='" + str(executable_obj.instance) + "')\n"
        action.set_action_cmd(action_cmd, executable_obj.class_name)
        self.add_invokable_action(action)
        self.logs.append(self.debug + 'I: create an *SeekBar Click* Action!')

    def print_invokable_actions(self):
        for action in self.invokable_actions:
            self.logs.append('<' + action.action_source + '>' + '    ' + str(action.action_id) + '@' + action.action_cmd.strip('\n'))

    def detect_invokable_actions(self):
        for executable_obj in self.ui_executable_objects:
            if not self.extra_invokable_actions and executable_obj.enabled:
                continue
            view_type = executable_obj.get_class_name()
            self.logs.append(self.debug + 'I: view type: ' + view_type)
            if '.TextView' in view_type or '.Button' in view_type or '.ToggleButton' in view_type:
                self.logs.append('clickable = ' + str(executable_obj.clickable) + ', long_clickable = ' + str(executable_obj.long_clickable))
                if executable_obj.clickable == 'true':
                    self.generate_click_action(executable_obj, 'click')
                if executable_obj.long_clickable == 'true':
                    self.generate_click_action(executable_obj, 'clickLong')
                self.logs.append(self.debug + 'I: up to now, detected invokable actions: ')
                self.print_invokable_actions()
                self.logs.append('==========')
            elif '.ImageView' in view_type or '.ImageButton' in view_type:
                self.logs.append('clickable = ' + str(executable_obj.clickable) + ', long_clickable = ' + str(executable_obj.long_clickable))
                if executable_obj.clickable == 'true':
                    self.generate_click_image_action(executable_obj, 'click')
                if executable_obj.long_clickable == 'true':
                    self.generate_click_image_action(executable_obj, 'clickLong')
                self.logs.append(self.debug + 'I: up to now, detected invokable actions: ')
                self.print_invokable_actions()
                self.logs.append('==========')
            elif '.EditText' in view_type or '.MultiAutoCompleteTextView' in view_type:
                self.generate_edit_text_action(executable_obj)
            elif '.CheckBox' in view_type or '.RadioButton' in view_type:
                self.logs.append('checkable = ' + executable_obj.checkable)
                if executable_obj.checkable:
                    self.generate_check_action(executable_obj)
            elif '.CheckedTextView' in view_type:
                self.logs.append('checkable = ' + executable_obj.checkable)
                if executable_obj.checkable:
                    self.generate_check_textview_action(executable_obj)
            elif '.SeekBar' in view_type:
                self.logs.append('clickable = ' + executable_obj.clickable)
                if executable_obj.clickable == 'true':
                    self.generate_seekbar_action(executable_obj)

        self.add_system_actions()
        self.logs.append('==========')
        self.logs.append(self.debug + 'I: the final detected invokable actions on this app state: ')
        self.print_invokable_actions()

    def add_system_actions(self):
        self.logs.append(self.debug + 'I: add possible SYSTEM actions for the app state in the Activity: ' + self.activity_name)
        if self.activity_name == self.entry_activity_name:
            menu_action = Action()
            self.actionIDCounter += 1
            view_cis = ''
            menu_action.set_system_action_property(self.actionIDCounter, view_cis, ActionConstValue.MenuActionCmd, self.activity_name)
            self.add_invokable_action(menu_action)
        back_action = Action()
        self.actionIDCounter += 1
        back_action.set_system_action_property(self.actionIDCounter, self.CIS, ActionConstValue.BackActionCmd, self.activity_name)
        self.add_invokable_action(back_action)
        if self.isScrollable:
            action = Action()
            self.actionIDCounter += 1
            action.set_action_property(self.actionIDCounter, self.CIS, '', ActionConstValue.Scroll, self.activity_name)
            action_cmd = ActionConstValue.Scroll + "(direction='down')\n"
            action.set_action_cmd(action_cmd, '')
            self.add_invokable_action(action)
            self.logs.append(self.debug + 'I: create a *Scroll Down* Action!')
            action = Action()
            self.actionIDCounter += 1
            action.set_action_property(self.actionIDCounter, self.CIS, '', ActionConstValue.Scroll, self.activity_name)
            action_cmd = ActionConstValue.Scroll + "(direction='up')\n"
            action.set_action_cmd(action_cmd, '')
            self.add_invokable_action(action)
            self.logs.append(self.debug + 'I: create a *Scroll Up* Action!')

    def output_file(self):
        with open(self.command_file_path, 'w') as f:
            for action in self.invokable_actions:
                f.write('    ' + str(action.action_id) + '@' + action.action_cmd.strip('\n') + '\n')

    def get_events(self):
        events = []
        for action in self.invokable_actions:
            events.append('    ' + str(action.action_id) + '@' + action.action_cmd.strip('\n') + '\n')

        return events


if __name__ == '__main__':
    print('I: start android app static analysis to detect actions.... ')
    file_path = '/home/tim/PyCharmProject/Q-testing/benchmark/GoodWeather_jacoco-output-1/stoat_fsm_output/ui_0_.xml'
    e = EventExtractor('', '', file_path, '', '')
    e.extract_event()
    for lo in e.ui_layout_objects:
        print(('[ui_layout_objects]' + lo.pkg_name + ' ' + lo.class_name))

    for eo in e.ui_executable_objects:
        print(('[ui_executable_objects]' + eo.pkg_name + ' ' + eo.class_name + ' ' + eo.resource_id))

    e.detect_invokable_actions()
    e.output_file()
