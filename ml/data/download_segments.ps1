# Downloads five 3-minute pieces (at 15/30/50/70/85 % of each game) in 720p plus the video
# information (title, description, chapters) for every row of videos.csv.
# Needs yt-dlp and ffmpeg:   winget install yt-dlp.yt-dlp   and   winget install Gyan.FFmpeg
# Run in PowerShell in this folder:   .\download_segments.ps1
# Optional: -Out "G:\Meine Ablage\handball-videos"  (a Google Drive for desktop folder uploads by itself)
param([string]$Csv = "videos.csv", [string]$Out = "handball-videos", [int]$Pieces = 5, [int]$Seconds = 180)
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$rows = Import-Csv -Path $Csv -Delimiter ';'
$i = 0
foreach ($r in $rows) {
  $i++
  $name = $r.name; $url = $r.url
  if (-not $url) { continue }
  if (Test-Path (Join-Path $Out "$name.done")) { Write-Host "[$i/$($rows.Count)] $name already done"; continue }
  Write-Host "[$i/$($rows.Count)] $name"
  $dur = & yt-dlp --no-warnings --print duration $url 2>$null
  if (-not $dur) { Write-Warning "no duration for $name (private or removed?)"; continue }
  $dur = [double]$dur
  $sections = @()
  foreach ($f in @(0.15, 0.30, 0.50, 0.70, 0.85)[0..($Pieces - 1)]) {
    $a = [math]::Floor($dur * $f); $b = [math]::Min($dur, $a + $Seconds)
    $sections += @("--download-sections", "*$a-$b")
  }
  & yt-dlp --no-warnings -f "bv*[height<=720]+ba/b[height<=720]" --merge-output-format mp4 `
      --write-info-json --no-write-playlist-metafiles @sections `
      -o (Join-Path $Out "$name.%(section_start)s.%(ext)s") $url
  if ($LASTEXITCODE -eq 0) { New-Item -ItemType File -Path (Join-Path $Out "$name.done") | Out-Null }
}
Write-Host "Fertig. Ordner: $Out"
