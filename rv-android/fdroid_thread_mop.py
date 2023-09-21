import requests
import concurrent.futures
import csv
import pandas as pd
import datetime
import threading
import os
import sys
import tempfile
import requests
import func_timeout
import networkx as nx

from androguard.core.analysis.analysis import Analysis, MethodAnalysis
from androguard.core.bytecodes.apk import APK
from androguard.misc import AnalyzeAPK

from commands.command import Command
from settings import LIB_DIR

from call_function_with_timeout import SetTimeoutDecorator


def process_package(package_name, mop_methods, writer):
#    print("PACKAGE: {}".format(package_name))
    
    package = data["packages"][package_name]
    metadata = package["metadata"]
    
    apk_file = get_last_apk_version(package)

    # adiciona apenas apps com URL para o sourceCode
    source = get_source_code_url(metadata)
    if source:
        try:
            apk_path = download_apk(apk_file)

            is_done, is_timeout, error_message, results = is_mop_enabled(apk_path, mop_methods)
            if is_timeout:
                mop_enabled = "Timeout"
            else:
                mop_enabled = "Yes" if results[0] else "No"
            apk = results[1]
            print("Uses JCA? {}".format(mop_enabled))

            last_updated = int(metadata["lastUpdated"]) / 1000

            row = [package_name, metadata["name"]["en-US"], metadata["categories"], mop_enabled,
                apk.get_min_sdk_version(), apk.get_effective_target_sdk_version(), apk_file,
                source, datetime.datetime.fromtimestamp(last_updated).strftime("%Y-%m-%d")]

            # Usar o bloqueio (lock) para escrever no arquivo CSV
            with csv_lock:
                writer.writerow(row)
                print(row)

            delete_file(apk_path)
        except:
            print("Error on app: {}".format(apk_file))

def execute(mop_specs_dir: str, out_file: str):
    print("Executing ...")

    # recupera os metodos usados nas specs mop
    # esses metodos sao usados para recuperar nodes correspondentes no callgraph
    # e depois ver se esses nodes sao alcancaveis pelos entrypoints
    mop_methods = get_methods_used_in_specs(mop_specs_dir)

    # recupera o índice do repositório do F-droid
    # https://f-droid.org/pt_BR/docs/All_our_APIs/
    print("Recuperando índice do repositório do f-froid: https://f-droid.org/repo/index-v2.json")
    response = requests.get('https://f-droid.org/repo/index-v2.json')
    global data
    data = response.json()

    # Abre o arquivo CSV para salvar os dados dos aplicativos
    with open(out_file, 'w', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)

        header = ["package", "name", "categories", "mop", "min_sdk", "target_sdk", "file", "sourceCode", "lastUpdated"]
        writer.writerow(header)

        cont = 0
        # Para cada pacote (app) do repositório
        print(len(data["packages"]))
        for package_name in data["packages"]:
            cont += 1
            print("\n\nPackage {}: {}".format(cont, package_name))
            # if cont > 30:
                # break

            process_package(package_name, mop_methods, writer)

    print("FIM DE FESTA !!!")

# Crie um bloqueio (lock) para garantir escrita segura no arquivo CSV
csv_lock = threading.Lock()

# Número de threads que você deseja usar
num_threads = 20

# Caminho para o diretório das especificações MOP e nome do arquivo de saída
mop_specs_dir = "seu_diretorio_mop_specs"
out_file = "output.csv"

# Usando concurrent.futures para executar em várias threads
with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
    executor.map(execute, [mop_specs_dir] * num_threads, [out_file] * num_threads)

# print("Todas as threads terminaram.")

def get_last_apk_version(package):
    # pega a versao q "bate" com lastUpdated
    last_updated = package["metadata"]["lastUpdated"]
    apk_file = ""
    for version in package["versions"]:
        if last_updated == package["versions"][version]["added"]:
            apk_file = package["versions"][version]["file"]["name"][1:]
    return apk_file

