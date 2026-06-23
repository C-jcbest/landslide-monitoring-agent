<#
.SYNOPSIS
Runs PostgreSQL and Valkey integration tests in an isolated Docker Compose project.

.DESCRIPTION
Creates an ephemeral `landslide-agent-test` Compose project on non-default
ports, applies Alembic migrations, runs only pytest's integration marker, and
always removes its containers and named volumes before returning.
#>

$ErrorActionPreference = "Stop"

$projectName = "landslide-agent-test"
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

$env:RUN_INTEGRATION = "1"
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
    Invoke-CheckedCommand -Command "uv" -Arguments @("run", "--group", "test", "alembic", "upgrade", "head")
    Invoke-CheckedCommand -Command "uv" -Arguments @("run", "--group", "test", "pytest", "-m", "integration")
}
finally {
    & docker compose @composeArgs down -v --remove-orphans
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "integration_stack_cleanup_failed"
    }
}
