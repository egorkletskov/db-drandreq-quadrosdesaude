import streamlit as st
import os
import logging
from quadrosdesaude import InventarioFTP, FTPDownloader
from quadrosdesaude.ui.ui_utils import StreamlitLogHandler, render_footer

st.set_page_config(page_title="1. Extração FTP", page_icon="📡", layout="wide")
st.header("Etapa 1: Extração Estruturada via FTP")
st.info(
    "Inicialização de mapeamento e construção de catálogo local para exploração do repositório remoto DATASUS."
)

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Parametrização do Catálogo")
    raiz_ftp = st.text_input("Diretório Raiz (FTP)", value="/dissemin/publicos")
    max_workers_sync = st.number_input(
        "Carga de Conexões Concorrentes (Threads)", min_value=1, max_value=32, value=8
    )

    if st.button("Executar Sincronização de Catálogo"):
        with st.expander("Monitoramento da Sincronização", expanded=True):
            log_placeholder = st.empty()

        handler = StreamlitLogHandler(log_placeholder)
        logger = logging.getLogger("quadrosdesaude")
        logger.addHandler(handler)

        try:
            with st.spinner("Construindo topologia de arquivos do DATASUS. Aguarde..."):
                inv = InventarioFTP(max_workers=int(max_workers_sync))
                inv.atualizar_inventario(diretorio_raiz=raiz_ftp)
                st.success("Sincronização de catálogo finalizada.")
        except BaseException as erro_critico:
            inv.evento_parada.set()
            raise erro_critico
        finally:
            logger.removeHandler(handler)

    st.markdown("---")
    pasta_destino = st.text_input(
        "Diretório Local de Persistência", value=os.path.abspath("./downloads")
    )

with col2:
    st.subheader("Explorador de Arquivos")
    if "pasta_atual" not in st.session_state:
        st.session_state.pasta_atual = "/dissemin/publicos"

    pasta_alvo = st.text_input("Segmento FTP Atual:", value=st.session_state.pasta_atual)

    inv = InventarioFTP()
    itens = inv.listar_todos_arquivos(pasta_alvo)

    if not itens:
        st.warning(
            "O diretório informado não contém artefatos indexados no catálogo local. Execute a sincronização."
        )
    else:
        st.write(f"Volume identificado: **{len(itens)}** arquivos associados ao nó `{pasta_alvo}`")
        df_itens = [
            {
                "Selecionar": False,
                "Nome do Artefato": i["nome"],
                "Diretório Origem": i["caminho_pai"],
                "Tamanho (MB)": round(i["tamanho_bytes"] / 1024 / 1024, 2),
                "Endereço Físico FTP": i["caminho_completo"],
            }
            for i in itens
        ]

        editado = st.data_editor(
            df_itens,
            column_config={
                "Selecionar": st.column_config.CheckboxColumn(default=False),
                "Endereço Físico FTP": None,
            },
            width="stretch",
            hide_index=True,
        )

        selecionados = [linha for linha in editado if linha["Selecionar"]]

        if selecionados:
            st.write("---")
            if st.button("Confirmar Execução de Download em Lote"):
                with st.expander("Monitoramento de Transferência", expanded=True):
                    log_placeholder_dl = st.empty()

                handler_dl = StreamlitLogHandler(log_placeholder_dl)
                logger_dl = logging.getLogger("quadrosdesaude")
                logger_dl.addHandler(handler_dl)

                try:
                    with st.status("Inicializando fila de alocação...") as status:
                        downloader = FTPDownloader()
                        for s in selecionados:
                            msg_inicio = f"Requisitando artefato: `{s['Diretório Origem']}/{s['Nome do Artefato']}`"
                            st.write(msg_inicio)
                            logger_dl.info(msg_inicio)

                            downloader.download_arquivo(
                                caminho_ftp=s["Diretório Origem"],
                                nome_arquivo=s["Nome do Artefato"],
                                pasta_destino=pasta_destino,
                                flag_pasta=True,
                            )
                            logger_dl.info(
                                f"Concluído: Transferência do arquivo {s['Nome do Artefato']} finalizada."
                            )

                        status.update(
                            label="Fila de processos encerrada.", state="complete", expanded=False
                        )
                        st.success(f"Ativos persistidos no diretório: {pasta_destino}")
                except BaseException as erro_download:
                    downloader.evento_parada.set()
                    raise erro_download
                finally:
                    logger_dl.removeHandler(handler_dl)

render_footer()
