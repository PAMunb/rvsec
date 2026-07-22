import os
from subprocess import call

from .utils import make_temp_dir

JAR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                   '..', '..', 'apktool', 'apktool.jar')


def decode_res_from_apk(apk_path):
    return decode_apk(apk_path, ['--no-src'])


def decode_src_from_apk(apk_path):
    return decode_apk(apk_path, ['--no-res'])


def decode_apk(apk_path, opt=None):
    tmp_dir = make_temp_dir('gator-')
    cmd = ['java', '-jar', JAR, 'd', '-f']
    if opt is not None:
        cmd.extend(opt)
    cmd.extend(['--output', tmp_dir, apk_path])
    call(cmd)
    return tmp_dir
