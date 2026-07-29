import os
import itertools
import gc
import struct
import polars as pl
import pyarrow.parquet as pq
from dbfread import DBF
from typing import Iterator, Dict, Any, List, Optional
from quadrosdesaude import descomprimir_dbc
from .parser import StringFieldParser
from quadrosdesaude.logger import logger, logar_tempo


def harmonizar_registos_em_fluxo(
    iterator_dbf: Iterator[Dict[str, Any]], schema_mestre: List[str]
) -> Iterator[Dict[str, Any]]:
    """
    Processa um fluxo de registros DBF garantindo que cada registro possua todas as colunas.

    Este gerador recebe registros mapeados em dicionários. Devido a peculiaridades dos
    dados do DATASUS, algumas colunas podem vir ausentes. O algoritmo harmoniza o schema
    criando um template com chaves nulas (strings vazias) baseadas no `schema_mestre`,
    preservando os valores originais quando presentes.

    Args:
        iterator_dbf (Iterator[Dict[str, Any]]): Iterador gerando dicionários de registros.
        schema_mestre (List[str]): Lista completa das colunas esperadas.

    Yields:
        Dict[str, Any]: Um dicionário estruturado garantindo compatibilidade com o schema esperado.
    """
    template = {coluna: "" for coluna in schema_mestre}
    for registo in iterator_dbf:
        yield {**template, **registo}


@logar_tempo("Descompressão DBC para DBF")
def dbc2dbf(caminho_dbc: str, caminho_dbf: str) -> bool:
    """
    Descomprime um arquivo .dbc binário em um formato padrão .dbf.

    Encapsula a chamada nativa em C (`descomprimir_dbc`) para realizar a extração
    desenvolvida especificamente para a arquitetura do PKWare do DATASUS.

    Args:
        caminho_dbc (str): Caminho absoluto de origem do arquivo .dbc.
        caminho_dbf (str): Caminho absoluto de destino para o arquivo .dbf.

    Returns:
        bool: Retorna True em caso de sucesso da descompressão, False em caso de falha silenciosa.
    """
    try:
        descomprimir_dbc(caminho_dbc, caminho_dbf)
        return True
    except Exception:
        return False


