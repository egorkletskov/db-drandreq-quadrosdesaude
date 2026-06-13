import os
import shutil
from ftplib import FTP, error_perm
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import List, Optional
from quadrosdesaude.logger import logger, logar_tempo


class FTPDownloader:
    """
    Facilita o download de arquivos de servidores FTP, com foco na infraestrutura do DATASUS.

    Esta classe encapsula a lógica para listar arquivos, baixar artefatos individuais
    e executar downloads massivos em lote de forma concorrente. Inclui suporte a
    barras de progresso e tratamento básico de erros transientes de rede.

    Attributes:
        ftp_host (str): Endereço IP ou hostname do servidor FTP.
        evento_parada (threading.Event): Sinalizador para interrupção segura dos downloads em andamento.
    """

    def __init__(self, ftp_host: str = "ftp.datasus.gov.br") -> None:
        """
        Inicializa a instância do FTPDownloader.

        Args:
            ftp_host (str, opcional): Endereço do servidor FTP. Padrão é "ftp.datasus.gov.br".
        """
        self.ftp_host = ftp_host
        self.evento_parada = threading.Event()

    def lista_arquivos(
        self,
        caminho_ftp: str,
        extensao: str = '.dbc',
        prefixo: Optional[str] = None,
        usuario: Optional[str] = None,
        senha: Optional[str] = None
    ) -> List[str]:
        """
        Lista arquivos num diretório específico do servidor FTP remoto.

        Conecta-se ao servidor FTP, acessa o diretório especificado em `caminho_ftp` e
        retorna os arquivos filtrados por extensão e prefixo, caso definidos.

        Args:
            caminho_ftp (str): O caminho absoluto do diretório no FTP (ex: "/dissemin/publicos/SINAN/DADOS/FINAIS").
            extensao (str, opcional): Extensão dos arquivos a serem listados (case-insensitive). Padrão é '.dbc'.
            prefixo (str | None, opcional): Prefixo dos nomes dos arquivos (case-insensitive). Padrão é None.
            usuario (str | None, opcional): Usuário para autenticação. Se None, utiliza acesso anônimo.
            senha (str | None, opcional): Senha para autenticação (requer usuário). Padrão é None.

        Returns:
            List[str]: Lista com os nomes dos arquivos encontrados que satisfazem os critérios.
                       Retorna lista vazia em caso de falha de conexão ou permissão.
        """
        try:
            with FTP(self.ftp_host, timeout=180) as ftp:
                if usuario:
                    ftp.login(user=usuario, passwd=senha or "")
                else:
                    ftp.login()
                    
                ftp.cwd(caminho_ftp)
                arquivos_e_pastas = ftp.nlst()

                if not prefixo and not extensao:
                    return arquivos_e_pastas

                if extensao:
                    files = [item for item in arquivos_e_pastas if item.upper().endswith(extensao.upper())]
                else:
                    files = arquivos_e_pastas
                    
                if prefixo:
                    files = [item for item in files if item.upper().startswith(prefixo.upper())]

                if not files:
                    logger.info("Nenhum arquivo encontrado que corresponda aos filtros aplicados.")
                    return []

                return files

        except error_perm as erro_permissao:
            logger.error(f"Erro de permissão ao acessar o caminho remoto: {erro_permissao}.")
            return []
        except Exception as erro_geral:
            logger.error(f"Ocorreu um erro inesperado na listagem de arquivos: {erro_geral}")
            return []

    def download_arquivo(
        self,
        caminho_ftp: str,
        nome_arquivo: str,
        pasta_destino: str,
        pasta_temp: str = './temp_download',
        usuario: Optional[str] = None,
        senha: Optional[str] = None,
        flag_pasta: bool = False
    ) -> Optional[str]:
        """
        Realiza a transferência de um único arquivo do servidor FTP para o disco local.

        O processo utiliza um diretório temporário para evitar a corrupção do arquivo
        em caso de interrupção da rede, movendo-o para a pasta final somente após
        o término da transferência.

        Args:
            caminho_ftp (str): O caminho absoluto do diretório remoto.
            nome_arquivo (str): O nome exato do artefato alvo.
            pasta_destino (str): Diretório local onde o arquivo será alocado permanentemente.
            pasta_temp (str, opcional): Diretório local temporário de buffer de download. Padrão './temp_download'.
            usuario (str | None, opcional): Usuário de autenticação FTP. Padrão None.
            senha (str | None, opcional): Senha de autenticação FTP. Padrão None.
            flag_pasta (bool, opcional): Sinaliza se a operação faz parte de um lote, ocultando o TQDM individual.

        Returns:
            Optional[str]: Uma string indicando o sucesso ("BAIXADO: nome" ou "Arquivo já baixado: nome").
                           Retorna None caso ocorra qualquer falha.
                           
        Raises:
            Exception: Propaga erros caso o sistema não consiga mover o arquivo temporário para o destino.
        """
        os.makedirs(pasta_destino, exist_ok=True)
        os.makedirs(pasta_temp, exist_ok=True)

        caminho_destino = os.path.join(pasta_destino, nome_arquivo)
        caminho_temp = os.path.join(pasta_temp, nome_arquivo)

        if os.path.exists(caminho_destino):
            return f"Arquivo já baixado localmente: {nome_arquivo}"

        try:
            with FTP(self.ftp_host, timeout=180) as ftp:
                if usuario:
                    ftp.login(user=usuario, passwd=senha or "")
                else:
                    ftp.login()
                ftp.cwd(caminho_ftp)

                if not flag_pasta:
                    total_size = ftp.size(nome_arquivo)
                    with open(caminho_temp, 'wb') as f_local, tqdm(
                        total=total_size,
                        unit='B', unit_scale=True, unit_divisor=1024, desc=nome_arquivo
                    ) as pbar:
                        def callback(data: bytes) -> None:
                            if self.evento_parada.is_set():
                                raise Exception("Sinal de interrupção detectado. Abortando download.")
                            f_local.write(data)
                            pbar.update(len(data))
                            
                        ftp.retrbinary(f"RETR {nome_arquivo}", callback)
                else:
                    with open(caminho_temp, 'wb') as f_local:
                        def callback(data: bytes) -> None:
                            if self.evento_parada.is_set():
                                raise Exception("Sinal de interrupção detectado. Abortando download.")
                            f_local.write(data)
                            
                        ftp.retrbinary(f"RETR {nome_arquivo}", callback)
                        
            try:
                shutil.move(caminho_temp, caminho_destino)
            except Exception as erro_movimentacao:
                raise Exception(f"Falha ao consolidar o arquivo {nome_arquivo} no destino final: {erro_movimentacao}") from erro_movimentacao
                
            return f"BAIXADO: {nome_arquivo}"

        except error_perm as erro_permissao:
            logger.error(f"Erro de acesso ou artefato inexistente no FTP: {erro_permissao}")
            return None
        except Exception as erro_geral:
            logger.error(f"Falha transiente na transferência do arquivo {nome_arquivo}: {erro_geral}")
            if os.path.exists(caminho_temp):
                os.remove(caminho_temp)
            return None
        finally:
            if os.path.exists(caminho_temp):
                os.remove(caminho_temp)

    @logar_tempo("Execução de Download Massivo via FTP (DATASUS)")
    def download_pasta(
        self,
        caminho_ftp: str,
        pasta_destino: str,
        pasta_temp: str = './temp_download',
        extensao: str = '.dbc',
        prefixo: Optional[str] = None,
        max_workers: int = 1,
        usuario: Optional[str] = None,
        senha: Optional[str] = None
    ) -> None:
        """
        Orquestra a extração de múltiplos arquivos de um diretório remoto, suportando paralelismo.

        Mapeia os artefatos viáveis baseando-se nos filtros aplicados e distribui as cargas
        de download através de um ThreadPoolExecutor, exibindo barra de progresso centralizada.

        Args:
            caminho_ftp (str): Diretório base no servidor remoto.
            pasta_destino (str): Diretório local para persistência final.
            pasta_temp (str, opcional): Diretório local de buffer. Padrão './temp_download'.
            extensao (str, opcional): Filtro de sufixo de arquivo. Padrão '.dbc'.
            prefixo (str | None, opcional): Filtro de prefixo. Padrão None.
            max_workers (int, opcional): Nível de concorrência suportado. Padrão 1.
            usuario (str | None, opcional): Usuário de autenticação. Padrão None.
            senha (str | None, opcional): Senha de autenticação. Padrão None.
        """
        logger.info("Iniciando esteira de download em lote.")

        arquivos_para_download = self.lista_arquivos(caminho_ftp, extensao, prefixo, usuario, senha)

        if not arquivos_para_download:
            logger.warning("Nenhum arquivo elegível localizado na origem. Rotina abortada.")
            return

        total_arquivos = len(arquivos_para_download)
        logger.info(f"Mapeamento concluído: {total_arquivos} arquivos identificados. Iniciando alocação de {max_workers} threads.")
        self.evento_parada.clear()

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futuros = []
                for nome_arquivo in arquivos_para_download:
                    futuros.append(
                        executor.submit(
                            self.download_arquivo,
                            caminho_ftp,
                            nome_arquivo,
                            pasta_destino,
                            pasta_temp,
                            usuario,
                            senha,
                            True
                        )
                    )

                with tqdm(total=total_arquivos, desc="Progresso Consolidado", position=0) as pbar:
                    for future in as_completed(futuros):
                        if self.evento_parada.is_set():
                            logger.warning("Interrupção solicitada pelo host. Cancelando fila pendente.")
                            executor.shutdown(wait=False, cancel_futures=True)
                            break
                        try:
                            future.result()
                            pbar.update(1)
                        except Exception as erro_thread:
                            logger.error(f"Falha operacional em tarefa assíncrona: {erro_thread}")

        except KeyboardInterrupt:
            logger.warning("Sinal SIGINT detectado pelo terminal. Desligando threads.")
            self.evento_parada.set()
        except BaseException as erro_critico:
            logger.error(f"Instabilidade crítica detectada na aplicação. Forçando parada: {erro_critico}")
            self.evento_parada.set()
            raise erro_critico
        finally:
            self.evento_parada.set()

        logger.info("Processo de download em lote finalizado.")
