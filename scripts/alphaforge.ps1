# AlphaForge's interactive Windows project manager.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve every project path from this script, not from the caller's location.
$script:ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$script:VenvPath = Join-Path $script:ProjectRoot ".venv"
$script:VenvPython = Join-Path $script:VenvPath "Scripts\python.exe"
$script:EnvPath = Join-Path $script:ProjectRoot ".env"
$script:EnvironmentDefaults = @(
    "OLLAMA_BASE_URL=http://localhost:11434"
    "OLLAMA_PRIMARY_MODEL=phi3"
    "OLLAMA_FALLBACK_MODEL=mistral"
    "OLLAMA_TIMEOUT_SECONDS=25"
    "ALPHAFORGE_DB_PATH=data/alphaforge.db"
)

# Consistent user-facing messages.
function Write-Success { param([string]$Message) Write-Host "[SUCCESS] $Message" -ForegroundColor Green }
function Write-WarningMessage { param([string]$Message) Write-Host "[WARNING] $Message" -ForegroundColor Yellow }
function Write-ErrorMessage { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

function Pause-ForUser {
    Write-Host ""
    [void](Read-Host "Press Enter to return to the menu")
}

# Run a native program without hiding its output or exit code.
function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$Description = "Command"
    )

    & $FilePath @Arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "$Description failed with exit code $exitCode."
    }
}

# Find a working Python 3 interpreter in the requested preference order.
function Get-ProjectPython {
    $candidates = @(
        @{ Name = "py"; Arguments = @("-3") },
        @{ Name = "python"; Arguments = @() },
        @{ Name = "python3"; Arguments = @() }
    )

    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate.Name -ErrorAction SilentlyContinue
        if ($null -eq $command) { continue }

        try {
            $versionArguments = @($candidate.Arguments) + @("--version")
            $version = (& $command.Source @versionArguments 2>&1 | Out-String).Trim()
            if (($LASTEXITCODE -eq 0) -and ($version -match "Python 3\.")) {
                return [PSCustomObject]@{
                    FilePath = $command.Source
                    Arguments = [string[]]$candidate.Arguments
                    DisplayName = $candidate.Name
                    Version = $version
                }
            }
        }
        catch {
            Write-WarningMessage "Could not use $($candidate.Name): $($_.Exception.Message)"
        }
    }

    return $null
}

function Test-VirtualEnvironment {
    return (Test-Path -LiteralPath $script:VenvPython -PathType Leaf)
}

function New-VirtualEnvironment {
    if (Test-Path -LiteralPath $script:VenvPath) {
        if (Test-VirtualEnvironment) {
            Write-WarningMessage "The virtual environment already exists at '$script:VenvPath'. It was not overwritten."
        }
        else {
            Write-ErrorMessage "'$script:VenvPath' exists but does not contain Scripts\python.exe. Use Rebuild virtual environment to replace it safely."
        }
        return $false
    }

    $python = Get-ProjectPython
    if ($null -eq $python) {
        Write-ErrorMessage "Python 3 was not found. Install Python 3, then try again."
        return $false
    }

    Write-Host "Using $($python.DisplayName): $($python.Version)"
    try {
        $arguments = @($python.Arguments) + @("-m", "venv", $script:VenvPath)
        Invoke-NativeCommand -FilePath $python.FilePath -Arguments $arguments -Description "Virtual environment creation"
        if (-not (Test-VirtualEnvironment)) {
            throw "Creation completed without producing '$script:VenvPython'."
        }
        Write-Success "Created the virtual environment at '$script:VenvPath'."
        return $true
    }
    catch {
        Write-ErrorMessage $_.Exception.Message
        return $false
    }
}

function Assert-VirtualEnvironment {
    if (-not (Test-VirtualEnvironment)) {
        Write-ErrorMessage "The virtual environment is missing. Select 'Create virtual environment' first."
        return $false
    }
    return $true
}

function Update-PipTools {
    if (-not (Assert-VirtualEnvironment)) { return $false }
    try {
        Invoke-NativeCommand -FilePath $script:VenvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel") -Description "Packaging-tool upgrade"
        Write-Success "Upgraded pip, setuptools, and wheel."
        return $true
    }
    catch {
        Write-ErrorMessage $_.Exception.Message
        return $false
    }
}

