import streamlit as st
import os
import glob
import logging
from quadrosdesaude import dbf2parquet
from quadrosdesaude.ui.ui_utils import StreamlitLogHandler, render_footer

st.set_page_config(page_title="3. Domínio Parquet", page_icon="📊", layout="wide")
st.header("Etapa 3: Integração Colunar (Parquet)")
st.info("Execute a arquitetura de transformação de metadados relacionais (DBF) em armazenamento analítico otimizado e de alta performance.")

pasta_dbf_fonte = st.text_input("Diretório de Entrada (Arquivos .dbf):", value=os.path.abspath("./temp_dbf"))

if os.path.exists(pasta_dbf_fonte) and os.path.isdir(pasta_dbf_fonte):
    arquivos_dbf = glob.glob(os.path.join(pasta_dbf_fonte, "*.[dD][bB][fF]"))
    if not arquivos_dbf:
        st.warning("Nenhum arquivo relacional (.dbf) detectado na origem.")
    else:
        st.write(f"Mapeamento concluído: **{len(arquivos_dbf)}** registros identificados para transição.")

        df_dbf = [{"Alocar": False, "Arquivo Fonte": os.path.basename(f), "Caminho Físico": f} for f in arquivos_dbf]
        editado_dbf = st.data_editor(
            df_dbf,
            column_config={"Alocar": st.column_config.CheckboxColumn(default=False), "Caminho Físico": None},
            width='stretch', hide_index=True
        )

        selecionados_dbf = [linha for linha in editado_dbf if linha["Alocar"]]

        if selecionados_dbf:
            st.markdown("---")
            col_dest, col_batch, col_comp = st.columns([2, 1, 1])
            with col_dest:
                pasta_parquet = st.text_input("Diretório de Destino (Data Lake Parquet):", value=os.path.abspath("./ducklake"))
            with col_batch:
                tamanho_lote = st.number_input("Tamanho do Lote (Volume em Memória):", min_value=1000, max_value=5000000, value=100000, step=10000)
            with col_comp:
                compressao = st.selectbox("Algoritmo de Compressão:", options=["zstd", "snappy", "gzip", "none"], index=0)

            if st.button("Executar Transformação Estrutural (Parquet)"):
                with st.expander("Monitoramento Operacional da Conversão Polars", expanded=True):
                    log_placeholder = st.empty()

                handler = StreamlitLogHandler(log_placeholder)
                logger = logging.getLogger("quadrosdesaude")
                logger.addHandler(handler)

                try:
                    os.makedirs(pasta_parquet, exist_ok=True)
                    barra = st.progress(0, text="Iniciando arquitetura de transformação...")

                    sucessos = 0
                    total_arquivos = len(selecionados_dbf)

                    for i, s in enumerate(selecionados_dbf):
                        nome_arquivo = s["Arquivo Fonte"]
                        caminho_entrada = s["Caminho Físico"]
                        caminho_saida = os.path.join(pasta_parquet, nome_arquivo.replace(".dbf", ".parquet").replace(".DBF", ".parquet"))

                        barra.progress(int((i / total_arquivos) * 100), text=f"Aplicando transformação escalar: {nome_arquivo}")

                        if dbf2parquet(caminho_entrada, caminho_saida, tamanho_lote=int(tamanho_lote), compressao=compressao):
                            sucessos += 1

                    barra.progress(100, text="Pipelines de ingestão finalizados com sucesso.")
                    st.success(f"Operação concluída: {sucessos} de {total_arquivos} artefatos estruturados e alocados em `{pasta_parquet}`.")
                finally:
                    logger.removeHandler(handler)

render_footer()
