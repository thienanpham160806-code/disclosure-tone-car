# Mở dashboard Đồ án 05 bằng một lệnh:
#   powershell -ExecutionPolicy Bypass -File dashboard\run.ps1
# Lần đầu (hoặc khi giao diện vừa sửa) sẽ build frontend (cần Node.js); sau đó tự mở trình duyệt ở http://127.0.0.1:8000
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$fe = Join-Path $PSScriptRoot "frontend"
$py = Join-Path $root ".venv\Scripts\python.exe"
$index = Join-Path $fe "dist\index.html"

$canBuild = [bool](Get-Command npm -ErrorAction SilentlyContinue)
$stale = -not (Test-Path $index)
if (-not $stale) {
    $newest = Get-ChildItem (Join-Path $fe "src"), (Join-Path $fe "index.html") -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $stale = $newest.LastWriteTime -gt (Get-Item $index).LastWriteTime
}
if ($stale -and $canBuild) {
    Write-Host "Đang build giao diện..." -ForegroundColor Cyan
    if (-not (Test-Path (Join-Path $fe "node_modules"))) { npm --prefix $fe install --no-audit --no-fund }
    npm --prefix $fe run build
} elseif ($stale) {
    Write-Host "Chưa có bản build giao diện và máy không có Node.js (npm). Cài Node.js LTS rồi chạy lại." -ForegroundColor Yellow
    exit 1
}

& $py -c "import fastapi, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) { & $py -m pip install "fastapi>=0.110" "uvicorn>=0.29" }

$env:PYTHONUTF8 = "1"
Set-Location $root
& $py (Join-Path $PSScriptRoot "backend\main.py") --open
