# Compares parser outputs with existing .reference sidecar files for samples
# Prints summary with counts and writes per-file diff snippets

param(
    [string]$ApiBase = "http://localhost:8080",
    [string]$SamplesDir = "data/samples",
    [int]$PollSeconds = 1,
    [int]$MaxPollIterations = 120
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $SamplesDir)) {
    Write-Error "Samples directory not found: $SamplesDir"
    exit 1
}

$refFiles = Get-ChildItem -File -Path $SamplesDir -Recurse -Filter '*.reference'
if (-not $refFiles) {
    Write-Host "No .reference files found in $SamplesDir"
    exit 0
}

$total = 0; $ok = 0; $fail = 0
$reports = @()

foreach ($rf in $refFiles) {
    $total++
    try {
        $ref = Get-Content -Path $rf.FullName -Raw | ConvertFrom-Json
        $source = Join-Path $rf.DirectoryName $ref.source_filename
        if (-not (Test-Path $source)) {
            throw "Source file not found: $source"
        }
        # Upload and get result
        $uploadJson = & curl.exe -s -F "file=@$source" "$ApiBase/upload"
        $fileId = ($uploadJson | ConvertFrom-Json).file_id
        $status = $null
        for ($i = 0; $i -lt $MaxPollIterations; $i++) {
            try { $status = Invoke-RestMethod -UseBasicParsing "$ApiBase/status/$fileId"; if ($status.status -eq 'done') { break } } catch {}
            Start-Sleep -Seconds $PollSeconds
        }
        $result = Invoke-RestMethod -UseBasicParsing "$ApiBase/result/$fileId"
        $got = [string]$result.full_text
        $exp = [string]$ref.expected_full_text
        # Simple normalization
        $norm = { param($s) if ($null -eq $s) { return '' } ([string]$s).Replace("`r","").Trim() }
        $g = & $norm $got
        $e = & $norm $exp
        if ($g -eq $e) {
            $ok++
            $reports += "OK  : $($ref.source_filename)"
        } else {
            $fail++
            $reports += "FAIL: $($ref.source_filename)"
            # Save brief diff
            $diffPath = "$source.diff.txt"
            $g2 = $g.Substring(0, [Math]::Min(1200, $g.Length))
            $e2 = $e.Substring(0, [Math]::Min(1200, $e.Length))
            Set-Content -Path $diffPath -Value ("EXPECTED:\n$e2\n\nGOT:\n$g2") -Encoding UTF8
        }
    } catch {
        $fail++
        $reports += "ERR : $($rf.Name) -> $($_.Exception.Message)"
    }
}

$summary = "TOTAL=$total OK=$ok FAIL=$fail"
$summary | Write-Host
$reports | ForEach-Object { Write-Host $_ }

