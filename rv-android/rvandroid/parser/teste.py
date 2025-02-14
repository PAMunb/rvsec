from droidbot.input_event import InputEvent

# from ...droidbot.input_event import InputEvent  

# import os
# # Obtém o valor atual de PYTHONPATH (se existir)
# pythonpath = os.environ.get('PYTHONPATH', '')

# # Adiciona o novo diretório ao PYTHONPATH
# novo_diretorio = '/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android'
# os.environ['PYTHONPATH'] = f"{novo_diretorio}:{pythonpath}" if pythonpath else novo_diretorio

# import aaa.meu_teste as x

class ItemAction:
    def __init__(self, id: int, text: str, event: InputEvent):
        self.id = id
        self.text = text
        self.event = event

# if __name__ == "main":
    # import os
    # # Obtém o valor atual de PYTHONPATH (se existir)
    # pythonpath = os.environ.get('PYTHONPATH', '')

    # # Adiciona o novo diretório ao PYTHONPATH
    # novo_diretorio = '/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android'
    # os.environ['PYTHONPATH'] = f"{novo_diretorio}:{pythonpath}" if pythonpath else novo_diretorio

print(ItemAction(0,"",None))  
# print(x.hello())      


# export PYTHONPATH=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android