function Install-AppDependencies {
    if (-not (Assert-VirtualEnvironment)) { return $false }
    $requirements = Join-Path $script:ProjectRoot "requirements.txt"
    if (-not (Test-Path -LiteralPath $requirements -PathType Leaf)) {
        Write-ErrorMessage "requirements.txt was not found."
        return $false
    }
    if (-not (Update-PipTools)) { return $false }
    try {
        Invoke-NativeCommand -FilePath $script:VenvPython -Arguments @("-m", "pip", "install", "-r", $requirements) -Description "Application dependency installation"
        Write-Success "Installed application dependencies."
        return $true
    }
    catch {
        Write-ErrorMessage $_.Exception.Message
        return $false
    }
}

function Install-DevDependencies {
    if (-not (Assert-VirtualEnvironment)) { return $false }
    $requirements = Join-Path $script:ProjectRoot "requirements-dev.txt"
    if (-not (Test-Path -LiteralPath $requirements -PathType Leaf)) {
        Write-ErrorMessage "requirements-dev.txt was not found."
        return $false
    }
    try {
        Invoke-NativeCommand -FilePath $script:VenvPython -Arguments @("-m", "pip", "install", "-r", $requirements) -Description "Development dependency installation"
        Write-Success "Installed development dependencies."
        return $true
    }
    catch {
        Write-ErrorMessage $_.Exception.Message
        return $false
    }
}

# Create safe default configuration without displaying existing secrets.
function Write-DefaultEnvironmentFile {
    $script:EnvironmentDefaults | Set-Content -LiteralPath $script:EnvPath -Encoding UTF8
}

function Initialize-EnvironmentFile {
    try {
        if (-not (Test-Path -LiteralPath $script:EnvPath)) {
            Write-DefaultEnvironmentFile
            Write-Success "Created .env with local defaults."
            return $true
        }

        Write-WarningMessage ".env already exists. Its contents will not be displayed or overwritten automatically."
        Write-Host "1. Keep existing file"
        Write-Host "2. Open it in Notepad"
        Write-Host "3. Recreate it using defaults"
        Write-Host "0. Cancel"
        $choice = Read-Host "Select an option"
        switch ($choice) {
            "1" { Write-Success "Kept the existing .env file."; return $true }
            "2" {
                $notepad = Get-Command notepad.exe -ErrorAction SilentlyContinue
                if ($null -eq $notepad) { throw "Notepad was not found." }
                Start-Process -FilePath $notepad.Source -ArgumentList @($script:EnvPath)
                Write-Success "Opened .env in Notepad."
                return $true
            }
            "3" {
                $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
                $backup = Join-Path $script:ProjectRoot ".env.backup-$stamp"
                Copy-Item -LiteralPath $script:EnvPath -Destination $backup
                Write-DefaultEnvironmentFile
                Write-Success "Recreated .env and saved the previous file as '$(Split-Path $backup -Leaf)'."
                return $true
            }
            "0" { Write-WarningMessage "Environment configuration was cancelled."; return $false }
            default { Write-WarningMessage "Invalid selection; no changes were made."; return $false }
        }
    }
    catch {
        Write-ErrorMessage "Could not configure .env: $($_.Exception.Message)"
        return $false
    }
}

# Ollama installation, process, and local-port helpers.
function Get-OllamaCommand {
    return (Get-Command ollama -ErrorAction SilentlyContinue)
}

function Test-OllamaInstalled {
    return ($null -ne (Get-OllamaCommand))
}

function Test-OllamaPort {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $result = $client.BeginConnect("127.0.0.1", 11434, $null, $null)
        if (-not $result.AsyncWaitHandle.WaitOne(1500, $false)) { return $false }
        $client.EndConnect($result)
        return $true
    }
    catch { return $false }
    finally { $client.Close() }
}

function Test-OllamaRunning {
    $process = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    return (($null -ne $process) -or (Test-OllamaPort))
}

function Install-OllamaWithPrompt {
    if (Test-OllamaInstalled) { return $true }
    Write-WarningMessage "Ollama is not installed. Download it manually from https://ollama.com/download/windows."
    $answer = Read-Host "Install Ollama with winget now? (y/N)"
    if ($answer -notmatch "^(y|yes)$") {
        Write-WarningMessage "Ollama installation was skipped."
        return $false
    }
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($null -eq $winget) {
        Write-ErrorMessage "winget is unavailable. Install Ollama manually."
        return $false
    }
    try {
        Invoke-NativeCommand -FilePath $winget.Source -Arguments @("install", "-e", "--id", "Ollama.Ollama", "--accept-package-agreements", "--accept-source-agreements") -Description "Ollama installation"
        Write-Success "winget completed the Ollama installation. Reopen PowerShell if the ollama command is not yet available."
        return (Test-OllamaInstalled)
    }
    catch {
        Write-ErrorMessage $_.Exception.Message
        return $false
    }
}

