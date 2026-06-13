import logging
import time
import functools
from contextlib import contextmanager
from typing import Callable, Any, Iterator


def configurar_logger() -> logging.Logger:
    """
    Configura e retorna o logger principal da biblioteca quadrosdesaude.
    
    As mensagens são formatadas de maneira padronizada para saída no terminal,
    podendo ser interceptadas e reaproveitadas por outras interfaces (como o Streamlit).

    Returns:
        logging.Logger: Instância configurada do logger principal.
    """
    logger = logging.getLogger("quadrosdesaude")

    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    return logger


logger = configurar_logger()


@contextmanager
def medir_tempo(nome_operacao: str) -> Iterator[None]:
    """
    Gerenciador de contexto para mensurar e registrar o tempo de execução de um bloco de código.

    Args:
        nome_operacao (str): Nome descritivo da operação que está sendo mensurada.

    Yields:
        None: Retorna o controle para o bloco de código interno.
    """
    logger.info(f"Iniciando operação: {nome_operacao}")
    inicio = time.perf_counter()
    try:
        yield
    finally:
        fim = time.perf_counter()
        duracao = fim - inicio
        logger.info(f"Operação concluída: {nome_operacao} | Duração: {duracao:.4f} segundos")


def logar_tempo(nome_operacao: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorador para mensurar e registrar o tempo de execução de uma função.

    Args:
        nome_operacao (str | None, opcional): Nome descritivo da operação. 
            Se não fornecido, o nome da função será utilizado. Padrão é None.

    Returns:
        Callable: Função decorada que executará o registro de tempo.
    """
    def decorador(func: Callable[..., Any]) -> Callable[..., Any]:
        nome = nome_operacao or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with medir_tempo(nome):
                return func(*args, **kwargs)
        return wrapper
    return decorador

