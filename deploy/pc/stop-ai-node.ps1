# ==============================================================================
# BREW & BEAN — Dừng AI Node & Giải phóng VRAM trên PC
# ==============================================================================

Write-Host "=== [BREW & BEAN] Đang dừng AI Node trên PC ===" -ForegroundColor Cyan

# 1. Dừng Cloudflare Tunnel (nếu đang chạy)
Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "[OK] Đã đóng Cloudflare Tunnel (nếu có)." -ForegroundColor Green

# 2. Giải phóng VRAM của các model đang nạp trong Ollama (keep_alive = 0)
foreach ($model in @("qwen3:4b", "qwen3:8b", "bge-m3")) {
    try {
        $body = @{ model = $model; keep_alive = 0 } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 3 -ErrorAction SilentlyContinue | Out-Null
    } catch {}
}

Write-Host "[OK] Đã giải phóng VRAM cho các model Ollama." -ForegroundColor Green