@SetTimeoutDecorator(timeout=600)
def is_mop_enabled(apk_path, mop_methods):
    print("Analyzing apk ...")
    apk, _, a = AnalyzeAPK(apk_path)

    # conjunto com os nomes das classes de entrada (activity, receiver, service),
    # ja no formato do androguard (br/unb/cic/...), mas nao completo (ainda) a ponto de poder comparar se o nome da classe eh igual
    entrypoints_classes = get_entrypoints_classes(apk)

    # conjunto com os nodes do callgraph q representam os entrypoints
    # todos os metodos de cada uma das classes do entrypoints_classes
    # e com os nodes do cg que representam os metodos usados nas specs
    entrypoints, methods = get_nodes(a, entrypoints_classes, mop_methods)

    return uses_jca(a, entrypoints, methods), apk


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


def get_nodes(a: Analysis, entrypoints_classes: set, mop_methods: dict):
    entrypoints = set()
    methods = set()
    cg = a.get_call_graph()

    node: MethodAnalysis
    for node in cg.nodes:
        for e in entrypoints_classes:
            if e in str(node.get_class_name()) and str(node.get_access_flags_string()) in ["public", "protected"]:
                entrypoints.add(node)
        for clazz in mop_methods:
            if clazz in str(node.get_class_name()):
                for method in mop_methods[clazz]:
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


def get_methods_used_in_specs(specs_dir: str):
    methods_file = os.path.join(tempfile.gettempdir(), 'methods.csv')
    mop_methods = get_javamop_methods(specs_dir, methods_file)
    delete_file(methods_file)
    return mop_methods


def get_javamop_methods(specs_dir: str, methods_file: str):
    # le as specs do mop_specs_dir e salva os metodos usados em methods_file
    # depois le esse arquivo e popula um dict [CLASSE --> lista de metodos]
    # retorna esse dict
    reach_javamop_jar = os.path.join(LIB_DIR, 'reachable', 'reach-mop.jar')
    javamop_methods_cmd = Command("java", [
        '-jar',
        reach_javamop_jar,
        '-d',
        specs_dir,
        '-o',
        methods_file
    ])
    reach_javamop_result = javamop_methods_cmd.invoke(stdout=sys.stdout)
    if reach_javamop_result.code != 0:
        raise Exception("Error while finding methods in MOP specs: {0}. {1}".format(reach_javamop_result.code,
                                                                                    reach_javamop_result.stderr))
    methods = dict()
    first_line = True
    with open(methods_file, 'r') as data:
        for line in csv.reader(data):
            if first_line:
                first_line = False
                continue
            class_name = line[0].replace('.', '/')
            method_name = line[1]
            if class_name not in methods:
                methods[class_name] = set()
            methods[class_name].add(method_name)
    return methods


def delete_file(file):
    if os.path.exists(file):
        print("Deleting file: {}".format(file))
        os.remove(file)


def download_apk(apk_filename):
    base_url = "https://f-droid.org/repo/"
    apk_url = base_url + apk_filename
    print("Downloading apk: {}".format(apk_url))
    response = requests.get(apk_url)
    if "content-disposition" in response.headers:
        content_disposition = response.headers["content-disposition"]
        filename = content_disposition.split("filename=")[1]
    else:
        filename = apk_url.split("/")[-1]
    apk_path = os.path.join(tempfile.gettempdir(), filename)
    with open(apk_path, mode="wb") as file:
        file.write(response.content)
    print(f"Downloaded file {apk_path}")
    return apk_path


def get_source_code_url(metadata):
    source = ""
    if "sourceCode" in metadata:
        source = metadata["sourceCode"]
    elif "issueTracker" in metadata:
        source = metadata["issueTracker"]
    elif "webSite" in metadata:
        source = metadata["webSite"]
    return source

if __name__ == '__main__':
    base_dir = '/home/lamaral/workspace/rvsec/'
    out_file = 'final_apps_to_download.csv'
    mop_specs_dir = base_dir + 'rvsec/rvsec-agent/src/main/mop'
    
    execute(mop_specs_dir, out_file)
