param(
    [string]$HostName = $(if ($env:UNIGURU_HOST) { $env:UNIGURU_HOST } else { "0.0.0.0" }),
    [int]$Port = $(if ($env:UNIGURU_PORT) { [int]$env:UNIGURU_PORT } else { 8000 }),
    [int]$Workers = $(if ($env:UNIGURU_WORKERS) { [int]$env:UNIGURU_WORKERS } else { 2 })
)

python -m uvicorn uniguru.service.api:app --host $HostName --port $Port --workers $Workers
