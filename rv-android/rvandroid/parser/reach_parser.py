import csv
from rvandroid.constants import *
from rvandroid.parser.classes import *


def read_reachable_methods(in_file: str):
    classes = Classes()    
    with open(in_file, 'r') as data:
        csv_reader = csv.reader(data, delimiter=',')
        next(csv_reader)
        for line in csv_reader:
            clazz = __to_clazz(line, classes)
            method = __to_method(line, clazz.name)
            classes.add_method(method)
    return classes


def __to_list(string_input) -> list[str]:
    """
    Converts a string in the format "[<method>;<method2>]" to a list of strings.

    Args:
        string_input: A string in the specified format.

    Returns:
        A list of strings, or None if the input string is not in the correct format.
    """
    method_list = []
    # Remove the outer double quotes and square brackets
    cleaned_string = string_input.strip('"[]')
    if ";" in cleaned_string:
        method_list = cleaned_string.split(";")
    return method_list


#class,is_activity,is_main_activity,method,params,reachable,reaches_mop,directly_reaches_mop,signature,mop_methods_reached
def __to_clazz(line, classes: Classes):
    name = line[0]
    is_activity = eval(line[1].capitalize())
    is_main_activity = eval(line[2].capitalize())
    return classes.add_clazz(name, is_activity, is_main_activity)


def __to_method(line, class_name: str):
    name = line[3]
    params = __to_params_list(line[4])
    signature = line[8]
    reachable = eval(line[5].capitalize())
    reaches_mop = eval(line[6].capitalize())
    directly_reaches_mop = eval(line[7].capitalize())
    directly_reachable_mop = __to_list(line[9])
    print(f"directly_reachable_mop={directly_reachable_mop}")
    return Method(class_name, name, params,signature,reachable,reaches_mop,directly_reaches_mop,directly_reachable_mop)


def __to_params_list(input) -> list[str]:
    # input examples: "[byte[];java.lang.String]", "[]"
    # Remove the first and last characters of the string
    input = input[1:-1]
    # Remove leading/trailing whitespace
    input = input.strip()
    # If the string is empty, return an empty list
    if input == "":
        return []
    # If the string is not empty, split the string into a list of strings
    return input.split(";")