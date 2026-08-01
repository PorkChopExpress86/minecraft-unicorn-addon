<#
    Activates the Ride a Unicorn packs in an existing Minecraft Bedrock world so
    the world opens with them already switched on -- no fiddling with the
    in-game pack menus.

    Usage:
        .\tools\activate-in-world.ps1                 # list worlds, activate in the newest
        .\tools\activate-in-world.ps1 -List           # just show the worlds
        .\tools\activate-in-world.ps1 -WorldPath "..." # target a specific world folder
        .\tools\activate-in-world.ps1 -NoTests        # skip the dev test pack

    Existing world_*_packs.json files are backed up to *.bak-<timestamp> and the
    pack entries are MERGED, so packs you already had active stay active.

    Minecraft must be closed when you run this -- it rewrites world files.
#>
[CmdletBinding()]
param(
    [string]$WorldPath,
    [switch]$List,
    [switch]$NoTests
)

$ErrorActionPreference = "Stop"

# Read pack identity straight from the manifests rather than duplicating it
# here -- a world entry whose version doesn't match the installed pack won't
# resolve, and hardcoding it means every version bump silently breaks this
# script until someone notices.
$repoRoot = Split-Path -Parent $PSScriptRoot

function Get-PackIdentity {
    param([string]$PackDir)
    $manifestPath = Join-Path $repoRoot "$PackDir\manifest.json"
    if (-not (Test-Path $manifestPath)) { throw "manifest not found: $manifestPath" }
    $m = Get-Content $manifestPath -Raw | ConvertFrom-Json
    [pscustomobject]@{ Uuid = $m.header.uuid; Version = @($m.header.version) }
}

$rp   = Get-PackIdentity "UnicornAddon_RP"
$bp   = Get-PackIdentity "UnicornAddon_BP"
$test = Get-PackIdentity "UnicornAddon_TestBP"

function Get-WorldRoots {
    $roots = @()
    $uwp = Join-Path $env:LOCALAPPDATA "Packages\Microsoft.MinecraftUWP_8wekyb3d8bbwe\LocalState\games\com.mojang\minecraftWorlds"
    if (Test-Path $uwp) { $roots += $uwp }
    $standalone = Join-Path $env:APPDATA "Minecraft Bedrock\Users"
    if (Test-Path $standalone) {
        foreach ($profile in Get-ChildItem $standalone -Directory) {
            $p = Join-Path $profile.FullName "games\com.mojang\minecraftWorlds"
            if (Test-Path $p) { $roots += $p }
        }
    }
    return $roots
}

function Get-Worlds {
    foreach ($root in Get-WorldRoots) {
        foreach ($dir in Get-ChildItem $root -Directory -ErrorAction SilentlyContinue) {
            $nameFile = Join-Path $dir.FullName "levelname.txt"
            $name = if (Test-Path $nameFile) { (Get-Content $nameFile -Raw).Trim() } else { "(unnamed)" }
            [pscustomobject]@{
                Name     = $name
                Path     = $dir.FullName
                Modified = $dir.LastWriteTime
            }
        }
    }
}

function Merge-PackList {
    param([string]$File, [object[]]$Packs)

    $entries = @()
    if (Test-Path $File) {
        $backup = "$File.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item $File $backup
        Write-Host "    backed up -> $(Split-Path $backup -Leaf)" -ForegroundColor DarkGray
        $raw = (Get-Content $File -Raw).Trim()
        if ($raw) {
            $parsed = $raw | ConvertFrom-Json
            if ($null -ne $parsed) { $entries = @($parsed) }
        }
    }

    $added = 0
    foreach ($p in $Packs) {
        # Drop any stale entry for this pack so a version bump replaces it
        # rather than leaving an unresolvable old version behind.
        $existing = $entries | Where-Object { $_.pack_id -eq $p.Uuid }
        if ($existing) {
            $entries = @($entries | Where-Object { $_.pack_id -ne $p.Uuid })
        }
        $entries += [pscustomobject]@{ pack_id = $p.Uuid; version = $p.Version }
        if (-not $existing) { $added++ }
    }

    # ConvertTo-Json collapses a single-element array to an object, so force brackets.
    $json = ConvertTo-Json -InputObject @($entries) -Depth 6
    if ($json -notmatch '^\s*\[') { $json = "[$json]" }
    Set-Content -Path $File -Value $json -Encoding utf8

    return $added
}

$worlds = @(Get-Worlds | Sort-Object Modified -Descending)

if (-not $worlds) {
    Write-Warning "No Minecraft worlds found. Create a world in-game first, then re-run."
    return
}

Write-Host ""
Write-Host "Worlds found:" -ForegroundColor Cyan
for ($i = 0; $i -lt $worlds.Count; $i++) {
    Write-Host ("  [{0}] {1,-24} {2}" -f $i, $worlds[$i].Name, $worlds[$i].Modified)
    Write-Host ("      {0}" -f $worlds[$i].Path) -ForegroundColor DarkGray
}
Write-Host ""

if ($List) { return }

if ($WorldPath) {
    if (-not (Test-Path $WorldPath)) { throw "World folder not found: $WorldPath" }
    $target = $WorldPath
} else {
    $target = $worlds[0].Path
    Write-Host "Targeting most recently played world: $($worlds[0].Name)" -ForegroundColor Yellow
}

$mcRunning = Get-Process -Name "Minecraft.Windows" -ErrorAction SilentlyContinue
if ($mcRunning) {
    Write-Warning "Minecraft appears to be running. Close it fully, then re-run -- otherwise it will overwrite these changes on exit."
    return
}

$bpPacks = if ($NoTests) { @($bp) } else { @($bp, $test) }

Write-Host "  behavior packs:" -ForegroundColor Cyan
$a = Merge-PackList -File (Join-Path $target "world_behavior_packs.json") -Packs $bpPacks
Write-Host "    $a added" -ForegroundColor Green

Write-Host "  resource packs:" -ForegroundColor Cyan
$b = Merge-PackList -File (Join-Path $target "world_resource_packs.json") -Packs @($rp)
Write-Host "    $b added" -ForegroundColor Green

Write-Host ""
Write-Host "Done. Open that world -- the packs load automatically and the self-test runs a few seconds after you spawn." -ForegroundColor Green
if (-not $NoTests) {
    Write-Host "Re-run the tests any time in chat with:  /scriptevent unicorn:test" -ForegroundColor DarkGray
}
