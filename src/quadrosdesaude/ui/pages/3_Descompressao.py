import streamlit as st
import os
import glob
import logging
from quadrosdesaude import dbc2dbf
from quadrosdesaude.ui.ui_utils import StreamlitLogHandler, render_footer

st.set_page_config(page_title="2. Descompressão", page_icon="🗃️", layout="wide")
st.header("Etapa 2: Conversão Linear (DBC para DBF)")
st.info("Execute a descompressão binária de artefatos PKWare do DATASUS (.dbc) para matrizes analíticas padrão (.dbf).")

pasta_dbc = st.text_input("Diretório de Entrada (Arquivos .dbc):", value=os.path.abspath("./downloads"))

if os.path.exists(pasta_dbc) and os.path.isdir(pasta_dbc):
    arquivos_dbc = glob.glob(os.path.join(pasta_dbc, "*.[dD][bB][cC]"))
    if not arquivos_dbc:
        st.warning("Nenhum arquivo executável (.dbc) identificado no diretório informado.")
    else:
        st.write(f"Mapeamento concluído: **{len(arquivos_dbc)}** registros elegíveis para conversão.")

        df_dbc = [{"Alocar": False, "Nome do Arquivo": os.path.basename(f), "Caminho Absoluto": f} for f in arquivos_dbc]
        editado_dbc = st.data_editor(
            df_dbc,
            column_config={"Alocar": st.column_config.CheckboxColumn(default=False), "Caminho Absoluto": None},
            width='stretch', hide_index=True
        )

        selecionados_dbc = [linha for linha in editado_dbc if linha["Alocar"]]

        if selecionados_dbc:
            st.markdown("---")
            pasta_dbf = st.text_input("Diretório de Saída (Staging DBF):", value=os.path.abspath("./temp_dbf"))

            if st.button("Executar Conversão Sistêmica"):
                with st.expander("Monitoramento Operacional da Extensão C", expanded=True):
                    log_placeholder = st.empty()

                handler = StreamlitLogHandler(log_placeholder)
                logger = logging.getLogger("quadrosdesaude")
                logger.addHandler(handler)

                try:
                    os.makedirs(pasta_dbf, exist_ok=True)
                    barra = st.progress(0, text="Inicializando esteira de conversão...")

                    sucessos = 0
                    total_arquivos = len(selecionados_dbc)
                    
                    for i, s in enumerate(selecionados_dbc):
                        nome_arquivo = s["Nome do Arquivo"]
                        caminho_entrada = s["Caminho Absoluto"]
                        caminho_saida = os.path.join(pasta_dbf, nome_arquivo.replace(".dbc", ".dbf").replace(".DBC", ".dbf"))

                        barra.progress(int((i / total_arquivos) * 100), text=f"Processando: {nome_arquivo}")

                        if dbc2dbf(caminho_entrada, caminho_saida):
                            sucessos += 1

                    barra.progress(100, text="Esteira de processamento finalizada.")
                    st.success(f"Ciclo consolidado: {sucessos} de {total_arquivos} registros convertidos com êxito em `{pasta_dbf}`.")
                finally:
                    logger.removeHandler(handler)

render_footer()
