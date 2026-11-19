# ==============================================================================
# BREW & BEAN — Dừng PostgreSQL 17 Native trên Local (No-Docker)
# ==============================================================================

$pgBin  = "$env:USERPROFILE\.local\pgsql\bin"
$pgData = "$env:USERPROFILE\.local\pgsql17-data"

if (Test-Path "$pgBin\pg_ctl.exe") {
    & "$pgBin\pg_isready.exe" -h 127.0.0.1 -p 5432 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[INFO] Đang dừng PostgreSQL 17 Native..." -ForegroundColor Cyan
        & "$pgBin\pg_ctl.exe" -D $pgData stop -m fast | Out-Host
        Write-Host "[OK] Đã dừng PostgreSQL 17." -ForegroundColor Green
    } else {
        Write-Host "[INFO] PostgreSQL 17 hiện không chạy." -ForegroundColor Yellow
    }
}
