"""
Module for parsing reachability analysis results from CSV files.
This parser handles method reachability information for Android applications,
including activity classes and MOP (Monitor-Oriented Programming) methods.
"""

import csv
import os
from typing import List, Optional

from rv_android_core.domain.classes import Classes, Method, Clazz
from rv_android_core.domain.window import Windows
from rv_android_core.util.android.signature_normalizer import SignatureNormalizer
from rv_static_analysis.parser.static.base_parser import BaseStaticAnalysisParser


class ReachParser(BaseStaticAnalysisParser):

    def __init__(self):
        """Initialize the Reach parser wrapper."""
        super().__init__("reach")
        self._normalizer = SignatureNormalizer()

    def parse_file(self, file_path: str, package: Optional[str], classes: Optional[Classes],
                   windows: Optional[Windows]) -> Classes:
        self.log_parse_start(file_path)

        if not os.path.exists(file_path):
            self.logger.warning(f"File {file_path} does not exist, returning empty classes")
            return classes if classes is not None else Classes()

        try:
            # Parse reachability information from the file
            classes = self.read_file(file_path)

            # Log successful parsing
            stats = {
                "classes": len(classes.classes),
                "methods": len(classes.methods)
            }
            self.log_parse_complete(file_path, stats)

            return classes
        except Exception as e:
            self.log_parse_error(file_path, e)
            return Classes()

    def read_file(self, file_path):
        classes = Classes()

        with open(file_path, 'r') as data:
            csv_reader = csv.reader(data, delimiter=',')
            # Skip header row
            next(csv_reader)

            for row in csv_reader:
                class_obj = self._parse_class(row, classes)
                method = self._parse_method(row, class_obj.name)
                classes.add_method(method)

        return classes

    def _parse_class(self, row: List[str], classes: Classes) -> Clazz:
        """
        Parse class information from a CSV row and add it to the Classes collection.

        Args:
            row (List[str]): CSV row containing class information
            classes (Classes): Existing Classes object to add the parsed class to

        Returns:
            Classes: The class object that was added
        """
        name = self._normalizer.normalize_class_name(row[0])
        is_activity = eval(row[1].capitalize())
        is_main_activity = eval(row[2].capitalize())
        return classes.add_clazz(name, is_activity, is_main_activity)

    def _parse_method(self, row: List[str], class_name: str) -> Method:
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
            params=self._parse_params_list(row[4]),
            signature=self._normalizer.normalize_signature(row[8]),
            reachable=eval(row[5].capitalize()),
            reaches_mop=eval(row[6].capitalize()),
            directly_reaches_mop=eval(row[7].capitalize())
        )

    def _parse_params_list(self, params_str: str) -> List[str]:
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


def read_reachable_methods(input_file: str):
    parser = ReachParser()
    return parser.parse_file(input_file, None, None, None)
