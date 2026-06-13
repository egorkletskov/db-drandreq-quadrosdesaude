import os
import sys
import subprocess
import socket
from contextlib import closing
from quadrosdesaude.logger import logger


def encontrar_porta_livre(porta_inicial: int = 8501) -> int:
    """
    Procura iterativamente por uma porta TCP local disponível.

    Args:
        porta_inicial (int): A porta pela qual a varredura deve começar. Padrão é 8501.

    Returns:
        int: O número da primeira porta disponível encontrada.

    Raises:
        RuntimeError: Se não houver portas disponíveis até o limite estipulado (9000).
    """
    porta = porta_inicial
    while porta < 9000:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            try:
                sock.bind(('localhost', porta))
                return porta
            except OSError:
                porta += 1
    raise RuntimeError("Recurso não disponível: Não foi possível identificar uma porta TCP livre.")


def main() -> None:
    """
    Ponto de entrada do executável da interface do usuário.
    Inicializa o serviço do Streamlit de forma isolada no ambiente.
    """
    try:
        porta = encontrar_porta_livre()
        logger.info(f"Inicializando serviço de interface Quadros de Saúde (Porta: {porta}).")

        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_home = os.path.join(diretorio_atual, "1_Home.py")

        if not os.path.exists(caminho_home):
            raise FileNotFoundError(f"Módulo base da interface não localizado em: {caminho_home}")

        subprocess.run([
            sys.executable, "-m", "streamlit", "run", caminho_home,
            "--server.port", str(porta),
            "--server.headless", "true"
        ], check=True)
        
    except Exception as erro_execucao:
        logger.error(f"Falha severa na inicialização da camada de visualização: {erro_execucao}")
        sys.exit(1)


if __name__ == "__main__":
    main()
