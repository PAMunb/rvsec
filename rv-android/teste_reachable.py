import json
import os
import analysis.coverage as cov
from constants import EXTENSION_METHODS



if __name__ == '__main__':
    base_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples"
    # apk = "cryptoapp.apk"
    apk = "app-debug.apk"
    # apk = "com.blogspot.e_kanivets.moneytracker_38.apk"
    # apk = "com.xmission.trevin.android.todo_1.apk"

    import analysis.reachable_methods_mop as teste
    #teste.reachable_methods_that_uses_jca(os.path.join(base_dir, apk))
    reachable = teste.reachable_methods_that_uses_jca(os.path.join(base_dir, apk))

    json_formatted_str = json.dumps(reachable, indent=2)
    print(json_formatted_str)
