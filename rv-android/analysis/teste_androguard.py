from androguard.core.bytecodes.dvm import DalvikVMFormat, DalvikCode
from androguard.misc import AnalyzeAPK
from androguard.core.analysis.analysis import Analysis, MethodAnalysis, ClassAnalysis

from app import App

def execute(apk_path: str):
    app = App(apk)
    package = app.package_name #.replace(".", "/")

    print(">>> {} ::: {}".format(app.name, package))
    #vm = DalvikVMFormat(app.apk.get_dex())

    a = Analysis()
    for d in app.apk.get_all_dex():
        a.add(DalvikVMFormat(d))

    c: ClassAnalysis
    for c in a.get_classes():
        clazz = str(c.name).replace("/", ".")[1:-1]
        if package in clazz and not c.external and not is_R(clazz):
            # TODO excluir R tbm
            print(clazz)
            m: MethodAnalysis
            for m in c.get_methods():
                print("   - {} ::: {} ::: {}".format(m.name, m.descriptor, m.access))

                args, ret = m.get_descriptor()[1:].split(")")
                print("ARGS::: {}".format(args))
                # if len(args) > 0:
                #     import androguard.decompiler.dad.util as util
                #     print(">>> {}".format(util.get_type(args[0])))
                code: DalvikCode = m.code
                if code:
                    # We patch the descriptor here and add the registers, if code is available
                    args = args.split(" ")

                    reg_len = code.get_registers_size()
                    nb_args = len(args)

                    start_reg = reg_len - nb_args
                    args = ["{} v{}".format(a, start_reg + i) for i, a in enumerate(args)]

                print("METHOD {} {} {} ({}){}".format(
                    m.method.get_class_name(),
                    m.method.get_access_flags_string(),
                    m.method.get_name(),
                    ", ".join(args), ret))


    # analysis: Analysis
    # app, _, analysis = AnalyzeAPK(apk_path)
    #
    # print("xxx")Analysis(Analysis)
    #
    # print("INTERNAL CLASSES .................")
    # c: ClassAnalysis
    # for c in analysis.get_internal_classes():
    #     print(c.name)
    #     x = c.get_class()
    #     print(x)

    print("FIM DE FESTA !!!")

def is_R(clazz: str):
    idx = clazz.rfind(".")
    name = clazz[idx + 1:]
    print(name)
    if name == "R" or name.startswith("R$"):
        return True
    return False


def parse_method(m: MethodAnalysis):
    pass


if __name__ == '__main__':
    apk = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk"
    execute(apk)

    # print(is_R("Lbr/unb/cic/cryptoapp/R;"))
    # print(is_R("Lbr/unb/cic/cryptoapp/R$drawable;"))
    # print(is_R("Lbr/unb/cic/cryptoapp/MainActivity;"))
    # print(is_R("Lbr/unb/cic/cryptoapp/RainActivity;"))

