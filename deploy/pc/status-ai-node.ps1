# ==============================================================================
# BREW & BEAN — Kiểm tra trạng thái AI Node (Ollama Local & Cloudflare Tunnel)
# ==============================================================================

Write-Host "=== [BREW & BEAN] Trạng thái AI Node trên PC ===" -ForegroundColor Cyan

# 1. Kiểm tra Ollama Local (127.0.0.1:11434)
try {
    $ver = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 3
    Write-Host "[ONLINE] Ollama Local (http://127.0.0.1:11434) - Version: $($ver.version)" -ForegroundColor Green

    $ps = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/ps" -TimeoutSec 3
    if ($ps.models -and $ps.models.Count -gt 0) {
        Write-Host "  Models đang nạp trong RAM/VRAM:" -ForegroundColor Cyan
        foreach ($m in $ps.models) {
            $sizeMB = [math]::Round($m.size / 1MB, 1)
            $vramMB = [math]::Round($m.size_vram / 1MB, 1)
            Write-Host "    - $($m.name): Tổng $sizeMB MB (VRAM: $vramMB MB)" -ForegroundColor White
        }
    } else {
        Write-Host "  (Chưa có model nào đang giữ trong VRAM)" -ForegroundColor DarkGray
    }
} catch {
    Write-Host "[OFFLINE] Ollama Local không phản hồi tại http://127.0.0.1:11434" -ForegroundColor Red
}

# 2. Kiểm tra Cloudflare Tunnel daemon
$cf = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
if ($cf) {
    Write-Host "[ONLINE] Tiến trình cloudflared đang chạy (PID: $($cf.Id -join ', '))" -ForegroundColor Green
} else {
    Write-Host "[LOCAL-ONLY] Tiến trình cloudflared đang tắt (Bình thường ở giai đoạn P0-P6)." -ForegroundColor Yellow
}
