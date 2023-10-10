#!/usr/bin/env python
import os

from androguard.misc import AnalyzeAPK
from androguard.core.bytecodes.apk import APK
from androguard.core.bytecodes.dvm import DalvikVMFormat, DalvikCode
from androguard.core.analysis.analysis import Analysis, MethodAnalysis, BasicBlocks
from networkx import MultiDiGraph
import networkx as nx
from networkx.algorithms import tournament


def exec(apk_path):
    print("Analisando apk ...")
    reachable_methods = []
    apk, _, a = AnalyzeAPK(apk_path)

    # conjunto com os nomes das classes de entrada (activity, receiver, service),
    # ja no formato do androguard (br/unb/cic/...), mas nao completo (ainda) a ponto de poder comparar se o nome da classe eh igual
    entrypoints_classes = get_entrypoints_classes(apk)

    # conjunto com os nodes do callgraph q representam os entrypoints
    # todos os metodos de cada uma das classes do entrypoints_classes
    entrypoints = get_entrypoints(a, entrypoints_classes)

    print("ENTRYPOINTS: ")
    n: MethodAnalysis
    for n in entrypoints:
        print("\t - -> {} ::: {} ::: {}".format(n.get_class_name(), n.get_method().get_name(),
                                                n.get_access_flags_string()))
    print("QTDE_ENTRYPOINTS: {}".format(len(entrypoints)))

    # visita todos os nodes e verifica se este tem um caminho entre algum entrypoint e este node
    reachable_methods = get_all_reachable_methods(a, entrypoints)

    print("REACHABLE_METHODS: ")
    m: MethodAnalysis
    for m in reachable_methods:
        print("{} ::: {}".format(m.get_class_name(), m.get_method().get_name()))
    print("QTDE_REACHABLE_METHODS: {}".format(len(reachable_methods)))

    print("FIM DE FESTA")


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


def get_entrypoints(a: Analysis, entrypoints_classes: set):
    entrypoints = set()
    cg = a.get_call_graph()

    node: MethodAnalysis
    for node in cg.nodes:
        for e in entrypoints_classes:
            if e in str(node.get_class_name()) and str(node.get_access_flags_string()) in ["public", "protected"]:
                entrypoints.add(node)

    return entrypoints

def get_all_reachable_methods(a: Analysis, entrypoints: set):
    reachable_methods = set()
    cg = a.get_call_graph()

    node: MethodAnalysis
    for node in cg.nodes:
        if node not in entrypoints:
            for e in entrypoints:
                if nx.has_path(cg, e, node):
                    reachable_methods.add(node)

    return reachable_methods


if __name__ == "__main__":
    base_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
    apk = "cryptoapp.apk"
    exec(os.path.join(base_dir, apk))
