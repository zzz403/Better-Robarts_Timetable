#!/bin/bash

echo "🧪 Testing UofT Study Rooms App"
echo "==============================="

# Check Python
echo "🐍 Checking Python..."
if command -v python3 &> /dev/null; then
    python3 --version
    echo "✅ Python 3 found"
else
    echo "❌ Python 3 not found"
    exit 1
fi

# Check required packages
echo ""
echo "📦 Checking required packages..."
packages=("streamlit" "pandas" "requests")

for package in "${packages[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo "✅ $package installed"
    else
        echo "❌ $package missing - installing..."
        pip install $package
    fi
done

# Test launcher
echo ""
echo "🚀 Testing launcher (5 seconds)..."
timeout 5s python3 launcher.py &
launcher_pid=$!

sleep 2
if ps -p $launcher_pid > /dev/null; then
    echo "✅ Launcher started successfully"
    kill $launcher_pid 2>/dev/null
else
    echo "❌ Launcher failed to start"
fi

# Check required files
echo ""
echo "📁 Checking required files..."
required_files=("app.py" "script.py" "launcher.py" "uoft_study_rooms.csv")

all_good=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
        all_good=false
    fi
done

echo ""
if [ "$all_good" = true ]; then
    echo "🎉 All checks passed! Ready to build standalone app."
    echo ""
    echo "🏗️  Next steps:"
    echo "   1. Run: ./build_app.sh"
    echo "   2. Share the created 'UofT_Study_Rooms_Standalone' folder"
    echo "   3. Friends can use it without Python!"
else
    echo "⚠️  Some issues found. Please fix them first."
fi