import streamlit as st

from quadrosdesaude.ui.ui_utils import render_footer

st.set_page_config(
    page_title="Quadros de Saúde | Painel de Controle",
    page_icon="🏥",
    layout="centered",
)

st.title("Quadros de Saúde v0.3.0")
st.markdown("Plataforma Orquestradora de ETL para bases do DATASUS.")
st.markdown("---")
st.markdown("### Navegação do Pipeline:")
st.markdown(
    """
    1. **Extração FTP:** Conexão, mapeamento e extração estruturada de arquivos do repositório remoto.
    2. **Descompressão:** Conversão em lote de arquivos binários nativos (.dbc) para formato tabular padrão (.dbf).
    3. **Domínio Parquet:** Transformação de dados estruturados para o padrão colunar analítico (.parquet).
    """
)

st.info("Para diretrizes arquiteturais e contribuições, consulte a documentação técnica oficial no repositório.")

render_footer()
