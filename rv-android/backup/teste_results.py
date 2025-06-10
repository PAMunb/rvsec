import logging
import sys

from rvandroid import analysis as res

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    result_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/results/20250123092100"

    res.process_results(result_dir)
