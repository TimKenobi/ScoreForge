@echo off
REM Build script for ScoreForge on Windows
REM Creates a standalone .exe

echo Building ScoreForge for Windows...

REM Ensure we're in the project directory
cd /d "%~dp0\.."

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Install build dependencies
echo Installing build dependencies...
pip install pyinstaller

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Build with PyInstaller
echo Running PyInstaller...
pyinstaller ScoreForge.spec --noconfirm

REM Check if build succeeded
if not exist "dist\ScoreForge.exe" (
    echo Build failed - ScoreForge.exe not found
    exit /b 1
)

echo.
echo ScoreForge.exe created successfully!
echo.
echo Build location: dist\ScoreForge.exe
echo.
echo Windows build complete!
