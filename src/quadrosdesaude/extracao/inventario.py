import ftplib
import time
import threading
import duckdb
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
from typing import Optional, Dict, List, Any
from quadrosdesaude.logger import logger, logar_tempo


class InventarioFTP:
    """
    Constrói e gerencia um catálogo local em DuckDB mapeando a árvore de diretórios
    de um servidor FTP remoto (focado no DATASUS).

    Esta classe foi arquitetada para alta performance, utilizando múltiplas threads e
    processamento de strings nativo (ASCII/Latin-1) para construir o inventário
    sem sofrer com timeouts e garantindo integridade transacional mínima.

    Attributes:
        db_path (str): Caminho local para o arquivo do banco de dados DuckDB.
        servidor_ftp (str): Hostname ou IP do servidor FTP alvo.
        max_workers (int): Número máximo de threads simultâneas para mapeamento.
        evento_parada (threading.Event): Sinalizador para interrupção segura (graceful shutdown).
        trava_db (threading.Lock): Semáforo para garantir atomicidade em inserções SQLite/DuckDB.
        fila_diretorios (Queue): Fila thread-safe de diretórios pendentes de mapeamento.
    """

    def __init__(self, db_path: str = "inventario_datasus.db", max_workers: int = 8) -> None:
        """
        Inicializa a instância do InventarioFTP.

        Args:
            db_path (str, opcional): Caminho local para o DuckDB. Padrão é "inventario_datasus.db".
            max_workers (int, opcional): Quantidade de threads para paralelismo. Padrão é 8.
        """
        self.db_path = db_path
        self.servidor_ftp = "ftp.datasus.gov.br"
        self.max_workers = max_workers
        self.evento_parada = threading.Event()
        self.trava_db = threading.Lock()
        self.fila_diretorios: Queue[str] = Queue()

    def inicializar_banco(self) -> None:
        """
        Garante a existência do banco de dados e da tabela de inventário.

        A tabela `inventory` armazena o caminho, nome, tipo e metadados de captura
        de cada artefato mapeado no FTP.
        """
        conexao = duckdb.connect(self.db_path)
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                caminho_completo TEXT PRIMARY KEY,
                nome TEXT,
                tipo TEXT,
                tamanho_bytes BIGINT,
                caminho_pai TEXT,
                segundos_mapeamento FLOAT,
                capturado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conexao.execute("PRAGMA force_checkpoint")
        conexao.close()
        logger.info(f"Banco de dados de inventário inicializado: {self.db_path}")

    def _extrair_dados_msdos(self, linha_bruta: str, caminho_pai: str) -> Optional[Dict[str, Any]]:
        """
        Realiza o processamento léxico de uma linha retornada pelo comando LIST/DIR do FTP.

        Lida primariamente com o formato MS-DOS/Windows comum em FTPs governamentais.

        Args:
            linha_bruta (str): String crua retornada pela listagem do servidor.
            caminho_pai (str): O diretório absoluto ao qual esta linha pertence.

        Returns:
            Optional[Dict[str, Any]]: Dicionário contendo os dados estruturados do arquivo/diretório.
                                      Retorna None se a linha for inválida ou não puder ser parseada.
        """
        try:
            partes = linha_bruta.split()
            if len(partes) < 4:
                return None

            indicador_tipo = partes[2]
            eh_diretorio = indicador_tipo == "<DIR>"
            nome_do_item = " ".join(partes[3:])
            tamanho = int(indicador_tipo) if not eh_diretorio else 0

            # Garantindo conversão adequada para caracteres especiais do Brasil
            nome_do_item = nome_do_item.encode("latin-1", errors="replace").decode("latin-1")
            caminho_limpo = caminho_pai if caminho_pai.endswith("/") else f"{caminho_pai}/"

            return {
                "caminho_completo": f"{caminho_limpo}{nome_do_item}",
                "nome": nome_do_item,
                "tipo": "diretorio" if eh_diretorio else "arquivo",
                "tamanho_bytes": tamanho,
                "caminho_pai": caminho_pai,
            }
        except Exception as erro_parsing:
            logger.debug(
                f"Falha ao realizar parsing da linha: '{linha_bruta}'. Detalhe: {erro_parsing}"
            )
            return None

    def _worker_mapeamento(self) -> None:
        """
        Rotina executada pelas threads do pool.

        Cada thread mantém sua própria conexão FTP isolada e consome iterativamente a
        fila de diretórios, alimentando o banco local conforme descobre novos nós.
        """
        conexao_db = None
        conexao_ftp = None

        try:
            conexao_db = duckdb.connect(self.db_path)
            conexao_ftp = ftplib.FTP(self.servidor_ftp)
            conexao_ftp.login()
            conexao_ftp.encoding = "latin-1"
            conexao_ftp.voidcmd("TYPE I")
        except Exception as erro_conexao:
            logger.error(f"Falha ao estabelecer conexão base na thread: {erro_conexao}")
            return

        while not self.evento_parada.is_set():
            try:
                caminho_alvo = self.fila_diretorios.get(timeout=2)
            except Empty:
                break

            logger.info(f"Mapeando diretório: {caminho_alvo}")
            tempo_inicio = time.time()
            sucesso_leitura = False

            while not sucesso_leitura:
                if self.evento_parada.is_set():
                    break

                try:
                    conexao_ftp.cwd(caminho_alvo)
                    listagem_bruta: List[str] = []
                    conexao_ftp.dir(listagem_bruta.append)
                    tempo_total = time.time() - tempo_inicio

                    for linha in listagem_bruta:
                        fatos = self._extrair_dados_msdos(linha, caminho_alvo)
                        if fatos:
                            with self.trava_db:
                                conexao_db.execute(
                                    """
                                    INSERT OR IGNORE INTO inventory
                                    (caminho_completo, nome, tipo, tamanho_bytes, caminho_pai, segundos_mapeamento)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                    [
                                        fatos["caminho_completo"],
                                        fatos["nome"],
                                        fatos["tipo"],
                                        fatos["tamanho_bytes"],
                                        fatos["caminho_pai"],
                                        tempo_total,
                                    ],
                                )

                            if fatos["tipo"] == "diretorio":
                                self.fila_diretorios.put(fatos["caminho_completo"])

                    sucesso_leitura = True

                except Exception as erro_ftp:
                    mensagem_erro = str(erro_ftp)
                    if "550" in mensagem_erro:
                        logger.warning(
                            f"Acesso negado ou diretório vazio no servidor remoto: {caminho_alvo}"
                        )
                        sucesso_leitura = True
                    else:
                        logger.error(
                            f"Erro transiente em {caminho_alvo} ({mensagem_erro}). Forçando reconexão..."
                        )
                        try:
                            conexao_ftp.quit()
                            time.sleep(1)
                            conexao_ftp = ftplib.FTP(self.servidor_ftp)
                            conexao_ftp.login()
                            conexao_ftp.encoding = "latin-1"
                            conexao_ftp.voidcmd("TYPE I")
                        except Exception:
                            pass

            self.fila_diretorios.task_done()

            if self.fila_diretorios.qsize() % 50 == 0:
                with self.trava_db:
                    conexao_db.execute("PRAGMA force_checkpoint")

        if conexao_db:
            conexao_db.execute("PRAGMA force_checkpoint")
            conexao_db.close()

        if conexao_ftp:
            try:
                conexao_ftp.quit()
            except Exception:
                pass

    @logar_tempo("Atualização Completa do Inventário FTP")
    def atualizar_inventario(self, diretorio_raiz: str = "/dissemin/publicos") -> None:
        """
        Orquestra a atualização do inventário de forma assíncrona.

        Dispara múltiplas threads que recursivamente listam todos os arquivos
        e diretórios a partir de `diretorio_raiz`.

        Args:
            diretorio_raiz (str, opcional): Caminho FTP base para o início do mapeamento.
                                            Padrão é "/dissemin/publicos".
        """
        logger.info(f"Iniciando rotina de mapeamento recursivo em: {diretorio_raiz}")
        self.inicializar_banco()
        self.fila_diretorios.put(diretorio_raiz)
        self.evento_parada.clear()

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                for _ in range(self.max_workers):
                    executor.submit(self._worker_mapeamento)

                while not self.fila_diretorios.empty():
                    time.sleep(2)
                    if self.evento_parada.is_set():
                        break

        except KeyboardInterrupt:
            logger.warning(
                "Interrupção externa detectada. Finalizando pool de threads de forma segura..."
            )
            self.evento_parada.set()
        finally:
            self.evento_parada.set()
            time.sleep(2)

        try:
            con_resumo = duckdb.connect(self.db_path)
            resumo = con_resumo.execute("""
                SELECT COUNT(*), COALESCE(SUM(tamanho_bytes), 0) / 1024 / 1024 / 1024
                FROM inventory
            """).fetchone()

            if resumo:
                logger.info(f"Consolidação de Inventário: {resumo[0]} entidades computadas.")
                logger.info(f"Volume de Dados Mapeado: {resumo[1]:.4f} GB")

            con_resumo.close()
        except Exception as erro_resumo:
            logger.error(f"Falha ao gerar o resumo final do inventário: {erro_resumo}")

    def listar_todos_arquivos(self, pasta_raiz: str) -> List[Dict[str, Any]]:
        """
        Consulta o banco local e retorna todos os artefatos classificados como 'arquivo'
        aninhados dentro da pasta raiz especificada.

        Args:
            pasta_raiz (str): Diretório base utilizado na consulta LIKE do banco.

        Returns:
            List[Dict[str, Any]]: Lista de dicionários, cada qual representando um arquivo mapeado,
                                  ordenada hierarquicamente.
        """
        try:
            con = duckdb.connect(self.db_path)
            padrao = f"{pasta_raiz}%"
            resultado = con.execute(
                """
                SELECT caminho_completo, nome, tamanho_bytes, caminho_pai
                FROM inventory
                WHERE tipo = 'arquivo' AND caminho_completo LIKE ?
                ORDER BY caminho_pai ASC, nome ASC
            """,
                [padrao],
            ).fetchall()
            con.close()

            return [
                {
                    "caminho_completo": row[0],
                    "nome": row[1],
                    "tamanho_bytes": row[2],
                    "caminho_pai": row[3],
                }
                for row in resultado
            ]
        except Exception as erro_db:
            logger.error(f"Falha na consulta ao banco local para a pasta {pasta_raiz}: {erro_db}")
            return []
