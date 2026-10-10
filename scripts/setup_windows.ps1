# One-time setup on Windows 10/11 (x86_64): Android SDK + emulator image + AVD,
# ffmpeg, JDK 17 and the `gui-agent` conda env. Windows counterpart of setup_mac.sh.
# Safe to re-run (skips what exists).
#
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
#
# Needs: winget, git, conda (Miniforge/Anaconda) on PATH. Downloads ~6-8 GB.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$Sdk = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA "Android\Sdk" }
$Image = "system-images;android-33;google_apis;x86_64"   # Pixel 6 / API 33, the image android_world documents
$Avd = "AndroidWorldAvd"
# Android command-line tools bootstrap (only used if the SDK has no cmdline-tools yet).
$CmdlineToolsZip = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"

foreach ($tool in "winget", "git", "conda") {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "$tool not found on PATH. See SETUP.md." }
}

Write-Host "==> winget packages (JDK 17, ffmpeg)"
function Install-WingetPackage($id) {
    winget list --id $id -e | Out-Null
    if ($LASTEXITCODE -ne 0) { winget install --id $id -e --accept-source-agreements --accept-package-agreements }
}
Install-WingetPackage "Microsoft.OpenJDK.17"
Install-WingetPackage "Gyan.FFmpeg"
$Jdk = Get-ChildItem "C:\Program Files\Microsoft" -Directory -Filter "jdk-17*" -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1
if ($Jdk) { $env:JAVA_HOME = $Jdk.FullName; $env:Path = "$($Jdk.FullName)\bin;$env:Path" }
if (-not (Get-Command java -ErrorAction SilentlyContinue)) { throw "java not found. Open a new terminal and re-run." }

Write-Host "==> Android SDK into $Sdk"
$SdkManager = Join-Path $Sdk "cmdline-tools\latest\bin\sdkmanager.bat"
if (-not (Test-Path $SdkManager)) {
    $tmp = Join-Path $env:TEMP "android-cmdline-tools"
    New-Item -ItemType Directory -Force $tmp | Out-Null
    Invoke-WebRequest $CmdlineToolsZip -OutFile "$tmp\tools.zip"
    Expand-Archive "$tmp\tools.zip" -DestinationPath $tmp -Force
    New-Item -ItemType Directory -Force (Join-Path $Sdk "cmdline-tools") | Out-Null
    Move-Item "$tmp\cmdline-tools" (Join-Path $Sdk "cmdline-tools\latest")
}
("y`n" * 30) | & $SdkManager --sdk_root="$Sdk" --licenses | Out-Null
& $SdkManager --sdk_root="$Sdk" "platform-tools" "emulator" "platforms;android-33" $Image
if ($LASTEXITCODE -ne 0) { throw "sdkmanager failed" }

Write-Host "==> AVD $Avd"
$Emulator = Join-Path $Sdk "emulator\emulator.exe"
if (-not ((& $Emulator -list-avds) -contains $Avd)) {
    "no" | & (Join-Path $Sdk "cmdline-tools\latest\bin\avdmanager.bat") create avd -n $Avd -k $Image -d pixel_6
}
# Without a hardware keyboard, `adb shell monkey` (used by AndroidWorld to launch apps)
# aborts with "SYS_KEYS has no physical keys" during --perform-emulator-setup.
$AvdConfig = Join-Path $env:USERPROFILE ".android\avd\$Avd.avd\config.ini"
if (Test-Path $AvdConfig) {
    $cfg = (Get-Content $AvdConfig) -replace '^hw\.keyboard=no$', 'hw.keyboard=yes'
    if (-not ($cfg -match '^hw\.keyboard=')) { $cfg += 'hw.keyboard=yes' }
    Set-Content -Path $AvdConfig -Value $cfg -Encoding ascii
}

Write-Host "==> Third-party code (android_world, gelab-zero)"
if (Test-Path .git) {
    git submodule update --init
    if ($LASTEXITCODE -ne 0) { throw "git submodule update failed" }
} else {
    # Unpacked from the ZIP (no .git): fetch the same upstream commits the submodules pin.
    function Get-PinnedRepo($dir, $url, $sha) {
        if ((Test-Path $dir) -and (Get-ChildItem $dir -Force | Select-Object -First 1)) { return }
        git init -q $dir
        git -C $dir fetch -q --depth 1 $url $sha
        if ($LASTEXITCODE -ne 0) { throw "could not fetch $url" }
        git -C $dir checkout -q FETCH_HEAD
    }
    Get-PinnedRepo "third_party\android_world" "https://github.com/google-research/android_world" "2dfc5ca3dc590efe9c72ce768f2b04182f2f75c7"
    Get-PinnedRepo "third_party\gelab-zero" "https://github.com/stepfun-ai/gelab-zero" "7b619f6f67d2b1101021fc453cb27bd48a29e4f2"
}

Write-Host "==> conda env 'gui-agent' (Python 3.11)"
if (conda env list | Select-String -Pattern '^gui-agent\s') {
    conda env update -n gui-agent -f environment.yml --prune
} else {
    conda env create -f environment.yml
}

if (-not (Test-Path .env)) { Copy-Item .env.example .env }

Write-Host @"

Done. Next (in a NEW terminal so PATH changes apply):
  conda activate gui-agent
  .\scripts\setup_model.ps1            # GELab-Zero into Ollama (once)
  .\scripts\start_emulator.ps1         # in its own terminal
  python scripts\check_setup.py

Emulator slow or won't start? Enable 'Windows Hypervisor Platform' (Windows Features), reboot.
"@
