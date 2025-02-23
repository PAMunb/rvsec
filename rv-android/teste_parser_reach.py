import logging
import sys

from rvandroid.parser.static import reach_parser

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    reach_file = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static/cryptoapp.apk.reach"
    classes = reach_parser.read_reachable_methods(reach_file)
    print(classes)

    for clazz in classes.get_classes():
        print(clazz.name)
        for method in clazz.methods:
            print(f"  - {method} ===> {method.params}")
