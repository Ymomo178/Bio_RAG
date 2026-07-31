param(
    [switch]$Gpu,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

# 输出清晰的启动阶段，方便定位首次运行时的下载或配置问题。
function Write-Step {
    param([string]$Message)

    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

# 从 .env 读取单个配置值，不把密钥输出到终端。
function Get-DotEnvValue {
    param(
        [string]$Name,
        [string]$DefaultValue = ""
    )

    $line = Get-Content -LiteralPath ".env" -Encoding utf8 |
        Where-Object { $_ -match "^\s*$([regex]::Escape($Name))\s*=" } |
        Select-Object -Last 1
    if (-not $line) {
        return $DefaultValue
    }

    $value = ($line -split "=", 2)[1].Trim()
    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
        ($value.StartsWith("'") -and $value.EndsWith("'"))) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $DefaultValue
    }
    return $value
}

# 判断 Docker Linux 引擎是否已经可以接受命令。
function Test-DockerReady {
    & docker info --format "{{.ServerVersion}}" *> $null
    return $LASTEXITCODE -eq 0
}

# 必要时自动启动 Docker Desktop，并等待容器引擎完成初始化。
function Start-DockerDesktop {
    if (Test-DockerReady) {
        return
    }

    Write-Step "正在启动 Docker Desktop"
    $dockerCommand = Get-Command docker -ErrorAction Stop
    $derivedRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $dockerCommand.Source))
    $candidates = @(
        (Join-Path $derivedRoot "Docker Desktop.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Docker\Docker\Docker Desktop.exe"),
        (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe")
    ) | Select-Object -Unique
    $desktopPath = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $desktopPath) {
        throw "Docker 命令已安装，但没有找到 Docker Desktop。请先手动启动 Docker Desktop。"
    }

    Start-Process -FilePath $desktopPath
    $deadline = (Get-Date).AddMinutes(2)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        if (Test-DockerReady) {
            Write-Host "Docker Desktop 已就绪。" -ForegroundColor Green
            return
        }
    }
    throw "Docker Desktop 在 2 分钟内没有完成启动，请打开 Docker Desktop 查看错误信息。"
}

# 读取某个 Bio RAG 容器当前使用的宿主机端口，便于重复启动时直接复用。
function Get-ExistingPublishedPort {
    param(
        [string]$ContainerName,
        [int]$ContainerPort
    )

    $containerId = & docker ps -a --filter "name=^/$ContainerName$" --format "{{.ID}}" |
        Select-Object -First 1
    if (-not $containerId) {
        return $null
    }

    $containerJson = & docker inspect $containerId
    if ($LASTEXITCODE -ne 0 -or -not $containerJson) {
        return $null
    }

    $container = @($containerJson | ConvertFrom-Json)[0]
    $portKey = "$ContainerPort/tcp"
    $binding = @($container.NetworkSettings.Ports.$portKey) | Select-Object -First 1
    if ($binding -and $binding.HostPort) {
        return [int]$binding.HostPort
    }
    return $null
}

# 检查 Windows 宿主机端口是否空闲。
function Test-PortAvailable {
    param([int]$Port)

    $connection = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -First 1
    return $null -eq $connection
}

# 优先复用现有项目端口；发生冲突时自动选择后续空闲端口。
function Resolve-ServicePort {
    param(
        [int]$ConfiguredPort,
        [string]$ContainerName,
        [int]$ContainerPort,
        [string]$ServiceName
    )

    $existingPort = Get-ExistingPublishedPort -ContainerName $ContainerName -ContainerPort $ContainerPort
    if ($existingPort) {
        return $existingPort
    }
    if (Test-PortAvailable -Port $ConfiguredPort) {
        return $ConfiguredPort
    }

    foreach ($candidate in (($ConfiguredPort + 1)..($ConfiguredPort + 100))) {
        if (Test-PortAvailable -Port $candidate) {
            Write-Host "$ServiceName 端口 $ConfiguredPort 已被占用，本次自动使用 $candidate。" -ForegroundColor Yellow
            return $candidate
        }
    }
    throw "$ServiceName 在 $ConfiguredPort 之后没有找到可用端口。"
}

# 判断源码模式所需的三个本地镜像是否全部存在。
function Test-LocalSourceImages {
    $images = @("bio-rag-web:latest", "bio-rag-backend-java:latest", "bio-rag-ai-service:latest")
    foreach ($image in $images) {
        & docker image inspect $image *> $null
        if ($LASTEXITCODE -ne 0) {
            return $false
        }
    }
    return $true
}