@logar_tempo("Conversão DBF para Parquet")
def dbf2parquet(
    caminho_dbf: str,
    destino_parquet: Optional[str] = None,
    tamanho_lote: int = 100000,
    compressao: str = "zstd",
    engine: str = "fast",
) -> bool:
    """
    Converte um arquivo .dbf para o formato Parquet otimizado para Data Lakes.

    A conversão opera em processamento de lotes (chunks) utilizando `itertools.islice` (engine='dbfread')
    ou struct unpacking direto em C + Polars (engine='fast'), limitando o consumo de RAM.
    Escreve apensos sucessivos via PyArrow ParquetWriter.

    Args:
        caminho_dbf (str): Caminho absoluto do arquivo .dbf de origem.
        destino_parquet (str | None, opcional): Caminho de saída do parquet. Se None,
            gera o nome no diretório atual. Padrão é None.
        tamanho_lote (int, opcional): Volume de linhas lidas em memória por ciclo. Padrão é 100000.
        compressao (str, opcional): Algoritmo de compressão do parquet (ex: 'zstd', 'snappy'). Padrão 'zstd'.
        engine (str, opcional): Motor de parsing de DBF a utilizar ('fast' ou 'dbfread'). Padrão 'fast'.

    Returns:
        bool: True caso a paridade de linhas entre DBF e Parquet seja atingida sem erros. False caso contrário.
    """
    if not destino_parquet:
        nome_base = os.path.basename(caminho_dbf)
        destino_parquet = f"{nome_base}.parquet"

    writer = None
    total_linhas_processadas = 0

    lote_de_registros = None
    df_lote = None
    tabela_arrow = None
    schema_mestre = None

    try:
        if engine == "fast":
            with open(caminho_dbf, 'rb') as f:
                header = f.read(32)
                num_records = struct.unpack('<I', header[4:8])[0]
                header_len = struct.unpack('<H', header[8:10])[0]
                record_len = struct.unpack('<H', header[10:12])[0]
                
                fields = []
                while f.tell() < header_len - 1:
                    field_data = f.read(32)
                    if field_data[0] == 0x0D:
                        break
                    name = field_data[:11].split(b'\x00')[0].decode('latin1')
                    length = field_data[16]
                    fields.append((name, length))
                    
                f.seek(header_len)
                
                fmt = '<x' + ''.join(f'{length}s' for name, length in fields)
                struct_obj = struct.Struct(fmt)
                schema_mestre = [name for name, length in fields]
                
                chunk_bytes_size = tamanho_lote * record_len
                
                while True:
                    raw_data = f.read(chunk_bytes_size)
                    if not raw_data:
                        break
                    registros_no_chunk = len(raw_data) // record_len
                    bytes_validos = registros_no_chunk * record_len
                    
                    chunk_tuples_bin = struct_obj.iter_unpack(raw_data[:bytes_validos])
                    
                    decoded_tuples = [
                        tuple(val.decode('latin1').strip() for val in row)
                        for row in chunk_tuples_bin
                    ]
                    
                    df_lote = pl.DataFrame(decoded_tuples, schema=schema_mestre, orient="row")
                    tabela_arrow = df_lote.to_arrow()
                    
                    if writer is None:
                        writer = pq.ParquetWriter(
                            destino_parquet, tabela_arrow.schema, compression=compressao
                        )
                    
                    writer.write_table(tabela_arrow)
                    total_linhas_processadas += registros_no_chunk
                    
                    lote_de_registros = df_lote = tabela_arrow = None
                    gc.collect()
        else:
            tabela_dbf = DBF(caminho_dbf, parserclass=StringFieldParser)
            schema_mestre = tabela_dbf.field_names

            gerador_harmonizado = harmonizar_registos_em_fluxo(iter(tabela_dbf), schema_mestre)

            for lote_de_registros in iter(
                lambda: list(itertools.islice(gerador_harmonizado, tamanho_lote)), []
            ):
                df_lote = pl.DataFrame(
                    lote_de_registros, schema_overrides={col: pl.Utf8 for col in schema_mestre}
                )
                tabela_arrow = df_lote.to_arrow()

                if writer is None:
                    writer = pq.ParquetWriter(
                        destino_parquet, tabela_arrow.schema, compression=compressao
                    )

                writer.write_table(tabela_arrow)
                total_linhas_processadas += len(df_lote)

                lote_de_registros = df_lote = tabela_arrow = None
                gc.collect()

        if writer:
            writer.close()

        if total_linhas_processadas == 0:
            return True

        meta_parquet = pq.ParquetFile(destino_parquet).metadata
        linhas_no_parquet = meta_parquet.num_rows
        colunas_parquet = set(meta_parquet.schema.names)
        colunas_dbf = set(schema_mestre)

        if not colunas_dbf.issubset(colunas_parquet):
            faltantes = colunas_dbf - colunas_parquet
            logger.error(
                f"Inconsistência estrutural detectada em {caminho_dbf}. Colunas omitidas no Parquet: {faltantes}"
            )
            return False

        if total_linhas_processadas == linhas_no_parquet:
            return True

        logger.error(
            f"Divergência volumétrica em {caminho_dbf}. "
            f"Processadas: {total_linhas_processadas} | Salvas: {linhas_no_parquet}."
        )
        return False
    except MemoryError as erro_memoria:
        logger.error(f"Esgotamento de memória (OOM) ao converter {caminho_dbf}: {erro_memoria}")
        return False
    except FileNotFoundError as erro_arquivo:
        logger.error(f"Arquivo de origem DBF inacessível ({caminho_dbf}): {erro_arquivo}")
        return False
    except Exception as erro_critico:
        logger.error(
            f"Exceção crítica durante a conversão do arquivo {caminho_dbf}: {erro_critico}"
        )
        return False
    finally:
        lote_de_registros = df_lote = tabela_arrow = None
        if writer:
            try:
                writer.close()
            except Exception:
                pass
        gc.collect()
