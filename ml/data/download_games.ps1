# Downloads whole games (720p mp4) plus the video information (<name>.info.json) for every row of a
# list such as videos_next.csv, named exactly like the "name" column, so the cloud ingest can match
# each video to its official game log. The ingest cuts the training segments itself.
# Needs yt-dlp and ffmpeg:   winget install yt-dlp.yt-dlp   and   winget install Gyan.FFmpeg
# Run in PowerShell in this folder:
#   .\download_games.ps1 -Csv videos_next.csv -Out "G:\Meine Ablage\<Drive-Ordner>"
# (a Google Drive for desktop folder uploads by itself). Optional: -Max 10 for a first test.
# Behind a VPN or company network YouTube may answer "confirm you are not a bot": run it over a
# phone hotspot, or pass -Browser chrome|edge|firefox to use your signed-in YouTube session.
param([string]$Csv = "videos_next.csv", [string]$Out = "handball-games", [int]$Max = 0,
      [string]$Browser = "")
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$rows = Import-Csv -Path $Csv -Delimiter ';'
$i = 0; $ok = 0; $failed = @()
foreach ($r in $rows) {
  $i++
  if ($Max -gt 0 -and $ok -ge $Max) { break }
  $name = $r.name; $url = $r.url
  if (-not $url -or -not $name) { continue }
  if (Test-Path (Join-Path $Out "$name.mp4")) { Write-Host "[$i/$($rows.Count)] $name already there"; $ok++; continue }
  Write-Host "[$i/$($rows.Count)] $name"
  $auth = @()
  if ($Browser) { $auth = @("--cookies-from-browser", $Browser, "--sleep-requests", "2", "--sleep-interval", "20", "--max-sleep-interval", "60") }
  # download into a temp folder first, so Drive never uploads half-finished files
  $tmp = Join-Path $env:TEMP "handball-dl"
  New-Item -ItemType Directory -Force -Path $tmp | Out-Null
  & yt-dlp --no-warnings @auth -f "bv*[height<=720][ext=mp4]+ba[ext=m4a]/bv*[height<=720]+ba/b[height<=720]" `
      --merge-output-format mp4 --write-info-json --no-write-playlist-metafiles --no-playlist `
      -o (Join-Path $tmp "$name.%(ext)s") $url
  $video = Join-Path $tmp "$name.mp4"
  if ($LASTEXITCODE -eq 0 -and (Test-Path $video)) {
    $info = Join-Path $tmp "$name.info.json"
    if (Test-Path $info) { Move-Item -Force $info (Join-Path $Out "$name.info.json") }
    Move-Item -Force $video (Join-Path $Out "$name.mp4")
    $ok++
  } else {
    Write-Warning "failed: $name"
    $failed += $name
  }
  Get-ChildItem $tmp -Filter "$name*" -ErrorAction SilentlyContinue | Remove-Item -Force
}
Write-Host "Fertig: $ok Spiele in $Out"
if ($failed.Count) { Write-Host "Nicht geklappt ($($failed.Count)):"; $failed | ForEach-Object { Write-Host "  $_" } }
