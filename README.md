# PC Web Remote

A simple, lightweight web server to control your Windows PC's media, brightness, and mouse from any device on your local network.

This project uses a Python server and the powerful `nircmd.exe` utility to simulate media key presses, adjust system settings, and control the mouse. It also uses Windows-native APIs to list and switch between open application windows.

## Features
- ⏯️ **Play/Pause:** Control media playback.
- 🔊 **Volume Control:** Turn the system volume up or down.
- ⏪⏩ **Seek:** Go backward or forward by 5-second intervals.
- 🔇 **Mute:** Toggle the system audio.
- ☀️ **Brightness:** Adjust the screen brightness up or down.
- 🖱️ **Trackpad & Mouse:** Use your phone screen as a trackpad to move the cursor and perform left/right clicks.
- 🪟 **Window Switcher:** View all open application windows, see their icons, and bring any window to the foreground with a single tap.
- 🖥️ **System Tray Icon:** The server runs quietly in the system tray and can be closed from there.

## How It Works
The application runs a Flask web server on your PC. When you interact with the web interface, it sends a request to the server. The server then uses either the bundled `nircmd.exe` utility or `pywin32` to execute the corresponding command, such as 'volume up', 'move cursor', or 'show window'.

## Setup and Usage
Follow these steps to get your remote control running:

**1. Prerequisites:**
- Make sure you have Python installed on your Windows PC. You can download it from [python.org](https://www.python.org/downloads/).

**2. Download the Project:**
- You can clone this repository or download the source code as a ZIP file and extract it.

**3. Install Dependencies:**
- Open a command prompt or terminal in the project directory and run the following command to install the required Python libraries (`Flask`, `pystray`, `Pillow`, and `pywin32`):
  ```
  pip install -r requirements.txt
  ```

**4. Run the Server:**
- Double-click the `media_control_server.py` file or run the following command in the terminal:
  ```
  python media_control_server.py
  ```
- The first time you run it, your Windows Firewall may ask for permission. **Allow access**, especially for "Private networks," so your phone can connect to the server.
- To stop the server, press **Ctrl+C** in the terminal window.

**5. Connect From Your Phone:**
- Find your PC's local IP address. You can do this by opening a Command Prompt and typing `ipconfig`. Look for the "IPv4 Address."
- Open a web browser on your phone and navigate to `http://<YOUR_PC_IP>:3000` (e.g., `http://192.168.1.10:3000`).
- You should now see the remote control interface.

## Important Usage Notes
- **Window Focus for Seeking:** For the "Backward 5s" and "Forward 5s" buttons to work, the media application (e.g., VLC, your web browser with YouTube) **must be the active, focused window** on your PC. This is because these buttons simulate the left and right arrow key presses.
- **Compatibility:** This application has been tested on **Windows 11**. Media controls work with most standard players. Brightness, mouse, and window control should work globally across the OS.

## Bundled Software
This project includes `nircmd.exe`, a freeware command-line utility created by Nir Sofer. For more information, please visit the official NirCmd website: [https://www.nirsoft.net/utils/nircmd.html](https://www.nirsoft.net/utils/nircmd.html)

## License
This project is open source. Feel free to fork it, modify it, and contribute.
