"""
Module for parsing reachability analysis results from CSV files.
This parser handles method reachability information for Android applications,
including activity classes and MOP (Monitor-Oriented Programming) methods.
"""

import csv
import logging as logging_api
from typing import List

from rvandroid.domain.classes import Classes, Method, Clazz

# Configure module logger
logging = logging_api.getLogger(__name__)


def read_reachable_methods(input_file: str) -> Classes:
    """
    Parse a reachability analysis CSV file and build a Classes object containing
    all reachable methods and their properties.

    Args:
        input_file (str): Path to the CSV file containing reachability analysis results

    Returns:
        Classes: Object containing all parsed classes and their methods
    """
    logging.debug(f"Starting to parse reachability file: {input_file}")
    classes = Classes()

    with open(input_file, 'r') as data:
        csv_reader = csv.reader(data, delimiter=',')
        # Skip header row
        next(csv_reader)

        for row in csv_reader:
            class_obj = _parse_class(row, classes)
            method = _parse_method(row, class_obj.name)
            classes.add_method(method)

    return classes


def _parse_method_list(input_str: str) -> List[str]:
    """
    Parse a string representing a list of methods in the format "[method1;method2;...]"

    Args:
        input_str (str): String containing semicolon-separated method names

    Returns:
        List[str]: List of method names, empty list if no methods found
    """
    # Remove quotes, brackets, and whitespace
    cleaned_str = input_str.strip('"[]')
    return cleaned_str.split(";") if ";" in cleaned_str else []


def _parse_class(row: List[str], classes: Classes) -> Clazz:
    """
    Parse class information from a CSV row and add it to the Classes collection.

    Args:
        row (List[str]): CSV row containing class information
        classes (Classes): Existing Classes object to add the parsed class to

    Returns:
        Classes: The class object that was added
    """
    name = row[0]
    is_activity = eval(row[1].capitalize())
    is_main_activity = eval(row[2].capitalize())
    return classes.add_clazz(name, is_activity, is_main_activity)


def _parse_method(row: List[str], class_name: str) -> Method:
    """
    Parse method information from a CSV row.

    Args:
        row (List[str]): CSV row containing method information
        class_name (str): Name of the class this method belongs to

    Returns:
        Method: Created Method object with parsed information
    """
    return Method(
        class_name=class_name,
        name=row[3],
        params=_parse_params_list(row[4]),
        signature=row[8],
        reachable=eval(row[5].capitalize()),
        reaches_mop=eval(row[6].capitalize()),
        directly_reaches_mop=eval(row[7].capitalize())
    )


def _parse_params_list(params_str: str) -> List[str]:
    """
    Parse a string representing method parameters in the format "[param1;param2;...]"

    Args:
        params_str (str): String containing parameter types

    Returns:
        List[str]: List of parameter types, empty list if no parameters
    """
    # Remove brackets
    cleaned_str = params_str[1:-1].strip()
    return cleaned_str.split(";") if cleaned_str else []
