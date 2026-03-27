#!/bin/bash

echo "🏗️  Building UofT Study Rooms macOS App (Standalone)"
echo "=================================================="

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "📦 Installing PyInstaller..."
    pip install pyinstaller
fi

# Generate spec file for standalone app
echo "📋 Generating PyInstaller spec for standalone app..."
python setup.py

# Build the standalone app (one file)
echo "🔨 Building standalone macOS app bundle..."
pyinstaller UofT_Study_Rooms.spec --clean --onedir

# Check if build was successful
if [ -d "dist/UofT Study Rooms.app" ]; then
    echo "✅ Build successful!"
    echo ""
    echo "� Creating distribution package..."
    
    # Create a DMG-like folder structure
    mkdir -p "UofT_Study_Rooms_Standalone"
    cp -r "dist/UofT Study Rooms.app" "UofT_Study_Rooms_Standalone/"
    
    # Create installation instructions
    cat > "UofT_Study_Rooms_Standalone/README.txt" << 'EOF'
🏫 UofT Study Rooms - Standalone App
===================================

📱 INSTALLATION (For friends without Python):

1. Copy "UofT Study Rooms.app" to your Applications folder
2. Double-click to run
3. The app will open your browser automatically
4. Click "Get Latest Data" in the sidebar to fetch room info

⚠️  FIRST TIME SETUP:
- macOS might show security warning
- Go to System Preferences > Security & Privacy
- Click "Open Anyway" for "UofT Study Rooms"

🔄 USAGE:
- Double-click the app icon to start
- Browser opens automatically at http://localhost:8501
- Use sidebar buttons to refresh data
- Click green time slots to book rooms
- Close terminal window to quit

📞 SUPPORT:
- If it doesn't work, make sure you have internet connection
- The app needs internet to fetch room data
- Contact the developer if you see errors

🎉 Enjoy booking your study rooms!
EOF

    # Create a simple installer script
    cat > "UofT_Study_Rooms_Standalone/Install.command" << 'EOF'
#!/bin/bash
echo "🏫 Installing UofT Study Rooms..."

# Copy to Applications
if [ -d "/Applications" ]; then
    cp -r "UofT Study Rooms.app" "/Applications/"
    echo "✅ Installed to Applications folder"
    echo "🚀 You can now find 'UofT Study Rooms' in your Applications"
    open "/Applications"
else
    echo "❌ Could not access Applications folder"
    echo "📁 Please manually drag 'UofT Study Rooms.app' to Applications"
fi

echo ""
echo "Press any key to continue..."
read -n 1
EOF

    chmod +x "UofT_Study_Rooms_Standalone/Install.command"
    
    echo "✅ Standalone package created!"
    echo "📂 Location: UofT_Study_Rooms_Standalone/"
    echo ""
    echo "� For your friends (NO PYTHON NEEDED):"
    echo "   1. Send them the 'UofT_Study_Rooms_Standalone' folder"
    echo "   2. They double-click 'Install.command' to install"
    echo "   3. Or manually drag the .app to Applications"
    echo "   4. Double-click 'UofT Study Rooms' to run"
    echo ""
    echo "🎁 Ready to share!"
    
    # Optionally create a ZIP for easy sharing
    echo "📦 Creating ZIP file for easy sharing..."
    zip -r "UofT_Study_Rooms_Standalone.zip" "UofT_Study_Rooms_Standalone"
    echo "📎 Created: UofT_Study_Rooms_Standalone.zip"
    
else
    echo "❌ Build failed!"
    echo "Check the output above for errors"
fi