# 🛠️ Espaço do Desenvolvedor (Playground)

Bem-vindo à pasta `devs/`! Este é um espaço reservado para que você possa criar scripts de teste rápidos, experimentar novas funcionalidades e debugar o comportamento do pacote localmente sem comprometer os testes de unidade principais ou a estrutura do pacote.

---

## 🚀 Como Preparar o Ambiente de Desenvolvimento

Siga os passos abaixo para preparar seu ambiente local:

### 1. Instalar as Dependências (com grupos de desenvolvimento)
Use o Poetry para instalar as dependências principais e todas as ferramentas de desenvolvimento e documentação:
```bash
poetry install --with dev,doc
```

### 2. Compilar as Extensões em C Localmente
O pipeline do DATASUS usa um módulo nativo em C (`descomprimir_dbc`) para realizar a descompressão binária acelerada. Sempre que fizer alterações na pasta `src/quadrosdesaude/c_src/` ou para a primeira execução, compile o módulo:
```bash
poetry run python build.py
```

### 3. Rodar Scripts de Teste Locais
Você pode criar qualquer arquivo Python nesta pasta `devs/` (por exemplo, `devs/meu_teste.py`) e executá-lo através do Poetry para garantir que ele localize as importações locais corretas:
```bash
poetry run python devs/exemplo.py
```

---

## 🧹 Padrões de Código e Verificações

Para manter a base de código limpa, organizada e aderente ao padrão PEP8, execute os seguintes comandos antes de submeter alterações:

### 1. Formatação Automatizada de Código
Executa nosso formatador personalizado para remover espaços desnecessários dentro de parênteses, limpar espaços vazios no final de linhas e substituir tabulações por 4 espaços:
```bash
python scripts/formatador.py
```

### 2. Validação de Sintaxe (PyCompile)
Garante que todos os arquivos `.py` são válidos e compilam sem erros de sintaxe básicos:
```bash
python -m compileall src/ tests/
```

### 3. Linter de Estilo (Flake8)
Valida a conformidade estrita das regras PEP8 (ignorando apenas linhas longas ou quebras pós-operador):
```bash
poetry run flake8 src/ --ignore=E501,W503
```

### 4. Rodar os Testes Unitários (Pytest)
Garanta que todas as funcionalidades e mockings continuam funcionando conforme o esperado:
```bash
poetry run pytest
```
