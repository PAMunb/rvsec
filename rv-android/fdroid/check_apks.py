import os
from androguard.core.bytecodes.apk import APK


def execute(apks_path):
    invalids = set()
    for apk_filename in os.listdir(apks_path):
        apk_path = os.path.join(apks_path, apk_filename)
        try:
            apk = APK(apk_path)
        except:
            os.remove(apk_path)
            invalids.add(apk_path)
    print("INVALIDS: {}".format(len(invalids)))
    for i in invalids:
        print(i)


if __name__ == '__main__':
    path = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks"
    execute(path)
