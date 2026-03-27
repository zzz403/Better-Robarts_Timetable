#!/usr/bin/env python3
"""
UofT Study Rooms - Desktop Application Launcher
"""
import os
import sys
import subprocess
import webbrowser
import time
import threading
from pathlib import Path

def find_free_port():
    """Find a free port for Streamlit"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def launch_streamlit():
    """Launch Streamlit app"""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    app_path = script_dir / "app.py"
    
    # Find a free port
    port = find_free_port()
    
    # Launch streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run", 
        str(app_path), 
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.address", "localhost"
    ]
    
    print(f"Starting UofT Study Rooms on http://localhost:{port}")
    
    # Start streamlit in background
    process = subprocess.Popen(cmd, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              cwd=script_dir)
    
    # Wait a bit for server to start
    time.sleep(3)
    
    # Open browser
    webbrowser.open(f"http://localhost:{port}")
    
    return process

def main():
    """Main launcher function"""
    print("🏫 UofT Study Rooms - Starting...")
    
    try:
        # Check if required files exist
        script_dir = Path(__file__).parent
        required_files = ["app.py", "script.py", "requirements.txt"]
        
        for file in required_files:
            if not (script_dir / file).exists():
                print(f"❌ Missing required file: {file}")
                input("Press Enter to exit...")
                return
        
        # Launch streamlit
        process = launch_streamlit()
        
        print("✅ Application started successfully!")
        print("📱 Browser should open automatically")
        print("🔄 To refresh data, use the sidebar buttons in the web interface")
        print("\n" + "="*50)
        print("Press Ctrl+C or close this window to stop the application")
        print("="*50)
        
        # Keep the process running
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping application...")
            process.terminate()
            process.wait()
            
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()