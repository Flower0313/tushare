param(
    [ValidateSet('dev','backend','frontend','worker','scheduler','maintenance','test','lint','metadata-import','validation','generate-api','analyze')]
    [string]$Command = 'dev'
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $ProjectRoot 'backend'
$Frontend = Join-Path $ProjectRoot 'frontend'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'

switch ($Command) {
    'dev' { & (Join-Path $PSScriptRoot 'start-tushare-platform.bat') }
    'backend' { Set-Location $Backend; $env:RUN_EMBEDDED_WORKER='false'; & (Join-Path $Backend '.venv\Scripts\uvicorn.exe') app.main:app --reload --host 127.0.0.1 --port 8000 }
    'frontend' { npm --prefix $Frontend run dev }
    'worker' { Set-Location $Backend; & $Python -m app.worker }
    'scheduler' { Set-Location $Backend; & $Python -m app.scheduler }
    'maintenance' { Set-Location $Backend; & $Python -m app.maintenance }
    'test' { Set-Location $Backend; & $Python -m pytest -q }
    'lint' { Set-Location $Backend; & $Python -m ruff check app tests; npm --prefix $Frontend run lint }
    'metadata-import' { Set-Location $Backend; & $Python tools\import_stock_metadata.py --refresh }
    'validation' { Set-Location $Backend; & $Python tools\validate_stock_apis.py }
    'generate-api' { npm --prefix $Frontend run generate:api }
    'analyze' { npm --prefix $Frontend run analyze }
}
