$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "未找到 docker 命令。"
    }
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop 尚未启动。"
    }

    # 两套 Compose 文件使用相同项目名，down 会停止同一组容器并保留数据卷。
    & docker compose -f docker-compose.yml down
    if ($LASTEXITCODE -ne 0) {
        throw "停止服务失败，退出码：$LASTEXITCODE"
    }
    Write-Host "Bio RAG 已停止，数据库、模型缓存和上传文件均已保留。" -ForegroundColor Green
} catch {
    Write-Host "停止失败：$($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
