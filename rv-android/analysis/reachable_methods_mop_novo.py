#!/usr/bin/env python
import csv
import json
import os
import sys

import networkx as nx
from androguard.core.analysis.analysis import Analysis, MethodAnalysis
from androguard.core.bytecodes.apk import APK
from androguard.misc import AnalyzeAPK

from commands.command import Command
from settings import LIB_DIR

from settings import MOP_DIR

def reachable_methods_that_uses_jca(apk_path: str):
    reachable = {}
    #TODO
    methods_file = '/tmp/methods.csv'

    print("Analisando apk ...")
    a: Analysis
    apk, _, a = AnalyzeAPK(apk_path)

    jca_methods = get_javamop_methods(MOP_DIR, methods_file)
    entrypoints_classes = get_entrypoints_classes(apk)

    entrypoints, methods = get_nodes(a, entrypoints_classes, jca_methods)

    reachable_methods = get_all_reachable_methods(a, apk, entrypoints)

    print("REACHABLE_METHODS: ")
    for m in reachable_methods:
        clazz = get_class_name(m)
        method = str(m.name)

        if "MessageDigest" in clazz:
            print("reach: {} :: {} :: {}".format(m.get_class_name(), m.name, m.get_descriptor()))

        # reachable_methods = {"class": m.get_class_name(), "method": m.name, "params": m.get_descriptor(), "uses_jca": False}
        if clazz not in reachable:
            reachable[clazz] = {"methods": {}}
        if method not in reachable[clazz]["methods"]:
            reachable[clazz]["methods"][method] = {"uses_jca": False}
    print("%%%%%%%%%%%%%%%%")
    json_formatted_str = json.dumps(reachable, indent=2)
    print(json_formatted_str)
    print("***********************")

    cg = a.get_call_graph()
    for method in reachable_methods:
        for jca_method in methods:
            if cg.has_successor(method, jca_method):
                print(">>>>> {} :: {} :: {}".format(get_class_name(method), method.name, method.get_descriptor()))


    print("FIM DE FESTA")


def get_class_name(m: MethodAnalysis):
    text = str(m.get_class_name()).replace("/", ".")
    text = text.replace(";", "")
    if text.startswith("L"):
        text = text[1:]
    return text


#TODO criar o methods_file .... nao receber como parametro
def get_javamop_methods(mop_specs_dir: str, methods_file: str):
    mop_extractor_jar = os.path.join(LIB_DIR, 'mop-extractor', 'mop-extractor.jar')
    mop_extractor_cmd = Command("java", [
        '-jar',
        mop_extractor_jar,
        '-t',
        'METHODS',
        '-d',
        mop_specs_dir,
        '-o',
        methods_file
    ])
    mop_extractor_result = mop_extractor_cmd.invoke(stdout=sys.stdout)
    if mop_extractor_result.code != 0:
        raise Exception("Error while finding methods in MOP specs: {0}. {1}".format(mop_extractor_result.code,
                                                                                    mop_extractor_result.stderr))

    methods = dict()
    with open(methods_file, 'r') as data:
        for line in csv.reader(data):
            class_name = line[0].replace('.', '/')
            method_name = line[1]
            if class_name not in methods:
                methods[class_name] = set()
            methods[class_name].add(method_name)
    os.remove(methods_file)
    return methods


def get_entrypoints_classes(a: APK):
    print("get entry points classes ...")
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
    print("get entry points ...")
    entrypoints = set()
    cg = a.get_call_graph()

    node: MethodAnalysis
    for node in cg.nodes:
        for e in entrypoints_classes:
            if e in str(node.get_class_name()) and str(node.get_access_flags_string()) in ["public", "protected"]:
                entrypoints.add(node)

    return entrypoints


def get_all_reachable_methods(a: Analysis, apk: APK, entrypoints: set):
    reachable_methods = set()
    cg = a.get_call_graph()
    package = apk.get_package().replace(".", "/")

    node: MethodAnalysis
    for node in cg.nodes:
        if node not in entrypoints:  # and not node.is_external() and not node.is_android_api():
            clazz = str(node.get_class_name())
            for e in entrypoints:
                #TODO limita pelo pacote mesmo?
                if package in clazz and nx.has_path(cg, e, node):
                    reachable_methods.add(node)
        else:
            #entrypoint is reachable
            reachable_methods.add(node)

    return reachable_methods


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
                for method in jca_methods[clazz]:
                    if method in str(node.get_method().get_name()):
                        methods.add(node)

    return entrypoints, methods

def uses_jca(a: Analysis, entrypoints: set, methods: set):
    cg = a.get_call_graph()
    for e in entrypoints:
        for m in methods:
            if nx.has_path(cg, e, m):
                return True
    return False
