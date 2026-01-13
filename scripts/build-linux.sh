#!/bin/bash
# Build script for ScoreForge on Linux
# Creates an AppImage

set -e

echo "🔨 Building ScoreForge for Linux..."

# Ensure we're in the project directory
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Install build dependencies
echo "📦 Installing build dependencies..."
pip install pyinstaller

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist

# Build with PyInstaller
echo "🏗️ Running PyInstaller..."
pyinstaller ScoreForge.spec --noconfirm

# Check if build succeeded
if [ ! -d "dist/ScoreForge" ]; then
    echo "❌ Build failed - ScoreForge directory not found"
    exit 1
fi

echo "✅ ScoreForge built successfully!"

# Create tarball
echo "📦 Creating tarball..."
cd dist
tar -czvf "ScoreForge-1.0.0-linux-x86_64.tar.gz" ScoreForge/
cd ..

echo "✅ Tarball created: dist/ScoreForge-1.0.0-linux-x86_64.tar.gz"

# Try to create AppImage if appimagetool is available
if command -v appimagetool &> /dev/null; then
    echo "📦 Creating AppImage..."
    
    # Create AppDir structure
    APPDIR="dist/ScoreForge.AppDir"
    mkdir -p "$APPDIR/usr/bin"
    mkdir -p "$APPDIR/usr/share/applications"
    mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
    
    # Copy files
    cp -r dist/ScoreForge/* "$APPDIR/usr/bin/"
    
    # Create desktop file
    cat > "$APPDIR/usr/share/applications/scoreforge.desktop" << EOF
[Desktop Entry]
Type=Application
Name=ScoreForge
Comment=Sheet Music Scanner and Editor
Exec=ScoreForge
Icon=scoreforge
Categories=Audio;Music;
Terminal=false
EOF
    
    # Copy desktop file to AppDir root
    cp "$APPDIR/usr/share/applications/scoreforge.desktop" "$APPDIR/"
    
    # Create AppRun
    cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
exec "${HERE}/usr/bin/ScoreForge" "$@"
EOF
    chmod +x "$APPDIR/AppRun"
    
    # Build AppImage
    ARCH=x86_64 appimagetool "$APPDIR" "dist/ScoreForge-1.0.0-x86_64.AppImage"
    
    echo "✅ AppImage created: dist/ScoreForge-1.0.0-x86_64.AppImage"
else
    echo "ℹ️ appimagetool not found - skipping AppImage creation"
    echo "  Install with: wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
fi

echo ""
echo "📊 Build summary:"
ls -lh dist/*.tar.gz 2>/dev/null || true
ls -lh dist/*.AppImage 2>/dev/null || true
echo ""
echo "🎉 Linux build complete!"
