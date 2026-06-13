# QUADROS DE SAÚDE - DATASUS 🦆

[![PyPI version](https://badge.fury.io/py/quadrosdesaude.svg)](https://badge.fury.io/py/quadrosdesaude)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

O `quadrosdesaude` é um pacote Python robusto desenhado para automatizar todo o pipeline de ETL (Extração, Transformação e Carga) de dados de saúde pública do Brasil (DATASUS), convertendo os antigos formatos compactados em cofres analíticos modernos (`DBC -> DBF -> Parquet / DuckLake`).

---

## 🚀 O Problema que Resolvemos

Os dados brutos do DATASUS são disponibilizados no formato `.dbc` (compactado PKWare de forma proprietária). Ler esse formato diretamente com ferramentas de análise modernas (Pandas, Polars, DuckDB) é impossível sem etapas complexas e de difícil automatização:

1. Fazer varredura manual no FTP sujeito a timeouts.
2. Baixar os arquivos binários.
3. Descomprimir o `.dbc` para o formato padrão `.dbf` usando descompressores compilados em C.
4. Converter o `.dbf` em lotes e harmonizar colunas inconsistentes antes de persistir em `.parquet`.

**A solução:** A biblioteca `quadrosdesaude` encapsula todo esse fluxo com performance nativa em C, gerando tabelas em lotes via Polars/Arrow sem estourar a memória RAM da sua máquina.

---

## 📦 Instalação

Instale a versão estável diretamente do PyPI:

```bash
pip install quadrosdesaude
```

---

## 🖥️ Interface Gráfica (UI)

Se você preferir uma interface visual interativa (Streamlit) para mapear pastas, baixar arquivos e rodar as conversões:

```bash
quadrosdesaude-ui
```
*(O comando acima abre automaticamente o navegador na interface local do projeto).*

---

## 🛠️ Exemplos de Uso (API Python)

Abaixo estão os exemplos práticos em Python de como integrar o pacote nos seus scripts ou pipelines de dados (ex: Apache Airflow, Prefect, Dagster).

### 1. Construção de Catálogo Local (Explorar FTP sem Timeouts)
A classe `InventarioFTP` cria um banco de dados local (`DuckDB`) que armazena a estrutura de arquivos do DATASUS, permitindo buscas instantâneas sem depender de conexões instáveis.

```python
from quadrosdesaude import InventarioFTP

# Inicializa o catalogador local
inventory = InventarioFTP(db_path="inventario_datasus.db", max_workers=8)

# Mapeia recursivamente a árvore do FTP do DATASUS a partir da pasta informada
inventory.atualizar_inventario(diretorio_raiz="/dissemin/publicos/SINAN")

# Consulta e lista rapidamente os arquivos registrados localmente
target_folder = "/dissemin/publicos/SINAN/DADOS/FINAIS"
files = inventory.listar_todos_arquivos(pasta_raiz=target_folder)

print(f"Encontrados {len(files)} arquivos.")
for file_info in files[:5]:
    print(f"- Nome: {file_info['nome']} | Tamanho: {file_info['tamanho_bytes']} bytes")
```

### 2. Download Concorrente via FTP
Utilize a ferramenta integrada para baixar os arquivos `.dbc` em lote de forma otimizada.

```python
from quadrosdesaude import ftp_download_pasta

# Baixa concorrentemente todos os arquivos do SINAN de Febre Amarela (iniciam com 'FAMA')
ftp_download_pasta(
    caminho_ftp="/dissemin/publicos/SINAN/DADOS/FINAIS",
    pasta_destino="./downloads_dbc",
    extensao=".dbc",
    prefix="FAMA",
    max_workers=4
)
```

### 3. Conversão Atômica (DBC para Parquet)
Ideal para ser encapsulada em uma tarefa/operador único do Airflow ou Prefect. Processa **um único arquivo** por vez de forma atômica, apagando arquivos temporários ao final.

```python
from quadrosdesaude import dbc2parquet

# Executa o pipeline completo para um único arquivo
success = dbc2parquet(
    caminho_dbc="./downloads_dbc/FAMABR22.dbc",
    destino_parquet="./ducklake",
    pasta_temp_dbf="./temp_dbf",
    pasta_temp_parquet="./temp_parquet",
    tamanho_lote=100000  # Limite de registros em memória por lote
)

if success:
    print("Conversão realizada com sucesso e temporários limpos!")
```

### 4. Orquestradores Locais (Lote Completo)
Se você precisa converter uma pasta inteira de arquivos `.dbc` localmente, utilize nossos orquestradores integrados:

```python
from quadrosdesaude import orquestrador_single, orquestrador_multi

# Opção A: Sequencial (Recomendado para produção, Airflow/Prefect ou hardware limitado)
orquestrador_single(
    pasta_origem_dbc="./downloads_dbc",
    pasta_destino_parquet="./ducklake",
    pasta_temp_dbf="./temp_dbf",
    pasta_temp_parquet="./temp_parquet",
    tamanho_lote=100000
)

# Opção B: Concorrente via Threads (Para maior velocidade local se houver bastante RAM livre)
orquestrador_multi(
    pasta_origem_dbc="./downloads_dbc",
    pasta_destino_parquet="./ducklake",
    pasta_temp_dbf="./temp_dbf",
    pasta_temp_parquet="./temp_parquet",
    max_workers=4,
    tamanho_lote=100000
)
```

---

## 🏗️ Arquitetura e Extensões em C

A conversão crítica de `.dbc` para `.dbf` é executada por um módulo em `C` nativo (Blackbox baseado no algoritmo `blast`) compilado na instalação do pacote.
* A pasta `c_src/` é considerada núcleo imutável para garantir estabilidade multiplataforma (Windows/Linux/macOS).
* As dependências secundárias de manipulação tabular (`polars`, `pyarrow`, `duckdb` e `streamlit`) são resolvidas automaticamente na instalação.

---

## 👥 Colaboração e Desenvolvimento

Para contribuir com o projeto:

1. Faça o fork e clone o repositório.
2. Instale as dependências de desenvolvimento usando o Poetry:
   ```bash
   poetry install --with dev
   ```
3. Formate e valide seu código contra o padrão PEP8 antes de criar um PR:
   ```bash
   # Formatar código (tabs para 4 espaços e trailing spaces)
   python scripts/formatador.py
   
   # Validar sintaxe básica
   python -m compileall src/
   
   # Rodar checagem PEP8 do flake8
   poetry run flake8 src/ --ignore=E501,W503
   ```

---

## 📝 Licença e Autor

* **Autor:** Dr. André Quadros - [LinkedIn](https://www.linkedin.com/in/andrequadros/)
* **Licença:** MIT (veja o arquivo `LICENSE.md`).