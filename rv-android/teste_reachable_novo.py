import csv
import json
import os
import sys

import networkx as nx
from androguard.core.analysis.analysis import Analysis, MethodAnalysis
from androguard.core.bytecodes.apk import APK
from androguard.misc import AnalyzeAPK
from networkx import MultiDiGraph

from commands.command import Command
from settings import LIB_DIR, WORKING_DIR

from settings import MOP_DIR
from constants import *


def extract_reachable_methods(apk_path: str, out_file: str):
    reachable = reachable_methods_that_uses_jca(apk_path)
    write_reachable_methods(reachable, out_file)


def reachable_methods_that_uses_jca(apk_path: str):
    # USE_JCA = reachable method (ONLY inside apk package) that directly use jca
    reachable = {}

    a: Analysis
    apk, _, a = AnalyzeAPK(apk_path)
    cg = a.get_call_graph()

    methods_used_in_specs_str = get_javamop_methods(MOP_DIR)
    methods_used_in_specs = get_methods_used_in_specs(cg, methods_used_in_specs_str)

    entrypoints_classes = get_entrypoints_classes(apk)
    entrypoints = get_entrypoints(cg, entrypoints_classes)

    reachable_methods = get_reachable_methods(cg, apk, entrypoints)

    for m in cg:
        clazz = get_class_name(m)

        print("clazz={} .... package={}".format(clazz, apk.get_package()))

        if apk.get_package() in clazz or "com.jonbanjo.cupsprint" in clazz:
            method = str(m.name)

            if is_constructor_or_static_initializer(method):
                continue

            if clazz not in reachable:
                reachable[clazz] = {IS_ACTIVITY: clazz in apk.get_activities(), METHODS: {}}
            if method not in reachable[clazz][METHODS]:
                # REACHABLE: alcancavel por algum entrypoint
                # USE_JCA: usa diretamente jca (chama um metodo jca dentro desse metodo)
                # REACHES_JCA: alcanca algum metodo jca
                reachable[clazz][METHODS][method] = {REACHABLE: False, USE_JCA: False, REACHES_JCA: False, "node": m}

            for jca_method in methods_used_in_specs:
                if cg.has_successor(m, jca_method):
                    reachable[clazz][METHODS][method][USE_JCA] = True
                if nx.has_path(cg, m, jca_method):
                    reachable[clazz][METHODS][method][REACHES_JCA] = True

    for m in reachable_methods:
        clazz = get_class_name(m)
        method = str(m.name)
        if is_constructor_or_static_initializer(method):
            continue
        reachable[clazz][METHODS][method][REACHABLE] = True

    for clazz in reachable:
        print("*************** class={}".format(clazz))
        for method in reachable[clazz][METHODS]:
            m = reachable[clazz][METHODS][method]
            if m[REACHES_JCA]: # and not m[USE_JCA]:
                paths = []
                print("***** method={}".format(method))
                for jca_method in methods_used_in_specs:
                    all_simple_paths = nx.all_simple_paths(cg, source=m["node"], target=jca_method)
                    for path___ in all_simple_paths:
                        path = []
                        first = True
                        xxx: MethodAnalysis
                        for xxx in path___:
                            if not first:
                                path.append("{}.{}".format(get_class_name(xxx), xxx.name))
                            else:
                                first = False
                            # print("{} :: {} ::: {} :::: {}".format(get_class_name(xxx), xxx.name, xxx.full_name, xxx.get_descriptor()))
                        paths.append(path)
                m["paths"] = paths
            m["node"] = None


    return reachable


def write_reachable_methods(reachable: dict, out_file: str):
    with open(out_file, 'w') as f:
        f.write("class,is_activity,method,reachable,use_jca\n")
        for clazz in reachable:
            for method in reachable[clazz][METHODS]:
                f.write("{},{},{},{},{}\n".format(clazz, reachable[clazz][IS_ACTIVITY], method, reachable[clazz][METHODS][method][REACHABLE],
                                                  reachable[clazz][METHODS][method][USE_JCA]))


def read_reachable_methods(in_file: str):
    reachable = {}
    with open(in_file, 'r') as data:
        csv_reader = csv.reader(data, delimiter=',')
        next(csv_reader)
        for line in csv_reader:
            clazz = line[0]
            method = line[2]
            if clazz not in reachable:
                reachable[clazz] = {IS_ACTIVITY: eval(line[1]), METHODS: {}}
            reachable[clazz][METHODS][method] = {REACHABLE: eval(line[3]), USE_JCA: eval(line[4])}
    return reachable


def get_class_name(m: MethodAnalysis):
    text = str(m.get_class_name()).replace("/", ".")
    text = text.replace(";", "")
    if text.startswith("L"):
        text = text[1:]
    return text


def get_javamop_methods(mop_specs_dir: str):
    methods_file = os.path.join(WORKING_DIR, 'methods_used_in_specs.txt')
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

    methods: dict[str, set[str]] = {}
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
    entrypoints = set[str]()

    for c in a.get_activities():
        entrypoints.add(c.replace('.', '/'))
    for c in a.get_receivers():
        entrypoints.add(c.replace('.', '/'))
    for c in a.get_services():
        entrypoints.add(c.replace('.', '/'))

    return entrypoints


def get_entrypoints(cg: MultiDiGraph, entrypoints_classes: set[str]):
    entrypoints = set()

    node: MethodAnalysis
    for node in cg.nodes:
        for e in entrypoints_classes:
            if e in str(node.get_class_name()) and str(node.get_access_flags_string()) in ["public", "protected"]:
                entrypoints.add(node)

    return entrypoints


def get_methods_used_in_specs(cg: MultiDiGraph, jca_methods: dict):
    methods = set()

    node: MethodAnalysis
    for node in cg.nodes:
        for clazz in jca_methods:
            if clazz in str(node.get_class_name()):
                for method in jca_methods[clazz]:
                    if method in str(node.get_method().get_name()):
                        methods.add(node)

    return methods


def get_reachable_methods(cg: MultiDiGraph, apk: APK, entrypoints: set[MethodAnalysis]):
    reachable_methods = set[MethodAnalysis]()
    # reachable_methods.update(entrypoints)
    package = apk.get_package()#.replace(".", "/")

    node: MethodAnalysis
    for node in cg.nodes:
        clazz = get_class_name(node)

        if (package in clazz) and (node not in entrypoints):  # and not node.is_external() and not node.is_android_api():
            for e in entrypoints:
                if nx.has_path(cg, e, node):
                    reachable_methods.add(node)

    return reachable_methods


def is_constructor_or_static_initializer(method: str):
    return ("<init>" in method) or ("<clinit>" in method)


def uses_jca(a: Analysis, entrypoints: set, methods: set):
    cg = a.get_call_graph()
    for e in entrypoints:
        for m in methods:
            if nx.has_path(cg, e, m):
                return True
    return False


if __name__ == '__main__':
    base_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples"
    apk = "cryptoapp.apk"

    # base_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_mini"
    # apk = "com.jonbanjo.cupsprintservice_23.apk"

    reachable = reachable_methods_that_uses_jca(os.path.join(base_dir, apk))
    # print(reachable)

    json_formatted_str = json.dumps(reachable, indent=2)
    print(json_formatted_str)
