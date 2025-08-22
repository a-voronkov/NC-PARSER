Param(
  [Parameter(Mandatory=$true)][string]$FilePath,
  [string]$BaseUrl = "http://localhost:8080",
  [int]$ChunkSize = 262144
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $FilePath)) { throw "File not found: $FilePath" }

# Init
$initBody = @{ filename = [IO.Path]::GetFileName($FilePath); size_bytes = (Get-Item $FilePath).Length } | ConvertTo-Json -Compress
$initResp = Invoke-RestMethod -Method Post -Uri "$BaseUrl/upload/init" -ContentType 'application/json' -Body $initBody
$fileId = $initResp.file_id
Write-Host "file_id=$fileId"

# Send chunks
$fs = [System.IO.File]::OpenRead($FilePath)
try {
  $buffer = New-Object byte[] $ChunkSize
  $index = 0
  while (($read = $fs.Read($buffer, 0, $ChunkSize)) -gt 0) {
    $tmp = [System.IO.Path]::GetTempFileName()
    try {
      [System.IO.File]::WriteAllBytes($tmp, $buffer[0..($read-1)])
      Invoke-WebRequest -Method Post -Uri "$BaseUrl/upload/chunk?file_id=$fileId&index=$index" -InFile $tmp -ContentType 'application/octet-stream' | Out-Null
      $index++
    } finally {
      Remove-Item -Force $tmp -ErrorAction SilentlyContinue
    }
  }
} finally {
  $fs.Dispose()
}

# Complete
Invoke-RestMethod -Method Post -Uri "$BaseUrl/upload/complete?file_id=$fileId" | Out-Null

# Poll result
for ($i=0; $i -lt 30; $i++) {
  try {
    $res = Invoke-RestMethod -Uri "$BaseUrl/result/$fileId"
    if ($res -ne $null -and $res.document_id) {
      $res | ConvertTo-Json -Depth 6 -Compress | Write-Output
      exit 0
    }
  } catch {}
  Start-Sleep -Seconds 1
}

throw "Result not ready"


