"""
Script de exemplo para desenvolvimento e testes rápidos da biblioteca quadrosdesaude.
Sinta-se à vontade para modificar este arquivo para experimentar com o código local.
"""

import os
from quadrosdesaude import medir_tempo, orquestrador_single, medir_tamanho_pasta, logger

# Configurando pasta de testes locais
PASTA_ORIGEM = os.path.abspath("./downloads")
PASTA_DESTINO = os.path.abspath("./ducklake_dev")
PASTA_TEMP_DBF = os.path.abspath("./temp_dbf")
PASTA_TEMP_PARQUET = os.path.abspath("./temp_parquet")


def main():
    logger.info("🦆 Iniciando script de testes de desenvolvimento...")

    # Exemplo simples de orquestração sequencial
    if os.path.exists(PASTA_ORIGEM):
        logger.info(f"Pasta de origem '{PASTA_ORIGEM}' encontrada.")

        with medir_tempo("Execução Completa de Teste (DBC -> Parquet)"):
            orquestrador_single(
                pasta_origem_dbc=PASTA_ORIGEM,
                pasta_destino_parquet=PASTA_DESTINO,
                pasta_temp_dbf=PASTA_TEMP_DBF,
                pasta_temp_parquet=PASTA_TEMP_PARQUET,
                tamanho_lote=50000,
            )

        medir_tamanho_pasta(PASTA_DESTINO)
    else:
        logger.warning(
            f"Pasta de origem '{PASTA_ORIGEM}' não encontrada. "
            "Baixe alguns arquivos usando a UI ou FTP Downloader para testar."
        )


if __name__ == "__main__":
    main()
