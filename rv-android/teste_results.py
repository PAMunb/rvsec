import json
import logging
import os
import sys

import analysis.coverage as cov
from constants import EXTENSION_METHODS

import analysis.results_analysis as res

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    result_dir = "/home/pedro/desenvolvimento/RV_ANDROID/RESULTS_experimento01/09/20240220124040"
    # result_dir = "/home/pedro/desenvolvimento/RV_ANDROID/RESULTS_experimento01/18/20240212124648"
    res.process_results(result_dir)
