#!/usr/bin/env python3
"""
Build script to create VoiceKey PC Server executable.

Requirements:
    pip install pyinstaller

Usage:
    python build_exe.py

This will create a standalone .exe file in the 'dist' folder.
"""

import subprocess
import sys
import os

def build():
    print("=" * 50)
    print("  VoiceKey PC Server - EXE Builder")
    print("=" * 50)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print("\n✓ PyInstaller found")
    except ImportError:
        print("\n✗ PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Build the executable
    print("\nBuilding executable...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # Single executable file
        "--name", "VoiceKey-Server",    # Name of the exe
        "--icon", "NONE",               # No icon (add your own .ico file path if you have one)
        "--console",                    # Show console window (for logs)
        "--clean",                      # Clean build
        "voicekey_server.py"
    ]
    
    subprocess.check_call(cmd)
    
    print("\n" + "=" * 50)
    print("  BUILD COMPLETE!")
    print("=" * 50)
    print("\n  Your executable is at:")
    print("  --> dist/VoiceKey-Server.exe")
    print("\n  Just double-click to run!")
    print("=" * 50)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    build()
