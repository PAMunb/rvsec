import json
import os
import analysis.coverage as cov
from constants import EXTENSION_METHODS

import analysis.results_analysis as res

if __name__ == '__main__':
    result_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/teste"
    res.process_results(result_dir)
