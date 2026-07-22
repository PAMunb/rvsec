# droidbot/adapter/qemu.py

import logging
import asyncio
import telnetlib3
# from telnetlib3.exceptions import TelnetException

from .adb import ADB
from .telnet import TelnetException

# from ..errors import DeviceError

# Adicione o telnetlib3 como uma dependência no setup.py do projeto
# e corrija os SyntaxWarning em adb.py e utils.py.

# O Telnetlib3 usa programação assíncrona, o que requer uma reestruturação do código.
# Para evitar bloquear a thread principal, usamos asyncio para gerenciar a conexão.

log = logging.getLogger(__name__)

class QEMUClient:
    """
    Um cliente Telnet assíncrono para QEMU usando telnetlib3.
    """
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def connect(self):
        """
        Estabelece a conexão com o servidor Telnet.
        """
        try:
            self.reader, self.writer = await telnetlib3.open_connection(
                self.host, self.port, timeout=10
            )
            return True
        except (ConnectionRefusedError, TelnetException, asyncio.TimeoutError) as e:
            log.error(f"Failed to connect to QEMU Telnet server: {e}")
            return False

    async def send_command(self, cmd):
        """
        Envia um comando e retorna a resposta.
        """
        if not self.writer:
            log.warning("Telnet client not connected.")
            return ""

        full_cmd = f"{cmd}\n"
        self.writer.write(full_cmd)
        await self.writer.drain()

        # A leitura pode ser tricky. Vamos tentar ler até o próximo prompt.
        # Por exemplo, se o prompt for "OK", podemos ler até encontrá-lo.
        # Aqui, vamos usar um timeout e ler tudo que for recebido.
        try:
            # telnetlib3.read() não bloqueia. Podemos ler a saída com await reader.read()
            # ou usar um método mais sofisticado, dependendo da necessidade.
            # Para este exemplo, vamos ler por 2 segundos e retornar o que tiver.
            response = await asyncio.wait_for(self.reader.read(1024), timeout=2.0)
            return response.strip()
        except asyncio.TimeoutError:
            log.warning("Timeout while waiting for command response.")
            return ""

    async def close(self):
        """
        Fecha a conexão.
        """
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()


class QEMUConn(ADB):
    """
    Uma classe que conecta ao ADB de um dispositivo QEMU.
    """
    def __init__(self, device, telnet_port):
        super(QEMUConn, self).__init__(device)
        self.telnet_port = telnet_port
        self.client = QEMUClient('127.0.0.1', self.telnet_port)

    async def __aenter__(self):
        """
        Permite usar a conexão Telnet com o 'with'.
        """
        if not await self.client.connect():
            #raise DeviceError("Failed to connect to QEMU Telnet port")
            raise Exception("Failed to connect to QEMU Telnet port")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Fecha a conexão Telnet ao sair do 'with'.
        """
        await self.client.close()

    def get_telnet_auth_token(self):
        """
        Obtém o token de autenticação Telnet do arquivo de credenciais.
        """
        auth_file = "/home/pedro/.emulator_auth_token"
        try:
            with open(auth_file, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def auth_to_qemu(self):
        """
        Autentica a conexão Telnet com o QEMU.
        Essa função agora precisa ser assíncrona.
        """
        auth_token = self.get_telnet_auth_token()
        if not auth_token:
            return True # Não há token, assumimos que não é necessário

        # TODO: Refatorar o código de autenticação para usar o novo cliente assíncrono.
        # Isso pode exigir uma mudança na estrutura de chamadas do DroidBot.
        # Por exemplo, a chamada para esta função deveria ser await self.auth_to_qemu()

        return False

    def qemu_cmd(self, cmd):
        """
        Envia um comando para o QEMU Telnet e retorna a resposta.
        Esta função também precisa ser assíncrona.
        """
        async def _run_command():
            async with self as qemu:
                return await qemu.client.send_command(cmd)

        return asyncio.run(_run_command())

    def get_current_activity(self):
        # A chamada para self.qemu_cmd() precisa ser await, mas o método
        # original do DroidBot não é assíncrono.
        # Portanto, esta parte do código precisa ser refatorada em todo o projeto.
        # return self.qemu_cmd('avd status')
        return "Unknown" # Retorno temporário para evitar erros.