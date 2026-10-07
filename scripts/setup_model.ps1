# Download GELab-Zero-4B-preview from Hugging Face and register it in local Ollama (Windows).
# Same steps as setup_model.sh; follows third_party/gelab-zero/README.md (Step 1.2).
#
#   .\scripts\setup_model.ps1                    # q8_0 (~4.4 GB)
#   $env:QUANT = "Q4_K_M"; .\scripts\setup_model.ps1
#
# Weights land in models\ (gitignored via models/.gitignore).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$Name = "gelab-zero-4b-preview"
$Quant = if ($env:QUANT) { $env:QUANT } else { "q8_0" }
$Dir = "models\$Name"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { throw "Install Ollama first: https://ollama.com/download" }
if (-not (Get-Command hf -ErrorAction SilentlyContinue)) { python -m pip install -q huggingface_hub }

New-Item -ItemType Directory -Force models | Out-Null
hf download --no-force-download stepfun-ai/GELab-Zero-4B-preview --local-dir $Dir
if ($LASTEXITCODE -ne 0) { throw "hf download failed" }

Push-Location $Dir
try {
    if ($Quant -eq "f16") { ollama create $Name -f Modelfile } else { ollama create -q $Quant $Name -f Modelfile }
    if ($LASTEXITCODE -ne 0) { throw "ollama create failed" }
} finally { Pop-Location }
ollama list | Select-String $Name
Write-Host "Model ready. In .env: LLM_MODEL=$Name and LLM_QUANT=$Quant"
