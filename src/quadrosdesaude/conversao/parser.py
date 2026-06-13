from dbfread import FieldParser
from typing import Any, Union


class StringFieldParser(FieldParser):
    """
    Parser personalizado para dbfread que tenta decodificar todos os campos como strings latin1.

    Esta classe sobrescreve o método `parse` padrão. Para cada campo lido do
    arquivo DBF, tenta remover espaços extras e decodificar os bytes
    usando a codificação 'latin-1'. Se a decodificação falhar (por exemplo,
    porque o dado não é bytes ou contém caracteres inválidos), o dado original
    é retornado sem modificação.

    Isto é útil para ler arquivos DBF com dados potencialmente anômalos ou
    tipos inconsistentes, garantindo que a extração prossiga e que os dados
    sejam tratados como texto bruto sempre que possível, crucial para Data Lakes.

    Exemplo de Uso:
        tabela = DBF('arquivo.dbf', parserclass=StringFieldParser)
    """

    def parse(self, field: Any, data: Any) -> Union[str, Any]:
        """
        Tenta decodificar o dado bruto para uma string latin-1 após remover espaços excedentes.

        Args:
            field (Any): O objeto Field do dbfread representando o esquema da coluna.
            data (Any): O valor bruto do campo extraído do arquivo DBF.

        Returns:
            Union[str, Any]: A string decodificada (se bem-sucedido) ou o dado original inalterado.
        """
        try:
            return data.strip().decode('latin1')
        except (ValueError, AttributeError):
            return data
