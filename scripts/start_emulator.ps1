# Start the AndroidWorld emulator on Windows. Keep this terminal open while running tasks.
#   .\scripts\start_emulator.ps1              # with window
#   .\scripts\start_emulator.ps1 -no-window   # headless
# -grpc 8554 is required by AndroidWorld (accessibility forwarding).
$Sdk = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { Join-Path $env:LOCALAPPDATA "Android\Sdk" }
& (Join-Path $Sdk "emulator\emulator.exe") -avd AndroidWorldAvd -no-snapshot -grpc 8554 @args
