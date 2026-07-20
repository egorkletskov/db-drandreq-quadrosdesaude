import os
import shutil
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from typing import Literal, Tuple, Union
from .conversor import dbc2dbf, dbf2parquet
from quadrosdesaude.logger import logger, logar_tempo


@logar_tempo("Pipeline Completo DBC para Parquet")
def dbc2parquet(
    caminho_dbc: str,
    destino_parquet: str,
    pasta_temp_dbf: str = "./temp_dbf",
    pasta_temp_parquet: str = "./temp_parquet",
    operacao: Literal["lote", "unico"] = "unico",
    tamanho_lote: int = 100000,
    compressao: str = "zstd",
) -> Union[Tuple[str, bool, str], bool]:
    """
    Processa um único arquivo .dbc efetuando sua conversão final para Parquet de modo atômico.

    A execução do pipeline consiste em:
    1. Descomprimir o binário .dbc para .dbf numa área de alocação temporária.
    2. Converter de .dbf para .parquet gerenciando processamento em lotes limitados.
    3. Validar consistência estrutural e transferir o arquivo final para seu destino persistente.
    4. Garantir a sanitização dos artefatos intermediários ao fim do ciclo.

    Args:
        caminho_dbc (str): Caminho absoluto de origem.
        destino_parquet (str): Diretório final de consolidação do arquivo parquet.
        pasta_temp_dbf (str, opcional): Área de staging para DBFs. Padrão './temp_dbf'.
        pasta_temp_parquet (str, opcional): Área de staging para Parquets. Padrão './temp_parquet'.
        operacao (Literal['lote', 'unico'], opcional): Assinatura de retorno esperada. Padrão 'unico'.
        tamanho_lote (int, opcional): Buffer de linhas por operação I/O na conversão. Padrão 100000.
        compressao (str, opcional): Algoritmo de compressão do Parquet. Padrão 'zstd'.

    Returns:
        Union[Tuple[str, bool, str], bool]:
            - Se `operacao='lote'`: Retorna a tupla (nome_base, sucesso, mensagem).
            - Se `operacao='unico'`: Retorna status booleano (True/False).
    """
    os.makedirs(pasta_temp_dbf, exist_ok=True)
    os.makedirs(pasta_temp_parquet, exist_ok=True)

    nome_base = os.path.basename(caminho_dbc)
    nome_sem_ext = Path(caminho_dbc).stem

    caminho_dbf_temp = os.path.join(pasta_temp_dbf, f"{nome_sem_ext}.dbf")
    caminho_parquet_temp = os.path.join(pasta_temp_parquet, f"{nome_sem_ext}.parquet")
    caminho_parquet_final = os.path.join(destino_parquet, f"{nome_sem_ext}.parquet")

    try:
        dbc2dbf(caminho_dbc, caminho_dbf_temp)

        if dbf2parquet(
            caminho_dbf_temp, caminho_parquet_temp, tamanho_lote=tamanho_lote, compressao=compressao
        ):
            try:
                shutil.move(caminho_parquet_temp, caminho_parquet_final)
            except Exception as erro_movimentacao:
                raise Exception(
                    f"Falha ao promover o arquivo {caminho_parquet_temp} ao diretório final: {erro_movimentacao}"
                ) from erro_movimentacao

            if operacao == "lote":
                return (nome_base, True, f"Processamento bem-sucedido: {caminho_parquet_final}")
            return True

        else:
            if operacao == "lote":
                return (
                    nome_base,
                    False,
                    f"Falha de integridade na conversão do arquivo: {caminho_dbf_temp}",
                )
            return False

    except Exception as erro_geral:
        logger.error(f"Exceção durante a esteira de conversão de {nome_base}: {erro_geral}")
        if operacao == "lote":
            return (nome_base, False, f"Falha transiente na conversão de: {caminho_dbf_temp}")
        return False
    finally:
        if os.path.exists(caminho_dbf_temp):
            os.remove(caminho_dbf_temp)
        if os.path.exists(caminho_parquet_temp):
            os.remove(caminho_parquet_temp)


def orquestrador_single(
    pasta_origem_dbc: str,
    pasta_destino_parquet: str,
    pasta_temp_dbf: str = "./temp_dbf",
    pasta_temp_parquet: str = "./temp_parquet",
    tamanho_lote: int = 100000,
    compressao: str = "zstd",
) -> None:
    """
    Controlador para execução linear e atômica de conversões em massa (DBC para Parquet).

    Apropriado para integrações determinísticas como tarefas de ETL orquestradas por
    ferramentas nativas de Data Engineering (e.g., Airflow, Dagster), onde concorrência
    não é aconselhável no nível de script.

    Args:
        pasta_origem_dbc (str): Diretório base contendo os arquivos binários nativos.
        pasta_destino_parquet (str): Local consolidado de saída em Data Lake estruturado.
        pasta_temp_dbf (str, opcional): Caminho de staging. Padrão './temp_dbf'.
        pasta_temp_parquet (str, opcional): Caminho de staging. Padrão './temp_parquet'.
        tamanho_lote (int, opcional): Densidade dos lotes em memória. Padrão 100000.
        compressao (str, opcional): Algoritmo do parquet resultante. Padrão 'zstd'.
    """
    for pasta in [pasta_temp_dbf, pasta_temp_parquet]:
        if os.path.exists(pasta):
            shutil.rmtree(pasta)
        os.makedirs(pasta, exist_ok=True)

    arquivos_dbc = list(Path(pasta_origem_dbc).glob("*.[dD][bB][cC]"))
    if not arquivos_dbc:
        logger.warning("Nenhum arquivo .dbc foi identificado na origem declarada.")
        return

    sucessos, falhas = 0, 0
    start_time_total = time.perf_counter()

    progress_bar = tqdm(total=len(arquivos_dbc), desc="Processamento Unificado")

    for caminho_dbc in arquivos_dbc:
        try:
            nome_base, sucesso, mensagem = dbc2parquet(
                caminho_dbc=str(caminho_dbc),
                destino_parquet=pasta_destino_parquet,
                pasta_temp_dbf=pasta_temp_dbf,
                pasta_temp_parquet=pasta_temp_parquet,
                operacao="lote",
                tamanho_lote=tamanho_lote,
                compressao=compressao,
            )
            if sucesso:
                sucessos += 1
            else:
                logger.error(f"Arquivo comprometido: {nome_base} - Motivo: {mensagem}")
                falhas += 1
        except Exception as erro:
            logger.error(f"Falha de sistema ao lidar com o arquivo {caminho_dbc.name}: {erro}")
            falhas += 1
        finally:
            progress_bar.update(1)

    progress_bar.close()

    duration_total = time.perf_counter() - start_time_total
    logger.info(f"Ciclo operacional finalizado. Duração: {duration_total:.2f} segundos.")
    logger.info(f"Arquivos processados com sucesso: {sucessos}")
    logger.info(f"Arquivos com falha ou rejeitados: {falhas}")


