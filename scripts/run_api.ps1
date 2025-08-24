Param(
  [string]$HostName = "0.0.0.0",
  [int]$Port = 8080
)

if ($env:NC_APP_HOST -and $env:NC_APP_HOST.Trim()) {
  $HostName = $env:NC_APP_HOST
}
if ($env:NC_APP_PORT -and $env:NC_APP_PORT.Trim()) {
  $Port = [int]$env:NC_APP_PORT
}

uvicorn nc_parser.api.main:app --host $HostName --port $Port


