# ==============================================================================
# BREW & BEAN — Khởi tạo & Khởi động PostgreSQL 17 Native + pgvector (No-Docker)
# Chạy trực tiếp trong User Space (localhost:5432), không cần quyền Admin/Docker
# ==============================================================================

$ErrorActionPreference = "Stop"

$localDir = "$env:USERPROFILE\.local"
$pgRoot   = "$localDir\pgsql"
$pgBin    = "$pgRoot\bin"
$pgData   = "$localDir\pgsql17-data"
$pgLog    = "$localDir\pgsql17-server.log"
$vecTmp   = "$localDir\pgvector-tmp"

if (-not (Test-Path "$pgBin\postgres.exe")) {
    throw "Không tìm thấy PostgreSQL 17 binaries tại $pgBin"
}

# 1. Cài đặt pgvector binary vào thư mục PostgreSQL 17
if ((Test-Path "$vecTmp\lib\vector.dll") -and -not (Test-Path "$pgRoot\lib\vector.dll")) {
    Write-Host "[INFO] Đang tích hợp pgvector v0.8.7 vào PostgreSQL 17..." -ForegroundColor Cyan
    Copy-Item "$vecTmp\lib\vector.dll" "$pgRoot\lib\vector.dll" -Force
    Copy-Item "$vecTmp\share\extension\vector*" "$pgRoot\share\extension\" -Force
}

# 2. Khởi tạo Data Directory (initdb) nếu chưa tồn tại
if (-not (Test-Path "$pgData\PG_VERSION")) {
    Write-Host "[INFO] Đang khởi tạo PostgreSQL 17 Data Directory tại $pgData (UTF-8)..." -ForegroundColor Cyan
    & "$pgBin\initdb.exe" -D $pgData -U postgres -E UTF8 --locale=C --auth=trust | Out-Host
}

# 3. Kiểm tra và khởi động PostgreSQL Server trên localhost:5432
& "$pgBin\pg_isready.exe" -h 127.0.0.1 -p 5432 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Đang khởi động PostgreSQL 17 Native tại localhost:5432..." -ForegroundColor Cyan
    & "$pgBin\pg_ctl.exe" -D $pgData -l $pgLog -o "-p 5432 -h 127.0.0.1,::1" start | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Không thể khởi động PostgreSQL 17 Native."
    }
    Write-Host "[OK] PostgreSQL 17 Native đã khởi động tại localhost:5432." -ForegroundColor Green
} else {
    Write-Host "[OK] PostgreSQL 17 Native đang chạy tại localhost:5432." -ForegroundColor Green
}

# 4. Tạo role cafe_owner, database cafe_db và kích hoạt extensions
$roleExists = & "$pgBin\psql.exe" -h 127.0.0.1 -p 5432 -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='cafe_owner'"
if ("$roleExists".Trim() -ne "1") {
    Write-Host "[INFO] Đang tạo role cafe_owner..." -ForegroundColor Cyan
    & "$pgBin\psql.exe" -h 127.0.0.1 -p 5432 -U postgres -c "CREATE ROLE cafe_owner WITH LOGIN PASSWORD 'password' SUPERUSER;" | Out-Host
}

$dbExists = & "$pgBin\psql.exe" -h 127.0.0.1 -p 5432 -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='cafe_db'"
if ("$dbExists".Trim() -ne "1") {
    Write-Host "[INFO] Đang tạo database cafe_db..." -ForegroundColor Cyan
    & "$pgBin\psql.exe" -h 127.0.0.1 -p 5432 -U postgres -c "CREATE DATABASE cafe_db OWNER cafe_owner ENCODING 'UTF8';" | Out-Host
}

$initSql = Join-Path $PSScriptRoot "..\..\scripts\sql\init_neon.sql"
if (Test-Path $initSql) {
    Write-Host "[INFO] Đang kích hoạt extensions (vector, pg_trgm, unaccent, pgcrypto) trên cafe_db..." -ForegroundColor Cyan
    & "$pgBin\psql.exe" -h 127.0.0.1 -p 5432 -U cafe_owner -d cafe_db -f $initSql | Out-Host
}

# 5. Kiểm tra danh sách extensions đã cài đặt
Write-Host "`n[OK] Danh sách Extensions đã kích hoạt trên cafe_db:" -ForegroundColor Green
& "$pgBin\psql.exe" -h 127.0.0.1 -p 5432 -U cafe_owner -d cafe_db -c "SELECT extname, extversion FROM pg_extension ORDER BY extname;" | Out-Host
