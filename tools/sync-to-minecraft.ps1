<#
    Copies the packs into the Microsoft Store (UWP) Minecraft development
    folders.

    Why copy instead of symlink/junction? The UWP app runs in an AppContainer
    sandbox and can only read paths carrying an ACE for its package SID.
    Granting that on E:\ needs elevation, so a junction pointing off to E:\ is
    not reliably readable by the game. Files copied *into* LocalState inherit
    the correct ACL from the parent, so they always load.

    Re-run this after every edit to the packs, then fully exit the world (or
    the game) and re-enter. Script-only changes can use /reload instead.
#>
[CmdletBinding()]
param([switch]$NoTests)

$ErrorActionPreference = "Stop"

$source = Split-Path -Parent $PSScriptRoot

# Two possible data roots. The Store app's own LocalState is the documented one,
# but this machine actually reads from %APPDATA%\Minecraft Bedrock (left behind
# by a third-party launcher -- it is where the real worlds live). Sync to every
# root that exists so the packs are found regardless of which one the game uses.
$roots = @()
$uwp = Join-Path $env:LOCALAPPDATA "Packages\Microsoft.MinecraftUWP_8wekyb3d8bbwe\LocalState\games\com.mojang"
if (Test-Path $uwp) { $roots += $uwp }
$shared = Join-Path $env:APPDATA "Minecraft Bedrock\Users\Shared\games\com.mojang"
if (Test-Path $shared) { $roots += $shared }

if (-not $roots) { throw "No Minecraft data folder found." }

if (Get-Process -Name "Minecraft.Windows" -ErrorAction SilentlyContinue) {
    Write-Warning "Minecraft is running. The copy will succeed, but you must fully exit the world and re-enter for changes to take effect."
}

$packs = @(
    @{ Name = "UnicornAddon_BP";     Dest = "development_behavior_packs" },
    @{ Name = "UnicornAddon_RP";     Dest = "development_resource_packs" },
    @{ Name = "UnicornAddon_TestBP"; Dest = "development_behavior_packs"; Test = $true }
)

foreach ($root in $roots) {
    Write-Host "$root" -ForegroundColor Cyan

    foreach ($p in $packs) {
        if ($p.Test -and $NoTests) {
            Write-Host "  skipped $($p.Name)" -ForegroundColor DarkGray
            continue
        }

        $src = Join-Path $source $p.Name
        if (-not (Test-Path $src)) { Write-Warning "missing source: $src"; continue }

        $destDir = Join-Path $root $p.Dest
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }

        $dest = Join-Path $destDir $p.Name

        # A pre-existing junction must be removed with rmdir, not Remove-Item,
        # or we would delete through it into the real project folder.
        if (Test-Path $dest) {
            $item = Get-Item $dest -Force
            if ($item.Attributes -match "ReparsePoint") {
                cmd /c rmdir "`"$dest`"" | Out-Null
                Write-Host "  removed old junction $($p.Name)" -ForegroundColor DarkGray
            } else {
                Remove-Item $dest -Recurse -Force
            }
        }

        Copy-Item $src $dest -Recurse -Force
        $n = @(Get-ChildItem $dest -Recurse -File).Count
        Write-Host ("  synced {0,-22} {1} files" -f $p.Name, $n) -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Done. In Minecraft these appear under the world's Behavior/Resource Pack lists." -ForegroundColor Green