function Show-OllamaInstallation {
    $ollama = Get-OllamaCommand
    if ($null -eq $ollama) {
        [void](Install-OllamaWithPrompt)
        return
    }
    Write-Success "Ollama is installed at '$($ollama.Source)'."
    try {
        & $ollama.Source --version
        if ($LASTEXITCODE -ne 0) { Write-WarningMessage "Ollama did not return a version successfully (exit code $LASTEXITCODE)." }
    }
    catch { Write-WarningMessage "Could not read the Ollama version: $($_.Exception.Message)" }
}

function Start-OllamaServer {
    $ollama = Get-OllamaCommand
    if ($null -eq $ollama) {
        Write-ErrorMessage "Ollama is not installed. Use 'Check Ollama installation' first."
        return $false
    }
    if (Test-OllamaRunning) {
        Write-Success "Ollama already appears to be running; no duplicate process was started."
        return $true
    }
    try {
        Write-Host "Starting Ollama in a hidden background window..."
        Start-Process -FilePath $ollama.Source -ArgumentList @("serve") -WindowStyle Hidden
        Start-Sleep -Seconds 3
        if (Test-OllamaPort) {
            Write-Success "Ollama is reachable on localhost port 11434."
            return $true
        }
        Write-ErrorMessage "Ollama was started, but port 11434 is not reachable. Check the Ollama logs or application."
        return $false
    }
    catch {
        Write-ErrorMessage "Could not start Ollama: $($_.Exception.Message)"
        return $false
    }
}

function Pull-OllamaModel {
    param([Parameter(Mandatory = $true)][string]$Model)
    $ollama = Get-OllamaCommand
    if ($null -eq $ollama) { Write-ErrorMessage "Ollama is not installed."; return $false }
    try {
        Invoke-NativeCommand -FilePath $ollama.Source -Arguments @("pull", $Model) -Description "Downloading Ollama model '$Model'"
        Write-Success "Downloaded Ollama model '$Model'."
        return $true
    }
    catch { Write-ErrorMessage $_.Exception.Message; return $false }
}

function Install-OllamaModels {
    if (-not (Test-OllamaInstalled)) { Write-ErrorMessage "Ollama is not installed."; return $false }
    if (-not (Start-OllamaServer)) { return $false }
    Write-Host "1. Pull primary model: phi3"
    Write-Host "2. Pull fallback model: mistral"
    Write-Host "3. Pull both models"
    Write-Host "0. Cancel"
    $choice = Read-Host "Select an option"
    switch ($choice) {
        "1" { return (Pull-OllamaModel -Model "phi3") }
        "2" { return (Pull-OllamaModel -Model "mistral") }
        "3" {
            $primary = Pull-OllamaModel -Model "phi3"
            $fallback = Pull-OllamaModel -Model "mistral"
            return ($primary -and $fallback)
        }
        "0" { Write-WarningMessage "Model download was cancelled."; return $false }
        default { Write-WarningMessage "Invalid selection; no models were downloaded."; return $false }
    }
}

# Project validation and runtime actions.
function Invoke-ProjectTests {
    if (-not (Assert-VirtualEnvironment)) { return $false }
    try {
        & $script:VenvPython -m pytest
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) { throw "pytest failed with exit code $exitCode." }
        Write-Success "All tests passed (exit code 0)."
        return $true
    }
    catch { Write-ErrorMessage $_.Exception.Message; return $false }
}

function Invoke-CompileCheck {
    if (-not (Assert-VirtualEnvironment)) { return $false }
    try {
        & $script:VenvPython -m compileall "alphaforge" "app.py"
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) { throw "compileall failed with exit code $exitCode." }
        Write-Success "Python compilation check passed (exit code 0)."
        return $true
    }
    catch { Write-ErrorMessage $_.Exception.Message; return $false }
}

