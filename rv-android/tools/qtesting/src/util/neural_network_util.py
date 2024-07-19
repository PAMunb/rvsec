import re
from tensorflow.keras import backend as K
from tensorflow.keras.layers import Layer
from tensorflow.keras.preprocessing.sequence import pad_sequences
import numpy as np, itertools
max_length = 0

def string_to_vector(df):
    global max_length
    for index, row in df.iterrows():
        for gui_hierarchy in ['gui_hierarchy1', 'gui_hierarchy2']:
            s2v = []
            for vector_string in str(row[gui_hierarchy]).split('\n'):
                if vector_string != '':
                    vector = []
                    for sub_string in vector_string.split(' '):
                        if sub_string != '':
                            vector.append(float(sub_string))

                    s2v.append(vector)

            df.at[(index, gui_hierarchy + '_v')] = s2v
            if len(s2v) > max_length:
                max_length = len(s2v)
                print(('max length is now : ' + str(max_length)))

    return df


def split_and_zero_padding(df, max_seq_length):
    X = {'left': (df['gui_hierarchy1_v']), 'right': (df['gui_hierarchy2_v'])}
    for dataset, side in itertools.product([X], ['left', 'right']):
        dataset[side] = pad_sequences(dataset[side], padding='pre', truncating='post', maxlen=max_seq_length)

    return dataset


class ManDist(Layer):
    """
    Keras Custom Layer that calculates Manhattan Distance.
    """

    def __init__(self, **kwargs):
        self.result = None
        super(ManDist, self).__init__(**kwargs)
        return

    def build(self, input_shape):
        print(input_shape)
        super(ManDist, self).build(input_shape)

    def call(self, x, **kwargs):
        self.result = K.exp(-K.sum(K.abs(x[0] - x[1]), axis=1, keepdims=True))
        return self.result

    def compute_output_shape(self, input_shape):
        return K.int_shape(self.result)

    def get_config(self):
        base_config = super(ManDist, self).get_config()
        return base_config


class EmptyWord2Vec:
    """
    Just for test use.
    """
    vocab = {}
    word_vec = {}
