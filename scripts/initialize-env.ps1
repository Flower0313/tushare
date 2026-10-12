param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
$envPath = Join-Path $ProjectRoot ".env"
$examplePath = Join-Path $ProjectRoot ".env.example"

if (Test-Path -LiteralPath $envPath) {
    exit 0
}

if (-not (Test-Path -LiteralPath $examplePath)) {
    throw "找不到环境变量模板：$examplePath"
}

Write-Host "首次启动需要配置本地 PostgreSQL。" -ForegroundColor Cyan
$securePassword = Read-Host "请输入 dbeaver_user 的 PostgreSQL 密码" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)

try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    if ([string]::IsNullOrWhiteSpace($plainPassword)) {
        throw "数据库密码不能为空。"
    }

    $encodedPassword = [Uri]::EscapeDataString($plainPassword)
    $databaseUrl = "postgresql+asyncpg://dbeaver_user:${encodedPassword}@127.0.0.1:5432/localdb"
    $content = [IO.File]::ReadAllText($examplePath)
    $content = [Text.RegularExpressions.Regex]::Replace(
        $content,
        "(?m)^DATABASE_URL=.*$",
        "DATABASE_URL=$databaseUrl"
    )
    [IO.File]::WriteAllText($envPath, $content, [Text.UTF8Encoding]::new($false))
}
finally {
    if ($passwordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    }
    $plainPassword = $null
}

Write-Host "已创建本地 .env。密码不会写入启动脚本。" -ForegroundColor Green

if ([string]::IsNullOrWhiteSpace($env:TUSHARE_TOKEN)) {
    Write-Warning "当前用户环境中没有 TUSHARE_TOKEN。Phase 1 可以启动，但后续调用接口前需要配置。"
}

