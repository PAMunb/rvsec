import logging
import re
import os
import io
import time
import sys

from commands.command import Command
from contextlib import contextmanager


class Android:

    @classmethod
    @contextmanager
    def create_emulator(cls, avd_name):
        # Code to acquire resource, e.g.:
        emulator = cls.start_emulator(avd_name)
        try:
            yield emulator
        finally:
            # Code to release resource, e.g.:
            cls.kill_emulator(avd_name)


    @classmethod
    def start_emulator(cls, avd_name):
        logging.info('Starting emulator')        
        start = time.time()
                
        #start_emulator_cmd = Command('emulator', ['-avd', avd_name, '-writable-system', '-wipe-data', '-no-boot-anim', '-no-window', '-netdelay', 'none'])
        start_emulator_cmd = Command('emulator', ['-avd', avd_name, '-writable-system', '-wipe-data', '-no-boot-anim', '-noaudio', '-no-snapshot-save', '-delay-adb'])
        emulator_proc = start_emulator_cmd.invoke_as_deamon()

        logging.info('Waiting for emulator to boot')        
        wait_emulator_cmd = Command('adb', ['wait-for-device'])
        wait_emulator_cmd.invoke()

        root_cmd = Command('adb', [
            'wait-for-device',
            'root',
        ])
        while root_cmd.invoke().stderr.strip().decode('ascii'):
           time.sleep(5)

        adb_remount = Command('adb', ['wait-for-device', 'remount'])
        while adb_remount.invoke().stderr.strip().decode('ascii'):
           time.sleep(5)

        logging.info('Emulator booted!')
        end = time.time()
        elapsed = end - start
        if elapsed > 60:
            logging.info('Emulator took {0} minutes and {1} seconds to boot'.format(int(elapsed / 60), elapsed % 60))
        else:
            logging.info('Emulator took {0} seconds to boot'.format(elapsed))
    

    @classmethod
    def kill_emulator(cls, avd_name):
        logging.info("Killing emulator ...")
        kill_emulator_cmd = Command('adb', ['-s', 'emulator-5554', 'emu', 'kill'])
        kill_emulator_cmd.invoke()
        kill_server_cmd = Command('adb', ['-s', 'emulator-5554', 'kill-server'])
        kill_server_cmd.invoke()
        kill_locks_cmd = Command('rm', ['~/.android/avd/{}.avd/*.lock'.format(avd_name)])
        kill_locks_cmd.invoke()
        time.sleep(10)
        logging.info('Emulator has been killed')


    @classmethod
    def install_apk(cls, file):
        logging.info("Installing APK: {0}".format(file))
        root_cmd = Command('adb', [
            'root',
        ])
        result = root_cmd.invoke()
        readlink_cmd = Command('readlink', ['-f', file])
        readlink_result = readlink_cmd.invoke()
        install_cmd = Command('adb', [
            '-s',
            'emulator-5554',
            'install',
            '-r',
            readlink_result.stdout.strip().decode('ascii')
        ])
        install_cmd.invoke()


    @classmethod
    def uninstall_apk(cls, file):
        package_name = cls.get_package_name(file)
        if package_name is not None:
            uninstall_cmd = Command('adb', ['-s', 'emulator-5554', 'uninstall', package_name])
            uninstall_cmd.invoke()


    @classmethod
    def get_package_name(cls, apk_path):
        get_package_list_cmd = Command('aapt', ['list', '-a', apk_path])
        get_package_list_result = get_package_list_cmd.invoke()
        get_package_list_result_str = get_package_list_result.stdout.strip().decode('ascii', 'ignore')

        match = re.search(r'Package Group .* packageCount=1 name=(.*)', get_package_list_result_str, re.MULTILINE)
        if match is None:
            match = re.search(r'package=(.*)', get_package_list_result_str, re.MULTILINE)
            if match is None:
                return None
        return match.group(1)  


    def get_permissions(cls, apk_path): 
        permissions = []
        get_permissions_cmd = Command('aapt', ['d', 'permissions', apk_path])
        get_permissions_result = get_permissions_cmd.invoke()
        get_permissions_result_str = get_permissions_result.stdout.strip().decode('ascii', 'ignore') 

        matches = re.findall(r"uses-permission: name='.*'", get_permissions_result_str, re.MULTILINE)        
        for match in matches:
            tmp = match.replace("uses-permission: name='","")
            tmp = tmp.replace("'","")            
            permissions.append(tmp)
        return permissions

        