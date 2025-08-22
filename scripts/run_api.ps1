Param(
  [string]$HostName = $env:NC_APP_HOST
    ? $env:NC_APP_HOST
    : "0.0.0.0",
  [int]$Port = $env:NC_APP_PORT
    ? [int]$env:NC_APP_PORT
    : 8080
)

uvicorn nc_parser.api.main:app --host $HostName --port $Port


