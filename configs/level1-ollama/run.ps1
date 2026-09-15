$ErrorActionPreference = "Stop"
$ModelName = "qwen-processor"

Write-Host "=== Building Level 1 Ollama Model: $ModelName ===" -ForegroundColor Cyan
Set-Location $PSScriptRoot

ollama create $ModelName -f ./Modelfile

Write-Host "Model '$ModelName' created successfully!" -ForegroundColor Green
Write-Host "Usage example:"
Write-Host "  Get-Content data.log | ollama run $ModelName 'Extract all error messages as JSON array'"