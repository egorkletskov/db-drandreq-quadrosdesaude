# Plano de Ação: Próximo Release (v0.3.0) — Quadros de Saúde

Este documento define os passos necessários para realizar o próximo release do pacote `quadrosdesaude` no PyPI, focando em usabilidade, correção de bugs, padronização do código (PEP8), testes de integridade de sintaxe e segurança.

---

## 1. Correção de Bugs Críticos e Refatoração dos Orquestradores
*   **Orquestração Modular:**
    *   Focaremos na execução atômica perfeita de **um arquivo por vez** (ideal para ferramentas de produção como Airflow e Prefect).
    *   Separar a lógica em duas funções distintas:
        1.  `orquestrador_single(pasta_origem, pasta_destino, ...)`: Processa arquivos sequencialmente, sem concorrência, o que é perfeito para orquestradores externos ou uso em ambientes locais limitados.
        2.  `orquestrador_multi(pasta_origem, pasta_destino, max_workers, ...)`: Gerencia a concorrência via `ThreadPoolExecutor` (paralelismo em nível de CPU liberando o GIL na extensão C e no Polars/Arrow).
    *   Manter a função `orquestrador(...)` original como uma fachada/roteador inteligente de compatibilidade reversa:
        ```python
        def orquestrador(..., max_workers=1, ...):
            if max_workers > 1:
                return orquestrador_multi(...)
            else:
                return orquestrador_single(...)
        ```
    *   **Ação:** Corrigir também o bug de digitação `futuro.append(...)` na nova implementação concorrente de `orquestrador_multi` alterando para `futuros.append(...)`.

---

## 2. Inclusão da Interface Gráfica (UI) no PyPI
Para entregar um produto completo aos pesquisadores e profissionais de saúde, incluiremos a interface Streamlit diretamente no pacote publicado.

*   **Mudança de Estrutura:**
    *   Mover a pasta `ui_quadrosdesaude` para `src/quadrosdesaude/ui`.
    *   Mover o script `iniciar_ui.py` para `src/quadrosdesaude/ui/iniciar_ui.py`.
*   **Adaptação do Código da UI:**
    *   Atualizar o arquivo `src/quadrosdesaude/ui/iniciar_ui.py` para resolver o caminho absoluto dos arquivos do Streamlit (como o `1_Home.py`) de forma dinâmica. Assim, o comando funcionará independentemente de onde o pacote for instalado no sistema do usuário.
    *   Implementar a função principal `main()` em `iniciar_ui.py` que executa o Streamlit por baixo do pano.
*   **Ponto de Entrada (CLI) no PyPI:**
    *   Configurar a tag `[tool.poetry.scripts]` no `pyproject.toml` para expor o comando `quadrosdesaude-ui` globalmente.
    *   Após a instalação via `pip install quadrosdesaude`, o usuário poderá simplesmente rodar:
        ```bash
        quadrosdesaude-ui
        ```

---

## 3. Linter, PEP8 e Verificação de Sintaxe (Tab para Espaços, Flake8 e PyCompile)
Conforme solicitado, garantiremos o cumprimento estrito do padrão PEP8 e realizaremos verificações sistemáticas de formatação e sintaxe.

*   **Formatação (Tab para Espaços):**
    *   Executar o script utilitário (`scripts/formatador.py`) que percorre todos os arquivos Python e substitui tabulações (`\t`) por 4 espaços, removendo também espaços extras ao fim de linhas.
*   **Validação de Sintaxe (`py_compile`):**
    *   Validar a integridade de sintaxe de todos os arquivos python do projeto executando `py_compile` em lote para garantir que nenhuma alteração introduziu erros de parsing.
*   **Conformidade PEP8 (`flake8`):**
    *   Adicionar `flake8` nas dependências de desenvolvimento no `pyproject.toml`.
    *   Estabelecer a execução do `flake8` no diretório `src/` para assegurar conformidade total com a PEP8 antes do build.

---

## 4. Melhorias na Documentação e Exemplos de Uso
O README atual é muito curto e não explica como utilizar a biblioteca via código Python. Vamos expandir e traduzir o manual.

*   **Novo `README.MD`:**
    *   Escrito em Português do Brasil (PT-BR).
    *   Adicionar seção com exemplos de código práticos e copy-pasteables (com código e variáveis em inglês).
    *   **Exemplos inclusos:**
        1. Como baixar arquivos DBC via FTP usando o `FTPDownloader`.
        2. Como utilizar o `InventarioFTP` para listar rapidamente arquivos sem timeouts.
        3. Como converter um único arquivo DBC para Parquet usando `dbc2parquet`.
        4. Como orquestrar uma pasta de arquivos DBC para criar o "DuckLake" usando `orquestrador`.
        5. Como iniciar a interface gráfica pelo terminal.
*   **Melhoria no MkDocs (`mkdocs.yml`):**
    *   Corrigir o caminho em `plugins.mkdocstrings` de `paths: [quadrosdesaude]` para `paths: [src]`. Sem isso, a geração automática da referência de API a partir de docstrings falha no MkDocs porque ele não consegue importar o módulo local `quadrosdesaude`.
    *   Complementar a documentação de `docs/index.md` com os mesmos exemplos do README expandido.

---

## 5. Segurança do Submódulo Privado (`.qds_standards`)
*   **Status Atual:** O submódulo `.qds_standards` é privado no GitHub.
*   **Segurança de Acesso:** Pessoas externas que clonarem o repositório público `quadrosdesaude` não terão acesso de leitura ao repositório `.qds_standards` no GitHub, resultando em erro se tentarem atualizar o submódulo.
*   **Exclusão na Publicação:** O arquivo `pyproject.toml` especifica explicitamente para o Poetry empacotar apenas `src/quadrosdesaude` (`packages = [{include = "quadrosdesaude", from = "src"}]`). Portanto, o código do submódulo `.qds_standards` **nunca** fará parte dos pacotes `.whl` ou `.tar.gz` distribuídos publicamente no PyPI. Está 100% isolado.
