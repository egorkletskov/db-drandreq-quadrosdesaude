import os
import glob
import shutil
from typing import Optional
from quadrosdesaude.logger import logger


def formatar_tamanho(num_bytes: int | None) -> str:
    """
    Converte um número de bytes para uma string formatada legível por humanos.

    Utiliza potências de 1024 para converter bytes em Kilobytes (KB), Megabytes (MB),
    Gigabytes (GB) ou Terabytes (TB), arredondando o resultado para duas casas decimais.

    Args:
        num_bytes (int | None): O número de bytes a ser formatado. Pode ser nulo.

    Returns:
        str: Uma string representando o tamanho formatado (ex: "1.23 MB", "500.00 KB").
             Retorna "0.00 B" se a entrada for None ou inválida.
    """
    if num_bytes is None:
        return "0.00 B"

    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}

    while num_bytes >= power and n < len(power_labels):
        num_bytes /= power
        n += 1

    return f"{num_bytes:.2f} {power_labels[n]}B"


def medir_tamanho_pasta(caminho_pasta: str) -> Optional[str]:
    """
    Calcula e retorna o tamanho total de todos os arquivos dentro de um diretório e subdiretórios.

    Percorre recursivamente a árvore de diretórios a partir do caminho fornecido,
    soma o tamanho de todos os arquivos encontrados e retorna o tamanho total formatado.
    Arquivos inacessíveis por questões de permissão serão registrados via logger.warning.

    Args:
        caminho_pasta (str): O caminho absoluto ou relativo para o diretório alvo.

    Returns:
        Optional[str]: Uma string com o tamanho total formatado (ex: "1.50 GB").
                       Retorna None em caso de falhas severas, embora o atual comportamento 
                       retorne o somatório do que pôde ser lido.
    """
    logger.info(f"Calculando o tamanho do diretório: {caminho_pasta}")
    tamanho_total_bytes = 0
    
    for dirpath, dirnames, filenames in os.walk(caminho_pasta):
        for f in filenames:
            caminho_arquivo = os.path.join(dirpath, f)
            try:
                tamanho_total_bytes += os.path.getsize(caminho_arquivo)
            except OSError as erro:
                logger.warning(f"Falha ao acessar o arquivo {caminho_arquivo}: {erro}")

    tamanho_formatado = formatar_tamanho(tamanho_total_bytes)
    logger.info(f"Tamanho total apurado para o diretório: {tamanho_formatado}")
    
    return tamanho_formatado

