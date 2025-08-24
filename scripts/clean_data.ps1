Param(
  [string]$DataDir = "data",
  [switch]$Uploads,
  [switch]$Artifacts,
  [switch]$Results,
  [int]$OlderThanDays = -1,
  [switch]$DryRun,
  [switch]$Force
)

# If NC_DATA_DIR env is set, prefer it
if ($env:NC_DATA_DIR -and $env:NC_DATA_DIR.Trim()) {
  $DataDir = $env:NC_DATA_DIR
}

$ErrorActionPreference = 'Stop'

function Get-Targets {
  param(
    [string]$Root,
    [string[]]$Subdirs,
    [int]$AgeDays
  )
  $targets = @()
  foreach ($sd in $Subdirs) {
    $path = Join-Path $Root $sd
    if (-not (Test-Path $path)) { continue }
    $dirs = Get-ChildItem -Path $path -Directory -ErrorAction SilentlyContinue
    if ($AgeDays -ge 0) {
      $cutoff = (Get-Date).AddDays(-$AgeDays)
      $dirs = $dirs | Where-Object { $_.LastWriteTime -lt $cutoff }
    }
    $targets += $dirs
  }
  return $targets
}

if (-not (Test-Path $DataDir)) {
  Write-Host "Data directory not found: $DataDir"
  exit 0
}

# If none specified, clean all three
$selected = @()
if ($Uploads) { $selected += 'uploads' }
if ($Artifacts) { $selected += 'artifacts' }
if ($Results) { $selected += 'results' }
if (-not $selected) { $selected = @('uploads','artifacts','results') }

$targets = Get-Targets -Root $DataDir -Subdirs $selected -AgeDays $OlderThanDays

if (-not $targets -or $targets.Count -eq 0) {
  Write-Host "Nothing to clean under $DataDir for: $($selected -join ', ')"
  exit 0
}

Write-Host ("Candidates to remove: {0}" -f $targets.Count)
foreach ($t in $targets) {
  Write-Host (" - {0}" -f $t.FullName)
}

if ($DryRun) {
  Write-Host "Dry-run mode: no deletions performed."
  exit 0
}

if (-not $Force) {
  Write-Host "Pass -Force to actually delete, or use -DryRun to preview."
  exit 1
}

$removed = 0
foreach ($t in $targets) {
  try {
    Remove-Item -Recurse -Force -ErrorAction Stop -Path $t.FullName
    $removed++
  } catch {
    Write-Warning ("Failed to delete {0}: {1}" -f $t.FullName, $_.Exception.Message)
  }
}

Write-Host ("Deleted: {0} directorie(s)" -f $removed)


