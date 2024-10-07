import csv
import json
import os


class WorkingMemory:
    def __init__(self, app_info):
        self.app_info = app_info


def execute(reach, gesda, gator):
    new_working_memory(reach, gesda, gator)


def parse_reach(reach):
    print("parse_reach: {}".format(reach))
    extension = os.path.splitext(reach)[1]
    print("extension={}".format(extension))
    if ".csv" == extension.strip().lower():
        parse_reach_csv(reach)
    else:
        raise Exception("Invalid file format: {}".format(reach))


def parse_reach_csv(reach):
    all_classes = {}
    windows = {}
    with open(reach, 'r') as data:
        for line in csv.DictReader(data):
            print(line)

            clazz_name = line["className"]
            if clazz_name not in all_classes:
                all_classes[clazz_name] = {"is_activity": to_bool(line["isActivity"]),
                                           "is_main": None,
                                           "methods": {}}

            method_name = line["methodName"]
            all_classes[clazz_name]["methods"][method_name] = {"reachable": to_bool(line["reachable"]),
                                                               "reaches_mop": to_bool(line["reachesMop"]),
                                                               "reaches_mop_inside_app": False, #TODO json tem todos os caminhos ... true se algum caminho acessa um metodo MOP diretamente do app
                                                               "directly_reaches_mop": to_bool(line["directlyReachesMop"])}

    print(all_classes)

def to_bool(value):
    return eval(value.lower().capitalize())

def new_working_memory(reach, gesda, gator):
    parse_reach(reach)


def parse_gesda(gesda):
    with open(gesda, 'r') as file:
        data = json.load(file)
        print(data)
        print("APP: file={}, package={}".format(data["fileName"], data["packageName"]))
        for window in data['windows']:
            print(" - Window: name={}, isMain={}".format(window["name"], window["isMain"]))
            for widget in window["widgets"]:
                print("   - Widget: name={}, type={} ::: {}".format(widget["name"], widget["type"], widget))
                if "listeners" in widget:
                    for listener in widget["listeners"]:
                        print("     - {} :: {}".format(listener["type"], listener["callbackMethod"]))


def parse_gator(gator):
    with open(gator, 'r') as file:
        data = json.load(file)
        print(data)


if __name__ == '__main__':
    gesda = "/home/pedro/tmp/rvsec-gesda.json"
    reach = "/home/pedro/tmp/rvsec-reach.csv"
    gator = "/home/pedro/tmp/rvsec-gator.json"

    # parse_gesda(gesda)
    # parse_gator(gator)
    execute(reach, gesda, gator)
