# ==============================================================================
# BREW & BEAN — Thiết lập biến môi trường an toàn & tối ưu cho Ollama Local
# Chỉ lắng nghe tại 127.0.0.1:11434 (Không mở port ra LAN/Internet)
# ==============================================================================

$ErrorActionPreference = "Stop"

$ollamaEnvVars = @{
    "OLLAMA_HOST"              = "127.0.0.1:11434"
    "OLLAMA_ORIGINS"           = "http://localhost:*,http://127.0.0.1:*"
    "OLLAMA_FLASH_ATTENTION"   = "1"
    "OLLAMA_KV_CACHE_TYPE"     = "q8_0"
    "OLLAMA_MAX_LOADED_MODELS" = "2"
    "OLLAMA_NUM_PARALLEL"      = "1"
    "OLLAMA_KEEP_ALIVE"        = "30m"
}

Write-Host "[BREW & BEAN] Đang cấu hình biến môi trường User cho Ollama..." -ForegroundColor Cyan

foreach ($key in $ollamaEnvVars.Keys) {
    $val = $ollamaEnvVars[$key]
    [Environment]::SetEnvironmentVariable($key, $val, "User")
    Set-Item -Path "Env:$key" -Value $val
    Write-Host "  + $key = $val" -ForegroundColor Green
}

Write-Host "`n[BREW & BEAN] Hoàn tất thiết lập biến môi trường Ollama Local (127.0.0.1:11434)." -ForegroundColor Cyan
