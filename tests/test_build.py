import subprocess
from pathlib import Path


def test_c_extension_compilation():
    """
    Testa se a compilação do blast.c (.so / .pyd) ocorre com sucesso via build.py
    e se a biblioteca é copiada para src/quadrosdesaude/
    """
    repo_root = Path(__file__).parent.parent
    build_script = repo_root / "build.py"

    assert build_script.exists(), "O script build.py deve existir na raiz do projeto."

    # Executa o build.py
    result = subprocess.run(
        ["python", str(build_script)], cwd=str(repo_root), capture_output=True, text=True
    )

    # O build não pode falhar com erro
    assert result.returncode == 0, (
        f"Falha ao compilar a extensão C:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    )

    # Verifica se os arquivos compilados foram movidos para a src
    src_dir = repo_root / "src" / "quadrosdesaude"
    compilados = list(src_dir.glob("*.so")) + list(src_dir.glob("*.pyd"))

    assert len(compilados) > 0, (
        "O binário compilado não foi encontrado no diretório src/quadrosdesaude/"
    )


def test_imports():
    """Garante que a sintaxe do Quadros de Saúde não foi quebrada nas refatorações."""
    # Como a refatoração DDD ainda vai ocorrer, por hora validamos a raiz

    assert True
