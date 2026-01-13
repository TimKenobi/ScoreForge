#!/bin/bash
# Build script for ScoreForge on macOS
# Creates a .app bundle and .dmg installer

set -e

echo "🔨 Building ScoreForge for macOS..."

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Install build dependencies
echo "📦 Installing build dependencies..."
pip install pyinstaller dmgbuild

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist

# Build with PyInstaller
echo "🏗️ Running PyInstaller..."
pyinstaller ScoreForge.spec --noconfirm

# Check if build succeeded
if [ ! -d "dist/ScoreForge.app" ]; then
    echo "❌ Build failed - ScoreForge.app not found"
    exit 1
fi

echo "✅ ScoreForge.app created successfully!"

# Create DMG
echo "📀 Creating DMG installer..."

# Create a temporary directory for DMG contents
DMG_DIR="dist/dmg"
mkdir -p "$DMG_DIR"
cp -r "dist/ScoreForge.app" "$DMG_DIR/"

# Create Applications symlink
ln -sf /Applications "$DMG_DIR/Applications"

# Create DMG
DMG_NAME="ScoreForge-1.0.0-macOS.dmg"
hdiutil create -volname "ScoreForge" -srcfolder "$DMG_DIR" -ov -format UDZO "dist/$DMG_NAME"

# Cleanup
rm -rf "$DMG_DIR"

echo "✅ DMG created: dist/$DMG_NAME"
echo ""
echo "📊 Build summary:"
ls -lh "dist/$DMG_NAME"
echo ""
echo "🎉 macOS build complete!"