# 统一执行 Compose 命令并在失败时保留原始退出码。
function Invoke-Compose {
    param(
        [string[]]$Files,
        [string[]]$Arguments
    )

    if ($Files.Count -eq 1) {
        $baseFile = $Files[0]
        & docker compose -f $baseFile @Arguments
    } elseif ($Files.Count -eq 2) {
        $baseFile = $Files[0]
        $overrideFile = $Files[1]
        & docker compose -f $baseFile -f $overrideFile @Arguments
    } else {
        throw "启动脚本仅支持一个基础 Compose 文件和一个覆盖文件。"
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose 执行失败，退出码：$LASTEXITCODE"
    }
}

# 等待前端代理和 Java 后端真正能够响应请求，而不只判断容器是否存在。
function Wait-BioRagReady {
    param([int]$WebPort)

    $healthUrl = "http://127.0.0.1:$WebPort/api/v1/system/health"
    $deadline = (Get-Date).AddMinutes(5)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                return
            }
        } catch {
            # 服务仍在初始化时继续等待，最终超时后统一打印日志。
        }
        Start-Sleep -Seconds 3
    }
    throw "服务在 5 分钟内没有就绪，请运行 docker compose logs 查看日志。"
}

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "未找到 docker 命令，请先安装 Docker Desktop。"
    }
    Start-DockerDesktop

    if (-not (Test-Path -LiteralPath ".env")) {
        Copy-Item -LiteralPath ".env.example" -Destination ".env"
        Start-Process notepad.exe -ArgumentList (Join-Path $projectRoot ".env")
        throw "已创建 .env。请先填写 LLM_BASE_URL、LLM_API_KEY 和 LLM_MODEL，保存后再次双击启动。"
    }

    $requiredSettings = @("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
    $missingSettings = @($requiredSettings | Where-Object {
        [string]::IsNullOrWhiteSpace((Get-DotEnvValue -Name $_))
    })
    if ($missingSettings.Count -gt 0) {
        Start-Process notepad.exe -ArgumentList (Join-Path $projectRoot ".env")
        throw "请先在 .env 填写：$($missingSettings -join ', ')。保存后再次双击启动。"
    }

    Write-Step "正在检查端口"
    $webPort = Resolve-ServicePort ([int](Get-DotEnvValue "WEB_PORT" "5173")) "bio-rag-web-1" 80 "Web"
    $javaPort = Resolve-ServicePort ([int](Get-DotEnvValue "JAVA_PORT" "8080")) "bio-rag-backend-java-1" 8080 "Java"
    $pythonPort = Resolve-ServicePort ([int](Get-DotEnvValue "PYTHON_PORT" "8000")) "bio-rag-ai-service-1" 8000 "Python"
    $postgresPort = Resolve-ServicePort ([int](Get-DotEnvValue "POSTGRES_PORT" "5432")) "bio-rag-postgres-1" 5432 "PostgreSQL"
    $env:WEB_PORT = "$webPort"
    $env:JAVA_PORT = "$javaPort"
    $env:PYTHON_PORT = "$pythonPort"
    $env:POSTGRES_PORT = "$postgresPort"

    $usingLocalImages = Test-LocalSourceImages
    $composeFiles = @()
    if ($usingLocalImages) {
        $composeFiles += "docker-compose.yml"
    } else {
        $composeFiles += "docker-compose.images.yml"
    }
    if ($Gpu) {
        if ($usingLocalImages) {
            # 本地源码镜像已经包含 CUDA PyTorch，覆盖远程 cuda 标签以避免重复拉取。
            $env:AI_SERVICE_CUDA_IMAGE = "bio-rag-ai-service:latest"
        }
        $composeFiles += "docker-compose.gpu.yml"
    }

    $mode = if ($Gpu) { "GPU" } else { "CPU" }
    $imageSource = if ($usingLocalImages) { "本地镜像" } else { "公开预构建镜像" }
    Write-Step "正在以 $mode 模式启动（$imageSource）"
    $upArguments = @("up", "-d")
    if ($usingLocalImages) {
        $upArguments += "--no-build"
    }
    Invoke-Compose -Files $composeFiles -Arguments $upArguments

    Write-Step "正在等待服务就绪"
    Wait-BioRagReady -WebPort $webPort

    $url = "http://localhost:$webPort"
    Write-Host "`nBio RAG 已启动：$url" -ForegroundColor Green
    Write-Host "关闭此窗口不会停止服务；需要停止时双击 stop.bat。"
    if (-not $NoBrowser) {
        Start-Process $url
    }
} catch {
    Write-Host "`n启动失败：$($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