def orquestrador_multi(
    pasta_origem_dbc: str,
    pasta_destino_parquet: str,
    pasta_temp_dbf: str = "./temp_dbf",
    pasta_temp_parquet: str = "./temp_parquet",
    max_workers: int = 2,
    tamanho_lote: int = 100000,
    compressao: str = "zstd",
) -> None:
    """
    Controlador para execução paralela da malha de conversão via instâncias multithread.

    Direcionado para maximização de throughput em máquinas virtuais com múltiplos
    núcleos, processando diferentes arquivos em simultâneo através de um ThreadPoolExecutor.

    Args:
        pasta_origem_dbc (str): Diretório base contendo os arquivos.
        pasta_destino_parquet (str): Diretório base de destino.
        pasta_temp_dbf (str, opcional): Local de alocação temporária (staging).
        pasta_temp_parquet (str, opcional): Local de alocação temporária.
        max_workers (int, opcional): Paralelismo máximo do worker pool. Padrão 2.
        tamanho_lote (int, opcional): Memória particionada por tarefa. Padrão 100000.
        compressao (str, opcional): Algoritmo adotado. Padrão 'zstd'.
    """
    for pasta in [pasta_temp_dbf, pasta_temp_parquet]:
        if os.path.exists(pasta):
            shutil.rmtree(pasta)
        os.makedirs(pasta, exist_ok=True)

    arquivos_dbc = list(Path(pasta_origem_dbc).glob("*.[dD][bB][cC]"))
    if not arquivos_dbc:
        logger.warning("Nenhum arquivo .dbc válido foi detectado no volume de entrada.")
        return

    sucessos, falhas = 0, 0
    start_time_total = time.perf_counter()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        progress_bar = tqdm(total=len(arquivos_dbc), desc="Processamento em Lote Concorrente")
        futuros = []

        for caminho_dbc in arquivos_dbc:
            futuros.append(
                executor.submit(
                    dbc2parquet,
                    str(caminho_dbc),
                    pasta_destino_parquet,
                    pasta_temp_dbf,
                    pasta_temp_parquet,
                    "lote",
                    tamanho_lote,
                    compressao,
                )
            )

        try:
            for futuro in as_completed(futuros):
                nome_base, sucesso, mensagem = futuro.result()
                if sucesso:
                    sucessos += 1
                else:
                    logger.error(
                        f"Falha detectada em arquivo gerido assincronamente: {nome_base} - {mensagem}"
                    )
                    falhas += 1
                progress_bar.update(1)
            progress_bar.close()

        except KeyboardInterrupt:
            logger.warning(
                "Solicitação manual de interrupção submetida. Desalocando recursos e cancelando a fila..."
            )
            executor.shutdown(wait=False, cancel_futures=True)
            return

        except Exception as erro_execucao:
            logger.error(
                f"Inconsistência identificada no nível de orquestração (Pool): {erro_execucao}"
            )
            executor.shutdown(wait=False, cancel_futures=True)
            return

    duration_total = time.perf_counter() - start_time_total
    logger.info(f"Ciclo de lote finalizado em {duration_total:.2f} segundos.")
    logger.info(f"Registros processados com sucesso: {sucessos}")
    logger.info(f"Registros apontados com anomalia: {falhas}")


def orquestrador(
    pasta_origem_dbc: str,
    pasta_destino_parquet: str,
    pasta_temp_dbf: str = "./temp_dbf",
    pasta_temp_parquet: str = "./temp_parquet",
    max_workers: int = 1,
    tamanho_lote: int = 100000,
    compressao: str = "zstd",
) -> None:
    """
    Interface de orquestração mestre para o pipeline de processamento do projeto.

    Atua como proxy de roteamento, destinando o tráfego de dados para execuções
    seriais ou paralelas dependendo da carga de `max_workers`.
    """
    if max_workers > 1:
        orquestrador_multi(
            pasta_origem_dbc=pasta_origem_dbc,
            pasta_destino_parquet=pasta_destino_parquet,
            pasta_temp_dbf=pasta_temp_dbf,
            pasta_temp_parquet=pasta_temp_parquet,
            max_workers=max_workers,
            tamanho_lote=tamanho_lote,
            compressao=compressao,
        )
    else:
        orquestrador_single(
            pasta_origem_dbc=pasta_origem_dbc,
            pasta_destino_parquet=pasta_destino_parquet,
            pasta_temp_dbf=pasta_temp_dbf,
            pasta_temp_parquet=pasta_temp_parquet,
            tamanho_lote=tamanho_lote,
            compressao=compressao,
        )