function Start-AlphaForge {
    if (-not (Assert-VirtualEnvironment)) { return $false }
    $app = Join-Path $script:ProjectRoot "app.py"
    if (-not (Test-Path -LiteralPath $app -PathType Leaf)) { Write-ErrorMessage "app.py was not found."; return $false }
    Write-Host "AlphaForge should be available at http://127.0.0.1:8080" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop the server and return to this manager."
    try {
        & $script:VenvPython $app
        $exitCode = $LASTEXITCODE
        if (($exitCode -ne 0) -and ($exitCode -ne 130)) { throw "AlphaForge stopped with exit code $exitCode." }
        Write-Success "AlphaForge server stopped."
        return $true
    }
    catch { Write-ErrorMessage $_.Exception.Message; return $false }
}

function Rebuild-VirtualEnvironment {
    Write-WarningMessage "This will permanently delete and recreate '$script:VenvPath'."
    $confirmation = Read-Host "Type REBUILD to continue"
    if ($confirmation -cne "REBUILD") { Write-WarningMessage "Rebuild cancelled; no files were deleted."; return $false }

    $expected = [System.IO.Path]::GetFullPath((Join-Path $script:ProjectRoot ".venv")).TrimEnd('\')
    $actual = [System.IO.Path]::GetFullPath($script:VenvPath).TrimEnd('\')
    if ($actual -cne $expected) { Write-ErrorMessage "Safety check failed: virtual-environment path is not the project-root .venv."; return $false }
    try {
        if (Test-Path -LiteralPath $actual) { Remove-Item -LiteralPath $actual -Recurse -Force }
    }
    catch { Write-ErrorMessage "Could not remove .venv: $($_.Exception.Message)"; return $false }

    if (-not (New-VirtualEnvironment)) { return $false }
    if (-not (Update-PipTools)) { return $false }
    if (-not (Install-DevDependencies)) { return $false }
    Write-Success "The virtual environment was rebuilt successfully."
    return $true
}

function Disable-ProjectVirtualEnvironment {
    if (-not (Test-Path Env:VIRTUAL_ENV)) {
        Write-WarningMessage "No activated virtual environment was detected. The manager already uses .venv directly without activation."
        return $true
    }

    $activePath = [System.IO.Path]::GetFullPath((Get-Item Env:VIRTUAL_ENV).Value).TrimEnd('\', '/')
    $projectVenvPath = [System.IO.Path]::GetFullPath($script:VenvPath).TrimEnd('\', '/')
    if ($activePath -ine $projectVenvPath) {
        Write-WarningMessage "A different virtual environment is active at '$activePath'. It was not changed."
        return $false
    }

    try {
        # Python's activation script saves the original PATH here. Restore it when available.
        if (Test-Path Env:_OLD_VIRTUAL_PATH) {
            $env:PATH = (Get-Item Env:_OLD_VIRTUAL_PATH).Value
            Remove-Item Env:_OLD_VIRTUAL_PATH
        }
        else {
            # Fall back to removing only this project's Scripts directory from PATH.
            $venvScripts = [System.IO.Path]::GetFullPath((Join-Path $script:VenvPath "Scripts")).TrimEnd('\', '/')
            $pathParts = @($env:PATH -split [System.IO.Path]::PathSeparator | Where-Object {
                -not [string]::IsNullOrWhiteSpace($_) -and
                ([System.IO.Path]::GetFullPath($_).TrimEnd('\', '/') -ine $venvScripts)
            })
            $env:PATH = $pathParts -join [System.IO.Path]::PathSeparator
        }

        Remove-Item Env:VIRTUAL_ENV
        if (Test-Path Env:VIRTUAL_ENV_PROMPT) { Remove-Item Env:VIRTUAL_ENV_PROMPT }
        Write-Success "Deactivated the AlphaForge virtual environment for this PowerShell session."
        return $true
    }
    catch {
        Write-ErrorMessage "Could not deactivate the virtual environment: $($_.Exception.Message)"
        return $false
    }
}

function Remove-ProjectVirtualEnvironment {
    if (-not (Test-Path -LiteralPath $script:VenvPath)) {
        Write-WarningMessage "The project virtual environment does not exist. Nothing was deleted."
        return $true
    }

    $expected = [System.IO.Path]::GetFullPath((Join-Path $script:ProjectRoot ".venv")).TrimEnd('\', '/')
    $actual = [System.IO.Path]::GetFullPath($script:VenvPath).TrimEnd('\', '/')
    if ($actual -ine $expected) {
        Write-ErrorMessage "Safety check failed: the deletion target is not the project-root .venv directory."
        return $false
    }

    Write-WarningMessage "This permanently deletes only '$actual'. Project source, .env, and data will be preserved."
    $confirmation = Read-Host "Type DELETE to remove .venv"
    if ($confirmation -cne "DELETE") {
        Write-WarningMessage "Deletion cancelled; no files were removed."
        return $false
    }

    if (Test-Path Env:VIRTUAL_ENV) {
        $activePath = [System.IO.Path]::GetFullPath((Get-Item Env:VIRTUAL_ENV).Value).TrimEnd('\', '/')
        if ($activePath -ieq $actual) {
            if (-not (Disable-ProjectVirtualEnvironment)) { return $false }
        }
    }

    try {
        Remove-Item -LiteralPath $actual -Recurse -Force
        if (Test-Path -LiteralPath $actual) { throw "The directory still exists after the removal command." }
        Write-Success "Deleted the AlphaForge virtual environment. Select option 2 or 12 to create it again."
        return $true
    }
    catch {
        Write-ErrorMessage "Could not delete .venv: $($_.Exception.Message)"
        return $false
    }
}

function Manage-VirtualEnvironment {
    Write-Host "1. Deactivate the AlphaForge virtual environment in this PowerShell session"
    Write-Host "2. Permanently delete the project .venv directory"
    Write-Host "0. Cancel"
    $choice = Read-Host "Select an option"
    switch ($choice) {
        "1" { return (Disable-ProjectVirtualEnvironment) }
        "2" { return (Remove-ProjectVirtualEnvironment) }
        "0" { Write-WarningMessage "Virtual-environment management was cancelled."; return $false }
        default { Write-WarningMessage "Enter 0, 1, or 2."; return $false }
    }
}

function Show-ProjectStatus {
    Write-Host "Project root: $script:ProjectRoot"
    $python = Get-ProjectPython
    if ($null -eq $python) { Write-Host "System Python: Not found" -ForegroundColor Red }
    else { Write-Host "System Python: $($python.DisplayName) ($($python.Version))" }

    $venvExists = Test-VirtualEnvironment
    Write-Host "Virtual environment: $venvExists"
    if ($venvExists) {
        try {
            $venvVersion = (& $script:VenvPython --version 2>&1 | Out-String).Trim()
            Write-Host "Virtual-environment Python: $venvVersion"
        }
        catch { Write-WarningMessage "Could not read virtual-environment Python version." }
    }
    Write-Host "requirements.txt exists: $(Test-Path -LiteralPath (Join-Path $script:ProjectRoot 'requirements.txt'))"
    Write-Host "requirements-dev.txt exists: $(Test-Path -LiteralPath (Join-Path $script:ProjectRoot 'requirements-dev.txt'))"
    Write-Host ".env exists: $(Test-Path -LiteralPath $script:EnvPath) (contents hidden)"
    Write-Host "Ollama installed: $(Test-OllamaInstalled)"
    Write-Host "Ollama running: $(Test-OllamaRunning)"
    Write-Host "app.py exists: $(Test-Path -LiteralPath (Join-Path $script:ProjectRoot 'app.py'))"

    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($null -eq $git) { Write-Host "Git: Not installed" }
    else {
        try {
            $branch = (& $git.Source -C $script:ProjectRoot branch --show-current 2>$null | Out-String).Trim()
            if ([string]::IsNullOrWhiteSpace($branch)) { $branch = "detached HEAD or unavailable" }
            $changes = (& $git.Source -C $script:ProjectRoot status --porcelain 2>$null | Out-String).Trim()
            Write-Host "Git branch: $branch"
            Write-Host "Git working tree has uncommitted changes: $(-not [string]::IsNullOrWhiteSpace($changes))"
        }
        catch { Write-WarningMessage "Git is installed, but repository status could not be read." }
    }
}

function Invoke-FullSetup {
    $summary = New-Object System.Collections.Generic.List[string]
    Write-Host "Starting first-time setup..." -ForegroundColor Cyan
    $python = Get-ProjectPython
    if ($null -eq $python) { Write-ErrorMessage "Python 3 is required."; return $false }
    $summary.Add("Python: $($python.Version)")

    if (-not (Test-VirtualEnvironment)) {
        if (-not (New-VirtualEnvironment)) { $summary.Add("Virtual environment: FAILED"); Show-SetupSummary $summary; return $false }
    }
    $summary.Add("Virtual environment: ready")
    if (-not (Update-PipTools)) { $summary.Add("Packaging tools: FAILED"); Show-SetupSummary $summary; return $false }
    $summary.Add("Packaging tools: updated")
    if (-not (Install-DevDependencies)) { $summary.Add("Dependencies: FAILED"); Show-SetupSummary $summary; return $false }
    $summary.Add("Dependencies: installed")

    if (-not (Test-Path -LiteralPath $script:EnvPath)) { Write-DefaultEnvironmentFile; $summary.Add(".env: created") }
    else { $summary.Add(".env: kept existing file") }

    if (-not (Test-OllamaInstalled)) { [void](Install-OllamaWithPrompt) }
    if (Test-OllamaInstalled) {
        $started = Start-OllamaServer
        $summary.Add("Ollama: installed; running=$started")
        $models = Read-Host "Download recommended phi3 and mistral models? (y/N)"
        if ($models -match "^(y|yes)$") {
            $primary = Pull-OllamaModel -Model "phi3"
            $fallback = Pull-OllamaModel -Model "mistral"
            $summary.Add("Ollama models: phi3=$primary, mistral=$fallback")
        }
        else { $summary.Add("Ollama models: skipped") }
    }
    else { $summary.Add("Ollama: unavailable (optional AI features disabled)") }

    $tests = Invoke-ProjectTests
    $compile = Invoke-CompileCheck
    $summary.Add("Tests passed: $tests")
    $summary.Add("Compile check passed: $compile")
    Show-SetupSummary $summary
    $launch = Read-Host "Launch AlphaForge now? (y/N)"
    if ($launch -match "^(y|yes)$") { [void](Start-AlphaForge) }
    return ($tests -and $compile)
}

function Show-SetupSummary {
    param([System.Collections.Generic.List[string]]$Items)
    Write-Host ""
    Write-Host "First-time setup summary" -ForegroundColor Cyan
    Write-Host "------------------------"
    foreach ($item in $Items) { Write-Host "- $item" }
}

# Menu rendering is kept separate from action dispatch for readability.
function Show-MainMenu {
    Clear-Host
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "         AlphaForge Manager" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Show project status"
    Write-Host "2. Create virtual environment"
    Write-Host "3. Install application dependencies"
    Write-Host "4. Install development dependencies"
    Write-Host "5. Create or update .env configuration"
    Write-Host "6. Check Ollama installation"
    Write-Host "7. Start Ollama"
    Write-Host "8. Download recommended Ollama models"
    Write-Host "9. Run tests"
    Write-Host "10. Compile-check Python files"
    Write-Host "11. Run AlphaForge"
    Write-Host "12. Complete first-time setup"
    Write-Host "13. Rebuild virtual environment"
    Write-Host "14. Deactivate or delete virtual environment"
    Write-Host "0. Exit"
    Write-Host ""
}

# Always restore the directory from which the user launched the manager.
$previousLocation = Get-Location
try {
    Set-Location -LiteralPath $script:ProjectRoot
    $exitRequested = $false
    while (-not $exitRequested) {
        Show-MainMenu
        $choice = Read-Host "Select an option"
        $pause = $true
        try {
            switch ($choice) {
                "1" { Show-ProjectStatus }
                "2" { [void](New-VirtualEnvironment) }
                "3" { [void](Install-AppDependencies) }
                "4" { [void](Install-DevDependencies) }
                "5" { [void](Initialize-EnvironmentFile) }
                "6" { Show-OllamaInstallation }
                "7" { [void](Start-OllamaServer) }
                "8" { [void](Install-OllamaModels) }
                "9" { [void](Invoke-ProjectTests) }
                "10" { [void](Invoke-CompileCheck) }
                "11" { [void](Start-AlphaForge) }
                "12" { [void](Invoke-FullSetup) }
                "13" { [void](Rebuild-VirtualEnvironment) }
                "14" { [void](Manage-VirtualEnvironment) }
                "0" { $exitRequested = $true; $pause = $false }
                default { Write-WarningMessage "Enter a number from 0 through 14." }
            }
        }
        catch { Write-ErrorMessage "The operation failed: $($_.Exception.Message)" }
        if ($pause) { Pause-ForUser }
    }
}
finally {
    Set-Location -LiteralPath $previousLocation
}
