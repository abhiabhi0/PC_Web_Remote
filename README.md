# PC Web Remote

A modern, lightweight web remote for controlling your Windows PC's media, volume, brightness, navigation, and mouse directly from your phone browser over your local network—built for watching movies and controlling presentations from the couch or bed without installing a dedicated mobile app.

---

## 📖 Table of Contents
- [Project Overview](#-project-overview)
- [Features](#-features)
- [How It Works](#-how-it-works)
- [Requirements](#-requirements)
- [Installation and Setup](#-installation-and-setup)
- [Connecting from a Phone](#-connecting-from-a-phone)
- [Installing the PWA on Android](#-installing-the-pwa-on-android)
- [Usage Guide](#-usage-guide)
- [Security and Privacy](#-security-and-privacy)
- [Troubleshooting](#-troubleshooting)
- [Development and Contributing](#-development-and-contributing)
- [License and Third-Party Components](#-license-and-third-party-components)

---

## 🌟 Project Overview

**PC Web Remote** turns any Android phone, tablet, or mobile device with a modern web browser into a responsive remote control for your Windows PC over your local Wi-Fi network. 

The primary use case is relaxed entertainment: watching movies, streaming video (YouTube, Netflix, VLC, MPC), or presenting slides from the couch or bed without having to get up to reach your laptop's keyboard and trackpad.

The application requires **no native mobile app or APK installation**. Your Windows PC runs a lightweight Python web server (Flask) in the system tray, and your phone connects directly through its browser with a mobile-first dark interface.

---

## ✨ Features

### 1. 🎬 Media Mode (Default View)
- ⏪ **Rewind Control**: Dedicated Rewind button with dynamic interval feedback (e.g., `−10 sec`).
- ⏯️ **Large Play/Pause**: Prominent central button designed for easy tapping without looking away from your screen.
- ⏩ **Forward Control**: Dedicated Fast-Forward button with dynamic interval feedback (e.g., `+10 sec`).
- ⏱️ **Configurable Seeking**:
  - Quick-preset chips for **5s**, **10s** (default), **15s**, **30s**, and **60s**.
  - Custom interval input: Enter any positive integer seconds and tap "Set".
  - Selected interval persists across page reloads using browser storage (`localStorage`).
- 🔊 **Live Volume Control & Windows Feedback**:
  - Real-time system volume slider (0%–100%) synchronized bidirectionally with Windows Core Audio.
  - Dedicated tactile **-5%** and **+5%** step buttons.
  - One-tap **Mute / Unmute** toggle with visual badge.
  - **On-Screen Feedback**: Simulates hardware media key events (`VK_VOLUME_UP`, `VK_VOLUME_DOWN`, `VK_VOLUME_MUTE`) to trigger the native Windows volume flyout where supported, combined with a lightweight non-intrusive on-screen display (OSD) overlay.
- ☀️ **Screen Brightness Adjustment**:
  - Dedicated **Dim (-10%)** and **Brighten (+10%)** controls.
  - Real-time percentage display on the remote and an elegant non-intrusive on-screen display (OSD) overlay on your laptop screen.
- 🎯 **Dedicated Arrow Keys (Collapsible D-Pad)**:
  - Mobile-friendly 4-way directional pad sending native Windows keyboard arrow keys (↑, ↓, ←, →).
  - Perfect for VLC and other media players that use arrow keys for native seeking and fine playback adjustments.
  - Collapsible with one tap to keep the primary Media controls prominent and easy to reach while watching movies.
- 🖱️ **Collapsible Mouse & Touchpad**:
  - Touchpad surface for smooth Windows cursor navigation without leaving the Media screen.
  - Tap-to-click, **Left Click**, **Right Click**, and **Drag Lock** (`Drag: ON / OFF`) for selecting or dragging sliders and windows.
  - Collapsible to maintain an uncluttered layout during movie playback.

### 2. 🧭 Navigation & Shortcuts Mode
- 🎵 **Media Track Navigation**:
  - **Previous Track (`|<<`)** and **Next Track (`>>|`)**: Clearly labeled controls that send native Windows media track commands (`VK_MEDIA_PREV_TRACK` `0xB1` and `VK_MEDIA_NEXT_TRACK` `0xB0`) to compatible players (Spotify, VLC, YouTube, etc.).
  - Kept completely separate from browser back/forward navigation.
- 🎯 **Dedicated Arrow Keys (D-Pad)**:
  - 4-way keyboard D-pad (Up, Left, Down, Right) for general Windows navigation, selecting items, scrolling lists, and media player shortcuts.
- 🌐 **Browser & Window Navigation**:
  - **Browser Back** & **Browser Forward**: Sends native Windows shortcuts (`Alt+Left` / `Alt+Right` / `VK_BROWSER_BACK`) to your active PC window without navigating your phone's browser.
  - **Refresh**: Sends `F5` / browser refresh.
  - **Fullscreen Toggle**: Sends `F11`.
  - **Escape Key**: Sends `Esc` to exit full screen or dismiss dialogs.
- 📊 **Presentation Controls**:
  - **Previous Slide** (`Page Up`) and **Next Slide** (`Page Down`).
- ⌨️ **Convenient Shortcuts**: One-tap buttons for **Tab**, **Enter**, **Space**, **Show Desktop (`Win+D`)**, **Alt+Tab**, and **Subtitles** (safely validated through an allowlist).
- 🖱️ **Touchpad Mouse**:
  - Smooth, low-latency touchpad with touch-drag cursor movement and `touch-action: none` to prevent mobile page scrolling.
  - Tap-to-click gesture, dedicated **Left Click** and **Right Click** buttons, and **Drag Lock** mode.
  - Fully synchronized with the Media section touchpad.

### 3. ⚙️ More & Connection Management
- 📡 **Connection Diagnostics**: Live status indicator (Online / Reconnecting / Offline), PC Hostname, Local IP, and active connection URLs.
- 🔄 **Local Hostname & IP Resolution**:
  - **Direct IP URL (Recommended)**: `http://<YOUR_PC_IP>:3000` (works reliably on every mobile device).
  - **mDNS Local URL**: `http://<YOUR_PC_HOSTNAME>.local:3000` (actively announced via Zeroconf for modern Android and iOS devices supporting mDNS).
  - **Computer Name URL**: `http://<YOUR_PC_HOSTNAME>:3000` (for networks where the router maps local NetBIOS/DNS names).
- 📲 **In-Browser Quick Connect QR Code**:
  - Live QR code generator preview directly in the web UI.
  - Defaults to the reachable Direct IP URL, with an instant toggle for `.local Hostname`.
- 🖥️ **Windows System Tray Integration**: The server runs quietly in the system tray, providing quick access to QR codes, connection info, and a clean shutdown option.
- 💡 **Keep Screen Awake**: Integrated Screen Wake Lock API keeps your phone display from turning off or dimming while watching movies.
- 📱 **Progressive Web App (PWA)**: Installable directly from your mobile browser as a standalone web app with offline shell caching.

---

## 🏗️ How It Works

```
┌─────────────────────────────────┐           Local Wi-Fi Network          ┌─────────────────────────────────┐
│          Android Phone          │ ─────────────────────────────────────> │           Windows PC            │
│  (Chrome / Samsung Internet)    │                                        │                                 │
│                                 │                                        │   Flask Web Server (:3000)      │
│  • Mobile-first Web Remote UI   │ <───────────────────────────────────── │   • Serves HTML/CSS/JS Shell    │
│  • Service Worker Shell Cache   │             HTTP / JSON API            │   • Validated Control Routes    │
│  • PWA Manifest (Standalone)    │                                        │   • Local mDNS (Zeroconf)       │
└─────────────────────────────────┘                                        └────────────────┬────────────────┘
                                                                                            │
                                                                   ┌────────────────────────┴────────────────────────┐
                                                                   ▼                                                 ▼
                                                     ┌───────────────────────────┐                     ┌───────────────────────────┐
                                                     │     Windows Native APIs   │                     │     Bundled NirCmd Tool   │
                                                     │  • pycaw & Core Audio     │                     │  • Backlight adjustment   │
                                                     │  • win32api Mouse & Keys  │                     │  • Keystroke simulation   │
                                                     │  • WMI Brightness queries │                     │  • Display commands       │
                                                     │  • Non-activating Tk OSD  │                     └───────────────────────────┘
                                                     └───────────────────────────┘
```

1. **Flask Server**: The Windows PC runs a lightweight Python web server on port `3000`. The server serves the web interface, static assets, PWA manifest, and control API endpoints.
2. **Local Network Connection**: The phone connects to the PC over local Wi-Fi via mDNS (`.local`), local IP, or hostname.
3. **Windows System Integrations**:
   - **`pycaw` & `comtypes`**: Communicates with the Windows Core Audio endpoint (`IAudioEndpointVolume`) to read and set the master volume and mute status accurately.
   - **`win32api` & `win32con` (`pywin32`)**: Dispatches low-latency mouse movement and clicks via `mouse_event`, and dispatches hardware media key events (`VK_VOLUME_UP`, `VK_VOLUME_DOWN`, `VK_VOLUME_MUTE`, `VK_MEDIA_NEXT_TRACK`, `VK_MEDIA_PREV_TRACK`).
   - **`win32com.client` (WMI)**: Queries `WmiMonitorBrightness` to retrieve real-time laptop screen brightness levels.
   - **`nircmd.exe`**: A bundled freeware utility used for backlight brightness adjustments (`changebrightness`) and system key combinations.
   - **`zeroconf`**: Broadcasts `_http._tcp.local.` and `<hostname>.local.` via multicast DNS (mDNS) so Android and iOS devices can resolve your computer without manual IP entry.
   - **Tkinter OSD Overlay**: Renders a floating on-screen indicator (`WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW`) on the laptop screen when volume or brightness changes, ensuring visual feedback without stealing keyboard or mouse focus from your movie.

---

## 📋 Requirements

### Windows PC
- **Operating System**: Windows 10 or Windows 11 (64-bit).
- **Python**: Python 3.8 or newer (tested on Python 3.13).
- **Python Packages**:
  - `Flask` (Web framework)
  - `pystray` (System tray icon)
  - `Pillow` (Icon and image handling)
  - `pywin32` (Windows API bindings)
  - `qrcode` (QR code generation)
  - `pycaw` (Windows Core Audio API)
  - `comtypes` (COM interface support)
  - `zeroconf` (mDNS local network discovery)
- **Bundled Utilities**:
  - `nircmd.exe` (included in repository)

> **Hardware Limitations for Screen Brightness**:
> Screen brightness control requires an internal display (such as a laptop screen) or an external monitor that supports DDC/CI and exposes backlight controls through Windows WMI (`WmiMonitorBrightness`). On desktops with non-DDC/CI monitors, hardware brightness adjustment may not be supported by the display driver.

### Mobile Device
- Any Android phone, tablet, iPhone, or iPad connected to the **same Wi-Fi network** as the PC.
- A modern mobile web browser (Google Chrome, Samsung Internet, Firefox, Safari).

---

## 🚀 Installation and Setup

### 1. Clone or Download the Repository
Open Command Prompt or PowerShell:
```bash
git clone https://github.com/abhiabhi0/PC_Web_Remote.git
cd PC_Web_Remote
```
*(Or download and extract the ZIP file from GitHub).*

### 2. Install Required Python Dependencies
Run:
```bash
pip install -r requirements.txt
```

### 3. Start the Server
Run:
```bash
python media_control_server.py
```
*(Alternatively, double-click `Start_PC_Remote.bat` to launch in a console, or use `Run_Hidden.vbs` to launch silently in the background).*

### 4. Windows Firewall Permission
The first time you run the server, Windows Defender Firewall may prompt you for permission:
- Check **"Private networks, such as my home or work network"**.
- Click **"Allow access"**.
- This is required for your phone to connect to the server over your Wi-Fi router.

### 5. Stopping the Server
- If running in a terminal: Press `Ctrl+C`.
- If running in the background: Right-click the **PC Web Remote** icon in the Windows system tray (bottom-right near the clock) and select **"Quit"**.

---

## 📱 Connecting from a Phone

Ensure your phone and PC are connected to the **same Wi-Fi network**.

### Option A: Desktop `.local` Hostname (Preferred)
Modern Android browsers and iOS devices support mDNS (`.local`) hostname resolution:
1. When the server starts, it prints your local mDNS URL to the terminal (e.g., `http://<your-pc-name>.local:3000`).
2. Open Chrome or your mobile browser and enter:
   ```
   http://<your-pc-name>.local:3000
   ```
3. **Why this is preferred**: If your Wi-Fi router reassigns your PC's IP address later, the `.local` hostname continues to work without needing to update bookmarks.

### Option B: QR-Code Quick Connect
1. On your PC, right-click the **PC Web Remote** icon in the Windows system tray.
2. Click **"Show QR Code (IP - Recommended)"** or **"Show QR Code (.local Hostname)"**.
3. Point your phone's camera at the QR code and tap the link to open the remote immediately.

### Option C: Direct IP-Address Fallback
If your router does not support mDNS resolution:
1. Find your PC's local IPv4 address by typing `ipconfig` in Command Prompt, or right-click the tray icon -> **"Show Connection Info"**.
2. Open your mobile browser and enter:
   ```
   http://<YOUR_PC_IP>:3000
   ```
   *(For example: `http://192.168.1.15:3000`).*

---

## 📲 Installing the PWA on Android

You can install PC Web Remote on your Android phone as a Progressive Web App (PWA) so that it runs full-screen like a native application without browser address bars:

1. Open the remote URL (e.g., `http://<your-pc-name>.local:3000` or `http://<YOUR_PC_IP>:3000`) in **Google Chrome** or **Samsung Internet** on your Android phone.
2. Tap the browser menu (**⋮** in the upper-right or lower-right).
3. Tap **"Add to Home screen"** or **"Install app"**.
4. Confirm installation. An icon titled **PC Remote** will appear on your phone's home screen and app launcher.
5. Opening the icon launches the remote in standalone full-screen mode.

### Secure Context & PWA Limitations
- **Secure Context Considerations**: W3C specifications for automated browser installation prompts (`beforeinstallprompt`) and service worker background features generally require a secure origin (`https://` or `localhost`). When accessed over plain `http://` across a local network, standard mobile browsers allow manual installation via **"Add to Home screen"** / **"Install app"**, creating a standalone web app window.
- **Enabling Full Secure Context on Chrome for Android**: If desired, you can instruct Chrome on Android to treat your local remote URL as a secure origin by visiting `chrome://flags/#unsafely-treat-insecure-origin-as-secure` on your phone, adding `http://<your-pc-name>.local:3000` (or your IP URL), and restarting Chrome.
- **Offline Shell vs. Live PC Controls**: Installing the PWA caches the static application shell (HTML, CSS, JS, icons) so the remote opens quickly. However, **PC Web Remote controls a physical Windows PC**: it does not queue commands or simulate PC actions when the PC is turned off or disconnected. When your PC is offline, the interface clearly displays a disconnected indicator and a **Refresh & Reconnect** action.

---

## 🎮 Usage Guide

### Mode Navigation
The bottom navigation bar allows switching between three primary screens:
1. **Media (Default)**: Volume, Rewind, Play/Pause, Forward, and Brightness.
2. **Navigate**: Track Navigation (Previous/Next Track), Browser navigation, shortcuts, and touchpad mouse.
3. **More**: Connection diagnostics, QR code switcher, Wake Lock preference, and setup guides.

### Configurable Seek Intervals
- Tap any preset chip (**5s**, **10s**, **15s**, **30s**, **60s**) to change the seek duration.
- To use a custom duration, enter positive integer seconds into the **Sec** box and tap **Set**.
- The Rewind and Forward buttons dynamically display the active interval (e.g., `−15 sec` and `+15 sec`).

### Arrow Keys & VLC Media Player Compatibility
- **Dedicated Arrow Keys (D-Pad)**: The 4 directional buttons (↑, ↓, ←, →) send native keyboard arrow keys directly to the active window on your Windows PC.
- **VLC Behavior**:
  - In VLC Media Player, pressing the Left/Right arrows triggers VLC's native configured jump (e.g., 10-second short jump).
  - Pressing Up/Down arrows adjusts VLC's internal playback volume.
  - This allows you to use VLC's native navigation and key bindings without conflicting with PC Web Remote's global controls.
- **Distinction from Rewind/Forward**:
  - The dedicated **Rewind / Forward** buttons use PC Web Remote's configurable seek duration (e.g., 5s, 10s, 30s).
  - The **Arrow Keys** send literal keyboard arrow strokes to let the active application handle the key according to its own shortcuts.
- **Distinction from System Volume**:
  - The dedicated **System Volume** slider and step buttons globally adjust Windows master audio via Windows Core Audio.
  - Arrow key events do not alter system-wide volume unless the focused application's specific shortcuts do so.

### Mouse & Touchpad Controls (Media & Navigate)
- **Collapsible Panels in Media Mode**: To keep primary movie controls easy to tap without scrolling, the Arrow Keys and Mouse/Touchpad panels in the Media section are collapsible. Tap the header to expand or hide them at any time.
- **Touchpad Surface**: Swipe across the touchpad surface to smoothly glide the Windows cursor. Tapping quickly triggers a native Left Click.
- **Left & Right Click**: Dedicated mobile-friendly buttons provide tactile click actions.
- **Drag Lock**: Tap the **Drag** button to toggle Drag Mode (`Drag: ON`). When active, the left mouse button is held down while you swipe the touchpad, enabling window moving, slider dragging, and text selection. Tap Drag or Left Click again to release.
- **Accidental Scroll Prevention**: The touchpad surface uses `touch-action: none` and dedicated touch handlers so finger movement controls the PC cursor without scrolling your phone's webpage.

### Important Notes on Application Focus
- Keystroke-based commands (such as Arrow Keys, Rewind/Forward seeking, Browser Back/Forward using `Alt+Left`/`Alt+Right`, and Presentation slide changes) send keystrokes to the **active, foreground window** on your PC.
- Make sure your target media player (e.g., VLC, YouTube tab in Chrome, Netflix, MPC) is the focused application on your PC.

### Track Navigation vs. Seeking
- **Rewind / Forward** (in Media mode) skips backward or forward *within the current media file or video*.
- **Previous Track / Next Track** (in Navigate mode) skips between *playlist tracks or songs* by sending Windows media key commands.

---

## 🔒 Security and Privacy

- **Local Network Scope**: PC Web Remote is intentionally designed for private, local home Wi-Fi networks. It does not use any cloud servers or third-party relay services.
- **Network Binding**: The server binds to `0.0.0.0:3000` to allow devices on your local Wi-Fi subnet to access the controls.
- **No Public Exposure**: Because the server does not include user authentication, **never expose port 3000 directly to the public internet** (e.g., via router port forwarding). Always keep the server behind your local network firewall.
- **Allowlisted Keystrokes**: Keyboard shortcuts and navigation commands are strictly validated against an internal allowlist on the server to prevent unauthorized command injection.

---

## 🔧 Troubleshooting

| Issue | Cause & Solution |
| :--- | :--- |
| **Phone cannot reach the server** | • Ensure your phone and PC are connected to the same Wi-Fi network.<br>• Check that Windows Defender Firewall is not blocking Python (allow Python on Private networks).<br>• Check whether your router has "AP Isolation" or "Client Isolation" enabled, which blocks communication between Wi-Fi devices. |
| **`.local` hostname does not resolve** | • Some older routers or Android versions do not support mDNS resolution.<br>• Use the **Direct IP URL** (`http://<YOUR_PC_IP>:3000`) instead, which works on every device. |
| **QR code opens an unreachable address** | • Open the "More" tab or right-click the system tray icon.<br>• Select the **Direct IP** QR code option, which generates a QR code pointing directly to your PC's active IP address. |
| **Volume/Brightness changes without native Windows indicator** | • Windows volume commands simulate media keys and trigger the native volume flyout where supported, alongside an on-screen display (OSD) overlay.<br>• Windows does not provide a public software API to trigger the native brightness flyout (reserved for BIOS/ACPI Fn-keys). The server adjusts the backlight via monitor APIs and displays an on-screen OSD overlay (`☀️ Brightness: X%`) on your PC. |
| **Seeking or shortcuts have no effect on media** | • The target player (VLC, Chrome with YouTube, Netflix) must be the active, focused window on your Windows PC.<br>• Click the player window once on your PC to bring it into focus. |
| **Server fails to start (`Address already in use`)** | • Another instance of the server or another application is using port `3000`.<br>• Close any existing running instances via Task Manager or the system tray icon. |

---

## 💻 Development and Contributing

### Project Structure
```
PC_Web_Remote/
├── media_control_server.py   # Flask server, Core Audio, NirCmd, WMI, OSD, tray icon
├── requirements.txt          # Python library dependencies
├── nircmd.exe                # Bundled NirCmd Windows utility
├── Start_PC_Remote.bat       # Startup batch script
├── Run_Hidden.vbs            # Silent background launcher
├── templates/
│   └── index.html            # Mobile-first responsive HTML interface
├── static/
│   ├── css/
│   │   └── style.css         # Cinema dark theme stylesheet
│   ├── js/
│   │   └── app.js            # Frontend client logic & PWA handlers
│   ├── manifest.webmanifest  # W3C Web App Manifest
│   ├── manifest.json         # Web App Manifest alias
│   ├── sw.js                 # PWA Service Worker (network-first shell cache)
│   └── icons/
│       ├── icon-192.png      # 192x192 PWA application icon
│       └── icon-512.png      # 512x512 PWA application icon
└── tests/
    └── test_server.py        # Automated test suite
```

### Running Automated Tests
Run the test suite from the repository root:
```bash
python -m unittest discover -s tests -v
```

---

## 📜 License and Third-Party Components

- **Project License**: Open source under the MIT License.
- **NirCmd Utility**: This project bundles `nircmd.exe`, a freeware command-line utility created by Nir Sofer. For licensing and documentation, visit the official NirCmd website: [https://www.nirsoft.net/utils/nircmd.html](https://www.nirsoft.net/utils/nircmd.html).
