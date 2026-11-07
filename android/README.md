# KeyWhisperer Remote (Android)

The phone is a **wireless mic and remote** for the KeyWhisperer companion running on your
Linux desktop. It streams microphone audio over home WiFi and shows what got typed. Nothing is
typed into the phone itself. Listen through your Bluetooth earbuds and control it with taps.

## Get the APK

1. On GitHub open **Actions**, pick the latest **Android** run (green tick).
2. Download the artifact **keywhisperer-debug-apk** (a zip containing `app-debug.apk`).
3. Copy the APK to the phone, open it and allow **Install unknown apps** for your file
   manager/browser when Android asks.

Build it yourself (JDK 17, Android SDK 35, Gradle 8.9+; there is no gradle wrapper committed):

```bash
cd android
echo "sdk.dir=$HOME/Android/Sdk" > local.properties
gradle testDebugUnitTest assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

## Pair

1. Start the companion on the desktop: `keywhisperer run` (it prints a QR code; `keywhisperer pair` shows it again).
2. In the app tap **Pair (scan QR)** and scan it. Or paste the `kw://<ip>:<port>?token=<token>`
   text into the field and tap **Use code**.
3. The pairing is saved and the app reconnects by itself on launch and after WiFi drops
   (retry after 1, 2, 5, then every 10 seconds).

## Controls

| Control | What it does |
| --- | --- |
| Big mic button | Mic on: starts streaming and sends `resume`. Mic off: stops sending audio and sends `pause`. |
| Send | Presses Enter on the desktop. |
| Undo | Removes the last typed chunk. |
| Read back | The companion sends text and the phone reads it aloud (through the earbuds). |
| Stop speaking | Visible while reading aloud; silences it. |

The screen stays on while the mic is on. Recording runs in a foreground service (a
notification with a **Stop** action), so it keeps going if the screen turns off later. The
service stays alive after "mic off" so an earbud tap can start the mic again; tap **Stop** in
the notification to end it completely.

## Earbud taps

Android sends media buttons to the app's MediaSession, which only works while the session is
"playing". The app reports PLAYING while the service runs (no sound is played).

| Gesture | Action |
| --- | --- |
| Play/pause, 1 tap | Toggle mic (acts about 0.4 s later, after checking for more taps) |
| Play/pause, 2 taps within 400 ms | Send |
| Play/pause, 3 taps | Read back |
| Play/pause, 4 taps | Undo |
| Next track | Send |
| Previous track | Read back |

To change the mapping edit `app/src/main/java/com/keywhisperer/remote/MediaButtons.kt`
(one small, commented object).

## Troubleshooting

- **Stuck on "Offline, retrying"**: phone and desktop must be on the same WiFi (not a guest
  network with client isolation). Check the IP in the QR matches the desktop's LAN address.
- **Linux firewall** blocks the port. Allow it:

  ```bash
  sudo ufw allow 8765/tcp
  ```

- **"Companion refused the token"**: the token changed. Scan the QR code again.
- **Earbud taps do nothing**: make sure the service is running (notification visible). Some
  phones route buttons to the last app that played audio; start the mic once from the app.
  Battery "optimization" settings can also stop the service; exempt KeyWhisperer.
- **No reading aloud**: install/enable a text-to-speech engine in Android settings.
