<#
.SYNOPSIS
Builds and smoke-tests the API container against an isolated migrated test stack.
#>

$ErrorActionPreference = "Stop"

$projectName = "landslide-agent-e2e"
$composeFile = "docker-compose.test.yml"
$composeArgs = @("-p", $projectName, "-f", $composeFile)

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "command_failed: $Command $($Arguments -join ' ')"
    }
}

function Invoke-MigrationWithRetry {
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        & uv run --group test alembic upgrade head
        if ($LASTEXITCODE -eq 0) {
            return
        }
        if ($attempt -lt 3) {
            Start-Sleep -Seconds (2 * $attempt)
        }
    }
    throw "migration_failed_after_retries"
}

$env:RUN_E2E = "1"
$env:API_BASE_URL = "http://localhost:58000"
$env:APP_ENV = "test"
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "55432"
$env:POSTGRES_DB = "agent_test"
$env:POSTGRES_USER = "agent_test"
$env:POSTGRES_PASSWORD = "agent_test_password"
$env:VALKEY_HOST = "localhost"
$env:VALKEY_PORT = "56379"
$env:LANGFUSE_TRACING_ENABLED = "false"
$env:SESSION_NAMING_ENABLED = "false"
$env:JWT_SECRET_KEY = "integration-test-key"

try {
    Invoke-CheckedCommand -Command "docker" -Arguments (@("compose") + $composeArgs + @("up", "-d", "--wait", "db", "valkey"))
    Invoke-MigrationWithRetry
    Invoke-CheckedCommand -Command "docker" -Arguments (@("compose") + $composeArgs + @("up", "-d", "--build", "--wait", "app"))
    Invoke-CheckedCommand -Command "uv" -Arguments @("run", "--group", "test", "pytest", "-m", "e2e")
}
catch {
    & docker compose @composeArgs logs --no-color app
    throw
}
finally {
    & docker compose @composeArgs down -v --remove-orphans
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "e2e_stack_cleanup_failed"
    }
}
