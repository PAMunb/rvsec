import argparse
import importlib
import logging
import os
import sys
import time

import experiment_01
import utils

available_tools = {}
output_formats = {}


def qualified_name(p):
    return p.replace(".py", "").replace("./", "").replace("/", ".")


def load_tools():
    '''Load all available tools.

     A tool must be defined in a subdirectory within
     the tools folder, in a python module named tool.py.
     This module must also declare a class named ToolSpec,
     which shoud inherit from AbstractTool.
    '''
    for subdir, dirs, files in os.walk('.' + os.sep + 'tools'):
        for filename in files:
            if filename == 'tool.py':
                tool_module = importlib.import_module(qualified_name(subdir + os.sep + filename))
                tool_class = getattr(tool_module, 'ToolSpec')
                tool_instance = tool_class()
                available_tools[tool_instance.name] = tool_instance


if __name__ == '__main__':

    load_tools()

    # Start catching arguments
    parser = argparse.ArgumentParser(description='Experiment 01 ...')

    # list available tools
    parser.add_argument("--list-tools", help="list available tools", action="store_true")

    # List of test tools used in the experiment
    parser.add_argument('-tools', nargs='+', help='List of test tools used in the experiment', default=['monkey'])

    # Threshold of the execution time in the experiment
    parser.add_argument('-t', nargs='+', default=[60],
                        help='(-t -time) Threshold of the execution time (in seconds) in the experiment', type=int)

    # Number of repetitions used in the experiment
    parser.add_argument('-r', default=1, help='(-r, -repetitions) Number of repetitions used in the experiment',
                        type=int)

    #TODO opcao skip_experiment ... para so gerar os monitores e instrumentar
    parser.add_argument("--skip_monitors", help="Skip monitors generation", action="store_true")
    parser.add_argument("--skip_instrument", help="Skip instrumentation", action="store_true")
    parser.add_argument("--no_window", help="Starts emulator with '-no-window'", action="store_true")

    # Enable DEBUG mode.
    parser.add_argument('--debug', help='Run in DEBUG mode (default: false)', dest='debug', action='store_true')

    # Print program version
    # parser.add_argument('--version', help='Print the experiment version', dest='version', action='store_true')

    args = parser.parse_args()
    # End catching arguments

    # TODO configurar log
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG if args.debug else logging.INFO)

    if args.list_tools:
        logging.info(" [Listing available tools] \n")
        for key in available_tools:
            print(" [{0}] {1} \n".format(key, available_tools[key].description))
        sys.exit(0)

    # if args.version:
    #     print('v{0}'.format(__version__))
    #     sys.exit(0)

    tools = []
    for t in available_tools:
        for tool in args.tools:
            if t == tool:
                tools.append(available_tools[t])

    generate_monitors = not args.skip_monitors
    instrument = not args.skip_instrument

    logging.info('############# STARTING EXPERIMENT #############')
    start = time.time()

    experiment_01.execute(args.r, args.t, tools, generate_monitors, instrument, args.no_window)

    end = time.time()
    elapsed = end - start
    logging.info('It took {0} to complete'.format(utils.to_readable_time(elapsed)))

    logging.info('############# ENDING EXPERIMENT #############')
