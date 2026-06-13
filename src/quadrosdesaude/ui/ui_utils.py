import logging
import streamlit as st
from typing import Any, List


class StreamlitLogHandler(logging.Handler):
    """
    Handler customizado para a infraestrutura de logging do Python.

    Objetiva capturar e replicar logs de processamento do backend (quadrosdesaude) 
    para dois canais distintos simultaneamente: persistência local (arquivo físico) 
    e exibição dinâmica na interface Streamlit (limitando a volumetria em memória).

    Attributes:
        placeholder (Any): Container interativo do Streamlit (`st.empty()`).
        log_file (str): Caminho absoluto/relativo do arquivo de log físico.
        max_lines_ui (int): Número limite de linhas mantidas no buffer da interface.
        log_lines (List[str]): Lista em memória contendo os registros recentes.
    """
    def __init__(self, placeholder: Any, log_file: str = "quadrosdesaude.log", max_lines_ui: int = 30) -> None:
        """
        Inicializa o handler vinculando-o ao contexto do Streamlit.

        Args:
            placeholder (Any): Componente do Streamlit preparado para injeção de texto.
            log_file (str, opcional): Nome do arquivo de disco. Padrão 'quadrosdesaude.log'.
            max_lines_ui (int, opcional): Tamanho do buffer circular para a UI. Padrão 30.
        """
        super().__init__()
        self.placeholder = placeholder
        self.log_file = log_file
        self.max_lines_ui = max_lines_ui
        self.log_lines: List[str] = []
        self.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))

    def emit(self, record: logging.LogRecord) -> None:
        """
        Subscreve a emissão de log base para suportar o direcionamento híbrido.

        Args:
            record (logging.LogRecord): O registro do log emitido pela aplicação.
        """
        try:
            msg = self.format(record)

            with open(self.log_file, "a", encoding="utf-8") as file_handler:
                file_handler.write(msg + "\n")

            self.log_lines.append(msg)
            if len(self.log_lines) > self.max_lines_ui:
                self.log_lines.pop(0)

            texto_ui = "\n".join(self.log_lines)
            self.placeholder.code(texto_ui, language="log")
            
        except Exception:
            self.handleError(record)


def render_footer() -> None:
    """
    Injeta de forma padronizada o rodapé institucional em páginas da interface.
    
    Aplica elementos HTML de separação e referências externas mantendo a integridade visual.
    """
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: gray; font-size: small;">
            <b>Quadros de Saúde</b> - Ferramentas Analíticas para Dados do SUS<br>
            Desenvolvido por <a href="https://instagram.com/dr.andreq" target="_blank" style="text-decoration: none; color: #1e88e5;"><b>Dr. André Quadros</b></a>
        </div>
        """,
        unsafe_allow_html=True
    )
