# VoiceKey PC Server

**Control your PC with your voice through the VoiceKey mobile app!**

This server receives commands from the VoiceKey mobile app and types text, sends keystrokes, opens URLs, and controls your mouse on your Windows PC.

---

## 📥 Download Options

### Option 1: Download Pre-built EXE (Recommended)
1. Go to the **Releases** page
2. Download `VoiceKey-Server.exe`
3. Double-click to run - no installation needed!

### Option 2: Build Your Own EXE
If you have Python installed:
```bash
# Install requirements
pip install websockets pynput pyinstaller

# Build the executable
python build_exe.py

# Find your exe at: dist/VoiceKey-Server.exe
```

### Option 3: Run with Python
```bash
# Install requirements
pip install websockets pynput

# Run the server
python voicekey_server.py
```

---

## 🚀 Quick Start

1. **Run VoiceKey-Server.exe** on your PC
2. Note the IP address shown (e.g., `192.168.1.100:8765`)
3. Open the **VoiceKey app** on your phone
4. Go to **PC Connect** tab
5. Enter your PC's IP address
6. Tap **Connect**
7. Start talking and watch text appear on your PC!

---

## 🎤 Voice Commands

The app comes with built-in voice commands:

| Say This | Does This |
|----------|-----------|
| "new line" | Press Enter |
| "period" | Insert `.` |
| "comma" | Insert `,` |
| "question mark" | Insert `?` |
| "exclamation" | Insert `!` |
| "tab" | Press Tab |
| "backspace" | Delete character |
| "delete that" | Select all + Delete |
| "select all" | Ctrl+A |
| "copy" | Ctrl+C |
| "paste" | Ctrl+V |
| "show my calendar" | Opens your calendar |

**Add your own commands in the Settings tab!**

---

## 🔧 Troubleshooting

### Can't connect?
- Make sure your phone and PC are on the **same WiFi network**
- Check if Windows Firewall is blocking the connection
- Try disabling firewall temporarily to test

### Text not typing?
- Click on the window/app where you want text to appear
- Make sure VoiceKey Server is running (check the console window)

### Permission issues on Mac/Linux?
- The app may need accessibility permissions to control keyboard/mouse
- On Mac: System Preferences → Security & Privacy → Accessibility

---

## 📋 Requirements

- **Windows 10/11** (for EXE version)
- **Python 3.8+** (if running from source)
- Same WiFi network as your phone

---

## 🛡️ Security Note

This server only accepts connections on your local network. It does NOT expose your PC to the internet.

---

## 📱 Get the Mobile App

Download VoiceKey AI from:
- **iOS**: App Store (coming soon)
- **Android**: Google Play (coming soon)
- **Development**: Scan QR code in Expo Go app

---

Made with ❤️ for voice productivity
