import logging
import sys

from rvandroid.domain.classes import Classes
from rvandroid.parser.static import reach_parser
from rvandroid.parser.static.base_parser import create_parser_factory
from rvandroid.parser.static.reach_parser import ReachParser

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    static_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/static"
    apk = "cryptoapp.apk"
    reach_file = f"{static_folder}/{apk}.reach"

    parser = ReachParser()
    # parser = create_parser_factory(ReachParser)

    classes = parser.parse_file(reach_file, None, None, None)
    # classes = reach_parser.read_reachable_methods(reach_file)

    classes_count = 0
    methods_count = 0
    for clazz in classes.get_classes():
        classes_count += 1
        print(clazz.name)
        for method in clazz.methods:
            methods_count += 1
            print(f"  - {method} ===> {method.params}")

    print(f"Classes: {classes_count}")
    print(f"Methods: {methods_count}")