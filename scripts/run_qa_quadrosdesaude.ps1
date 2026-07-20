$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutputFile = "${Timestamp}__qa_report_qds.txt"

Write-Output "========================================" | Out-File -FilePath $OutputFile -Encoding utf8
Write-Output "       RELATORIO QA - QUADROS DE SAUDE  " | Out-File -FilePath $OutputFile -Encoding utf8 -Append
Write-Output "========================================" | Out-File -FilePath $OutputFile -Encoding utf8 -Append
Write-Output "Data da Execucao: $(Get-Date)" | Out-File -FilePath $OutputFile -Encoding utf8 -Append
Write-Output "" | Out-File -FilePath $OutputFile -Encoding utf8 -Append

# Usando poetry run para o ambiente isolado do Quadros de Saúde
Write-Output "--- RUFF CHECK (Estilo e Erros) ---" | Out-File -FilePath $OutputFile -Encoding utf8 -Append
$ruffCheck = poetry run ruff check . 2>&1
$ruffCheck | Out-File -FilePath $OutputFile -Encoding utf8 -Append
Write-Output "" | Out-File -FilePath $OutputFile -Encoding utf8 -Append

Write-Output "--- MYPY (Tipagem Estatica) ---" | Out-File -FilePath $OutputFile -Encoding utf8 -Append
$mypyCheck = poetry run mypy src/ 2>&1
$mypyCheck | Out-File -FilePath $OutputFile -Encoding utf8 -Append
Write-Output "" | Out-File -FilePath $OutputFile -Encoding utf8 -Append

Write-Output "--- PYTEST (Testes Base & Compilacao C) ---" | Out-File -FilePath $OutputFile -Encoding utf8 -Append
$pytestRun = poetry run pytest tests/ 2>&1
$pytestRun | Out-File -FilePath $OutputFile -Encoding utf8 -Append
Write-Output "" | Out-File -FilePath $OutputFile -Encoding utf8 -Append

Write-Host "Relatorio gerado com sucesso em: .quadrosdesaude/$OutputFile" -ForegroundColor Green
