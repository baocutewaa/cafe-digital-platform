# ==============================================================================
# BREW & BEAN — Sao lưu PostgreSQL (Local hoặc Neon Cloud) về ổ cứng máy tính
# ==============================================================================

param(
    [string]$DbUrl = "postgresql://cafe_owner:password@localhost:5432/cafe_db",
    [string]$OutputDir = "$PSScriptRoot\..\..\backups"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outFile = Join-Path $OutputDir "cafe_db_$timestamp.dump"

Write-Host "[BREW & BEAN] Đang chạy pg_dump ra file: $outFile ..." -ForegroundColor Cyan
pg_dump --dbname="$DbUrl" --format=custom --file="$outFile"
Write-Host "[OK] Sao lưu hoàn tất: $outFile" -ForegroundColor Green
