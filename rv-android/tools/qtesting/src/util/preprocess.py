from hashlib import md5
import logging, os, sys, xml.dom.minidom, xml.etree.ElementTree, subprocess
from tensorflow.keras.preprocessing.sequence import pad_sequences
logging.basicConfig(format='%(asctime)s : %(filename)s[line:%(lineno)d] : %(levelname)s : %(message)s', level=logging.INFO)
bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
WIDGET_CLASS_FILE_PATH = os.path.abspath(os.path.join(bundle_dir, './widget_classes.txt'))
SCREEN_RESOLUTION_X = 768
SCREEN_RESOLUTION_Y = 1280

class Preprocess(object):

    def __init__(self, DEVICE_ID):
        global SCREEN_RESOLUTION_X
        global SCREEN_RESOLUTION_Y
        self.widget_class_map = {}
        self.widget_class_list = []
        self.read_widget_classes()
        result = subprocess.getoutput('adb -s ' + DEVICE_ID + ' shell wm size')
        if 'Physical size:' in result:
            offset = result.rindex('Physical size:') + 14
            xAndyStr = result[offset:]
            xAndy = xAndyStr.split('x')
            SCREEN_RESOLUTION_X = int(xAndy[0])
            SCREEN_RESOLUTION_Y = int(xAndy[1])

    def read_widget_classes(self):
        f = open(WIDGET_CLASS_FILE_PATH, 'r')
        for line in f.readlines():
            self.widget_class_list.append(line.strip('\n'))

    def extract_vectors(self, xml_tree):
        vectors = []
        root = xml_tree.getroot()
        self.preorder_traverse(vectors, root)
        vectors = self.split_and_zero_padding([vectors], 100)
        return vectors

    def preorder_traverse(self, vectors, node):
        if 'hierarchy' != node.tag:
            vector = self.extract_vector_from_node(node)
            vectors.append(vector)
        for child in node:
            self.preorder_traverse(vectors, child)

    def extract_vector_from_node(self, node):
        node_vector = [0.0] * (5 + len(self.widget_class_list) + 1 + 160)
        if node.get('NAF') == '' or not node.get('NAF'):
            node_vector[0] = 0.0
        elif node.get('NAF') == 'true':
            node_vector[0] = 1.0
        bounds_string = node.get('bounds')
        if bounds_string == '' or not bounds_string:
            print(node)
            node_vector[1] = 0.0
            node_vector[2] = 0.0
            node_vector[3] = 0.0
            node_vector[4] = 0.0
        else:
            lt_bounds_string = bounds_string[0:bounds_string.rfind('[')]
            rb_bounds_string = bounds_string[bounds_string.rfind('['):len(bounds_string)]
            lt_x = int(lt_bounds_string[1:lt_bounds_string.find(',')])
            lt_y = int(lt_bounds_string[lt_bounds_string.find(',') + 1:lt_bounds_string.rfind(']')])
            rb_x = int(rb_bounds_string[1:rb_bounds_string.find(',')])
            rb_y = int(rb_bounds_string[rb_bounds_string.find(',') + 1:rb_bounds_string.rfind(']')])
            node_vector[1] = round(lt_x / SCREEN_RESOLUTION_X, 2)
            node_vector[2] = round(lt_y / SCREEN_RESOLUTION_Y, 2)
            node_vector[3] = round(rb_x / SCREEN_RESOLUTION_X, 2)
            node_vector[4] = round(rb_y / SCREEN_RESOLUTION_Y, 2)
        widget_class = node.get('class')
        one_hot_num = 0
        for i in range(0, len(self.widget_class_list)):
            if self.widget_class_list[i] == widget_class:
                one_hot_num = i
                break

        if widget_class == self.widget_class_list[one_hot_num]:
            node_vector[one_hot_num + 5] = 1.0
        else:
            node_vector[len(self.widget_class_list) + 5] = 1.0
        content_desc = node.get('content-desc')
        md5_str_16 = str(md5(content_desc.encode('utf-8')).hexdigest())
        md5_str_10 = str(int(md5_str_16, 16))
        if len(md5_str_10) > 40:
            logging.error('length is beyond 40')
        for i in range(0, len(md5_str_10)):
            node_vector[len(self.widget_class_list) + 6 + i] = float(md5_str_10[i]) / 10
            if i >= 39:
                break

        package = node.get('package')
        md5_str_16 = str(md5(package.encode('utf-8')).hexdigest())
        md5_str_10 = str(int(md5_str_16, 16))
        if len(md5_str_10) > 40:
            logging.error('length is beyond 40')
        for i in range(0, len(md5_str_10)):
            node_vector[len(self.widget_class_list) + 46 + i] = float(md5_str_10[i]) / 10
            if i >= 39:
                break

        resource_id = node.get('resource-id')
        md5_str_16 = str(md5(resource_id.encode('utf-8')).hexdigest())
        md5_str_10 = str(int(md5_str_16, 16))
        if len(md5_str_10) > 40:
            logging.error('length is beyond 40')
        for i in range(0, len(md5_str_10)):
            node_vector[len(self.widget_class_list) + 86 + i] = float(md5_str_10[i]) / 10
            if i >= 39:
                break

        text = node.get('text')
        md5_str_16 = str(md5(text.encode('utf-8')).hexdigest())
        md5_str_10 = str(int(md5_str_16, 16))
        if len(md5_str_10) > 40:
            logging.error('length is beyond 40')
        for i in range(0, len(md5_str_10)):
            node_vector[len(self.widget_class_list) + 126 + i] = float(md5_str_10[i]) / 10
            if i >= 39:
                break

        return node_vector

    def split_and_zero_padding(self, df, max_seq_length):
        return pad_sequences(df, padding='pre', truncating='post', maxlen=max_seq_length, dtype='float', value=0.0)
