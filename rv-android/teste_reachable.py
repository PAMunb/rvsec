import json
import os
import analysis.coverage as cov
from constants import EXTENSION_SOOT



if __name__ == '__main__':
    base_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples"
    # apk = "cryptoapp.apk"
    apk = "app-debug.apk"

    import analysis.reachable_methods_mop_novo as teste
    teste.reachable_methods_that_uses_jca(os.path.join(base_dir, apk))
