# Requires: running API on http://localhost:8080
# Writes: for each sample file under data/samples, creates a sidecar .reference JSON file with expected_full_text
# Notes: This script uses curl.exe for upload (multipart) and PowerShell's JSON conversion.

param(
    [string]$ApiBase = "http://localhost:8080",
    [string]$SamplesDir = "data/samples",
    [int]$PollSeconds = 1,
    [int]$MaxPollIterations = 180
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $SamplesDir)) {
    Write-Error "Samples directory not found: $SamplesDir"
    exit 1
}

# Enumerate files (exclude *.reference)
$files = Get-ChildItem -File -Path $SamplesDir -Recurse | Where-Object { $_.Name -notlike '*.reference' }
if (-not $files) {
    Write-Host "No sample files found in $SamplesDir"
    exit 0
}

foreach ($f in $files) {
    try {
        Write-Host "Uploading:" $f.FullName
        $uploadJson = & curl.exe -s -F "file=@$($f.FullName)" "$ApiBase/upload"
        if (-not $uploadJson) { throw "Empty upload response" }
        $upload = $uploadJson | ConvertFrom-Json
        $fileId = $upload.file_id
        if (-not $fileId) { throw "file_id missing in upload response: $uploadJson" }

        # Poll status
        $status = $null
        for ($i = 0; $i -lt $MaxPollIterations; $i++) {
            try {
                $status = Invoke-RestMethod -UseBasicParsing "$ApiBase/status/$fileId"
                if ($status.status -eq 'done') { break }
            } catch {}
            Start-Sleep -Seconds $PollSeconds
        }
        if (-not $status -or $status.status -ne 'done') {
            Write-Warning "Timed out waiting for status=done for $fileId"
        }

        # Fetch result
        $result = Invoke-RestMethod -UseBasicParsing "$ApiBase/result/$fileId"
        $fullText = ""
        if ($result -and $result.full_text) { $fullText = [string]$result.full_text }

        # Compose reference object
        $ref = [ordered]@{
            source_filename = $f.Name
            source_relpath  = (Resolve-Path -Relative $f.FullName)
            expected_full_text = $fullText
            notes = "Auto-generated reference from current parser output."
            generated_at = (Get-Date).ToString('s')
        }
        $json = $ref | ConvertTo-Json -Depth 6
        $refPath = "$($f.FullName).reference"
        Set-Content -Path $refPath -Value $json -Encoding UTF8
        Write-Host "Saved reference:" $refPath
    } catch {
        Write-Warning "Failed for $($f.FullName): $($_.Exception.Message)"
    }
}

