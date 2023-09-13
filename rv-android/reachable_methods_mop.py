#!/usr/bin/env python
import os

from androguard.misc import AnalyzeAPK
from androguard.core.bytecodes.apk import APK
from androguard.core.bytecodes.dvm import DalvikVMFormat, DalvikCode
from androguard.core.analysis.analysis import Analysis, MethodAnalysis, BasicBlocks
from networkx import MultiDiGraph
import networkx as nx
from networkx.algorithms import tournament
from commands.command import Command
from settings import LIB_DIR
import sys
import csv

def exec(apk_path):

    mop_specs_dir = '/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-agent/src/main/mop'
    methods_file = '/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/reachable-methods/reachable-javamop/methods.csv'
    jca_methods = get_javamop_methods(mop_specs_dir, methods_file)

    print("Analisando apk ...")
    reachable_methods = []
    apk, _, a = AnalyzeAPK(apk_path)

    # conjunto com os nomes das classes de entrada (activity, receiver, service),
    # ja no formato do androguard (br/unb/cic/...), mas nao completo (ainda) a ponto de poder comparar se o nome da classe eh igual
    entrypoints_classes = get_entrypoints_classes(apk)

    # conjunto com os nodes do callgraph q representam os entrypoints
    # todos os metodos de cada uma das classes do entrypoints_classes
    entrypoints, methods = get_nodes(a, entrypoints_classes, jca_methods)

    print(methods)

    uses = uses_jca(a, entrypoints, methods)

    print("{} uses JCA? {}".format(apk_path, uses))

    print("FIM DE FESTA")


def get_javamop_methods(mop_specs_dir: str, methods_file: str):
    reach_javamop_jar = os.path.join(LIB_DIR, 'reachable', 'reach-mop.jar')
    javamop_methods_cmd = Command("java", [
        '-jar',
        reach_javamop_jar,
        '-d',
        mop_specs_dir,
        '-o',
        methods_file
    ])
    reach_javamop_result = javamop_methods_cmd.invoke(stdout=sys.stdout)
    #TODO checar se resultado foi ok

    methods = dict()
    with open(methods_file, 'r') as data:
        for line in csv.reader(data):
            class_name = line[0].replace('.', '/')
            method_name = line[1]
            if class_name not in methods:
                methods[class_name] = set()
            methods[class_name].add(method_name)
    return methods

def get_entrypoints_classes(a: APK):
    print("get entry points ...")
    entrypoints = set()

    for c in a.get_activities():
        entrypoints.add(c.replace('.', '/'))
    for c in a.get_receivers():
        entrypoints.add(c.replace('.', '/'))
    for c in a.get_services():
        entrypoints.add(c.replace('.', '/'))

    print('entrypoints = {}'.format(len(entrypoints)))

    return entrypoints

def get_nodes(a: Analysis, entrypoints_classes: set, jca_methods: dict):
    entrypoints = set()
    methods = set()
    cg = a.get_call_graph()

    node: MethodAnalysis
    for node in cg.nodes:
        for e in entrypoints_classes:
            if e in str(node.get_class_name()) and str(node.get_access_flags_string()) in ["public", "protected"]:
                entrypoints.add(node)
        for clazz in jca_methods:
            if clazz in str(node.get_class_name()):
                print(node.get_class_name())
                for method in jca_methods[clazz]:
                    print("\t - {} ::: {}".format(method, node.get_method().get_name()))
                    if method in str(node.get_method().get_name()):
                        methods.add(node)

    return entrypoints, methods

def get_entrypoints(a: Analysis, entrypoints_classes: set):
    entrypoints = set()
    cg = a.get_call_graph()

    node: MethodAnalysis
    for node in cg.nodes:
        for e in entrypoints_classes:
            if e in str(node.get_class_name()) and str(node.get_access_flags_string()) in ["public", "protected"]:
                entrypoints.add(node)

    return entrypoints

def uses_jca(a: Analysis, entrypoints: set, methods: set):
    cg = a.get_call_graph()
    for e in entrypoints:
        for m in methods:
            if nx.has_path(cg, e, m):
                return True
    return False

if __name__ == "__main__":
    base_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
    apk = "cryptoapp.apk"
    exec(os.path.join(base_dir, apk))
