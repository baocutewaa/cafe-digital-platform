# ==============================================================================
# BREW & BEAN — Khởi động AI Node trên PC (Ollama Local + Cloudflare Tunnel)
# Hỗ trợ cả chế độ Local Dev (chỉ bật Ollama) và Production (bật kèm cloudflared)
# ==============================================================================

param(
    [switch]$WithTunnel = $false
)

$ErrorActionPreference = "Continue"

Write-Host "=== [BREW & BEAN] Khởi động AI Node trên PC ===" -ForegroundColor Cyan

# 1. Nạp biến môi trường an toàn cho Ollama
$setupScript = Join-Path $PSScriptRoot "setup-ollama-env.ps1"
if (Test-Path $setupScript) {
    & $setupScript
}

# 2. Kiểm tra / Khởi động tiến trình Ollama (127.0.0.1:11434)
try {
    $ver = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 3
    Write-Host "[OK] Ollama đang chạy (version: $($ver.version))." -ForegroundColor Green
} catch {
    Write-Host "[INFO] Đang khởi động tiến trình Ollama serve..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# 3. Nạp ấm (Warm-up) BGE-M3 vào bộ nhớ
Write-Host "[INFO] Đang warm-up model embedding bge-m3..." -ForegroundColor Cyan
try {
    $embedBody = @{ model = "bge-m3"; input = "Warm up BREW & BEAN" } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/embed" -Method Post -Body $embedBody -ContentType "application/json" -TimeoutSec 30 | Out-Null
    Write-Host "[OK] Model bge-m3 đã sẵn sàng." -ForegroundColor Green
} catch {
    Write-Host "[WARN] Chưa thể warm-up bge-m3: $_" -ForegroundColor Yellow
}

# 4. Nếu chạy ở Giai đoạn P7 (-WithTunnel), bật cloudflared
if ($WithTunnel) {
    if (Get-Command cloudflared -ErrorAction SilentlyContinue) {
        Write-Host "[INFO] Đang khởi động Cloudflare Named Tunnel..." -ForegroundColor Cyan
        Start-Process -FilePath "cloudflared" -ArgumentList "tunnel run" -WindowStyle Hidden
        Write-Host "[OK] Cloudflare Tunnel đã được kích hoạt." -ForegroundColor Green
    } else {
        Write-Host "[WARN] Chưa cài đặt cloudflared (chỉ cần ở Giai đoạn P7)." -ForegroundColor Yellow
    }
}
