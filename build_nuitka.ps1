$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MoB_KML Web Edition - Build with Nuitka" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Ensure venv is activated
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Install ALL required packages (app + build dependencies)
Write-Host "`nInstalling/updating all dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade -r requirements.txt
python -m pip install --upgrade nuitka zstandard ordered-set

# Clean previous builds
Write-Host "`nCleaning previous builds..." -ForegroundColor Yellow
if (Test-Path ".\dist") {
    cmd /c "rmdir /s /q .\dist 2>nul || taskkill /f /im python.exe 2>nul & rmdir /s /q .\dist"
    Write-Host "Removed ./dist" -ForegroundColor Green
}
if (Test-Path ".\build") {
    cmd /c "rmdir /s /q .\build 2>nul || taskkill /f /im python.exe 2>nul & rmdir /s /q .\build"
    Write-Host "Removed ./build" -ForegroundColor Green
}
if (Test-Path ".\launcher.py") {
    Remove-Item ".\launcher.py" -Force -ErrorAction SilentlyContinue
    Write-Host "Removed ./launcher.py" -ForegroundColor Green
}

# Ensure profiles dir exists with at least a placeholder
if (-not (Test-Path ".\profiles")) {
    New-Item -ItemType Directory -Path ".\profiles" | Out-Null
}
if (-not (Test-Path ".\profiles\.gitkeep")) {
    "" | Out-File -FilePath ".\profiles\.gitkeep" -Encoding ASCII
}

# Create launcher script (write as ASCII to avoid BOM issues)
Write-Host "`nCreating launcher script..." -ForegroundColor Yellow
$launcher = @"
import os
import sys
import webbrowser
import time
import traceback
from threading import Thread

def open_browser():
    time.sleep(3)
    try:
        webbrowser.open('http://127.0.0.1:8000')
    except Exception as e:
        print(f"Could not open browser: {e}")

if __name__ == "__main__":
    app_dir = os.path.dirname(os.path.abspath(__file__))
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    try:
        # Direct import so Nuitka can trace the dependency
        from app.main import app as fastapi_app
        import uvicorn

        browser_thread = Thread(target=open_browser, daemon=True)
        browser_thread.start()

        print("Starting MoB_KML server on http://127.0.0.1:8000 ...")
        uvicorn.run(
            fastapi_app,
            host="127.0.0.1",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)
    except Exception as e:
        # Write error to file next to exe for debugging
        err_path = os.path.join(app_dir, "mob_kml_error.log")
        with open(err_path, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
"@
# Use .NET to write without BOM
[System.IO.File]::WriteAllText(
    (Join-Path $PWD "launcher.py"),
    $launcher,
    [System.Text.UTF8Encoding]::new($false)
)
Write-Host "Launcher script created" -ForegroundColor Green

# Verify launcher.py can be imported
Write-Host "`nVerifying launcher imports..." -ForegroundColor Yellow
python -c "from app.main import app; print('app.main imported OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Cannot import app.main. Check that app/__init__.py exists." -ForegroundColor Red
    exit 1
}
Write-Host "Import verification passed" -ForegroundColor Green

# Run Nuitka compilation
Write-Host "`nStarting Nuitka compilation..." -ForegroundColor Yellow
Write-Host "This may take 10-20 minutes depending on your system..." -ForegroundColor Cyan

python -m nuitka `
    --onefile `
    --standalone `
    --windows-icon-from-ico=mob.ico `
    --windows-console-mode=force `
    --assume-yes-for-downloads `
    --follow-import-to=fastapi `
    --follow-import-to=uvicorn `
    --follow-import-to=pydantic `
    --follow-import-to=starlette `
    --follow-import-to=pandas `
    --follow-import-to=openpyxl `
    --follow-import-to=rapidfuzz `
    --follow-import-to=cell_kml_generator `
    --follow-import-to=app `
    --follow-import-to=anyio `
    --include-package=cell_kml_generator `
    --include-package=app `
    --include-package=uvicorn.protocols `
    --include-package=uvicorn.protocols.http `
    --include-package=uvicorn.lifespan `
    --include-package=uvicorn.loops `
    --include-module=uvicorn.protocols.http.h11_impl `
    --include-module=uvicorn.loops.asyncio `
    --include-module=uvicorn.lifespan.on `
    --include-package=anyio `
    --include-package=starlette `
    --include-package=multipart `
    --include-data-dir=templates=templates `
    --include-data-dir=static=static `
    --include-data-dir=profiles=profiles `
    --include-data-files=mob.ico=mob.ico `
    --output-dir=dist `
    --output-filename=MoB_KML.exe `
    launcher.py

# Check if build was successful
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "BUILD SUCCESSFUL!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green

    Write-Host "`nExecutable created:" -ForegroundColor Cyan
    Write-Host "  .\dist\MoB_KML.exe" -ForegroundColor Yellow

    Write-Host "`nTo run the application:" -ForegroundColor Cyan
    Write-Host "  .\dist\MoB_KML.exe" -ForegroundColor Yellow

    Write-Host "`nThe application will:" -ForegroundColor Green
    Write-Host "  - Start the FastAPI server on http://127.0.0.1:8000" -ForegroundColor White
    Write-Host "  - Automatically open in your default browser" -ForegroundColor White
    Write-Host "  - Display the MoB_KML interface" -ForegroundColor White
    Write-Host "`nNOTE: Console window is visible for debugging." -ForegroundColor Yellow
    Write-Host "After confirming it works, change --windows-console-mode=force" -ForegroundColor Yellow
    Write-Host "to --windows-console-mode=disable in build_nuitka.ps1" -ForegroundColor Yellow

    # Optional: Create a desktop shortcut
    Write-Host "`nCreating desktop shortcut..." -ForegroundColor Yellow
    $targetPath = (Resolve-Path ".\dist\MoB_KML.exe").Path
    $shortcutPath = "$env:USERPROFILE\Desktop\MoB_KML.lnk"

    try {
        $shell = New-Object -COM WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $targetPath
        $shortcut.WorkingDirectory = (Resolve-Path ".\dist").Path
        $shortcut.IconLocation = (Resolve-Path ".\mob.ico").Path
        $shortcut.Description = "MoB KML Generator - Web Edition"
        $shortcut.Save()
        Write-Host "Desktop shortcut created: MoB_KML.lnk" -ForegroundColor Green
    } catch {
        Write-Host "Could not create desktop shortcut (may require admin)" -ForegroundColor Yellow
    }

    # Clean up launcher script
    Write-Host "`nCleaning up temporary files..." -ForegroundColor Yellow
    Remove-Item ".\launcher.py" -Force -ErrorAction SilentlyContinue
    Write-Host "Temporary files removed" -ForegroundColor Green
} else {
    Write-Host "`n========================================" -ForegroundColor Red
    Write-Host "BUILD FAILED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "`nPlease check the error messages above." -ForegroundColor Yellow
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Build process completed!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
