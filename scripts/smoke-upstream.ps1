param(
    [string]$ApiBaseUrl = 'http://127.0.0.1:8000'
)

$ErrorActionPreference = 'Stop'
$ApiBaseUrl = $ApiBaseUrl.TrimEnd('/')

$health = Invoke-WebRequest -Uri "$ApiBaseUrl/health" -TimeoutSec 5 -SkipHttpErrorCheck
if ($health.StatusCode -ne 200) {
    throw "Backend health check failed: HTTP $($health.StatusCode)"
}

$request = @{
    params = @{
        ts_code = '000001.SZ'
        start_date = '20240923'
        end_date = '20240927'
        adj = 'qfq'
        freq = 'D'
        asset = 'E'
    }
    fields = @('ts_code', 'trade_date', 'close', 'adj_factor')
    write_mode = 'UPSERT'
} | ConvertTo-Json -Depth 4 -Compress

$response = Invoke-WebRequest -Uri "$ApiBaseUrl/api/apis/pro_bar/preview" -Method Post `
    -ContentType 'application/json' -Body $request -TimeoutSec 30 -SkipHttpErrorCheck
if ($response.StatusCode -ne 200) {
    $code = 'HTTP_ERROR'
    try { $code = ($response.Content | ConvertFrom-Json).error.code } catch { }
    throw "pro_bar preview failed: HTTP $($response.StatusCode), code=$code"
}

$preview = $response.Content | ConvertFrom-Json
if ($preview.rows.Count -lt 1) {
    throw 'pro_bar preview returned no rows for the smoke-test range'
}

Write-Output "Upstream smoke passed: pro_bar preview returned $($preview.rows.Count) rows."
