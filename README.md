# PC Web Remote

A simple, lightweight web server to control your Windows PC's media playback from any device on your local network, like your phone.

This project uses a Python server and the powerful `nircmd.exe` utility to simulate media key presses, offering a reliable way to manage playback without installing any apps on your remote device—all you need is a web browser.

## Features
- ⏯️ **Play/Pause:** Control media playback.
- 🔊 **Volume Control:** Turn the system volume up or down.
- ⏪⏩ **Seek:** Go backward or forward by 5-second intervals.
- 🖥️ **System Tray Icon:** The server runs quietly in the system tray and can be closed from there.

## How It Works
The application runs a Flask web server on your PC. When you press a button on the web interface from your phone, it sends a request to the server. The server then uses the bundled `nircmd.exe` utility to execute the corresponding command, such as 'volume up' or 'press left arrow key'.

## Setup and Usage
Follow these steps to get your remote control running:

**1. Prerequisites:**
- Make sure you have Python installed on your Windows PC. You can download it from [python.org](https://www.python.org/downloads/).

**2. Download the Project:**
- You can clone this repository or download the source code as a ZIP file and extract it.

**3. Install Dependencies:**
- Open a command prompt or terminal in the project directory and run the following command to install the required Python libraries:
  ```
  pip install -r requirements.txt
  ```

**4. Run the Server:**
- Double-click the `media_control_server.py` file or run the following command in the terminal:
  ```
  python media_control_server.py
  ```
- The first time you run it, your Windows Firewall may ask for permission. **Allow access**, especially for "Private networks," so your phone can connect to the server.

**5. Connect From Your Phone:**
- Find your PC's local IP address. You can do this by opening a Command Prompt and typing `ipconfig`. Look for the "IPv4 Address."
- Open a web browser on your phone and navigate to `http://<YOUR_PC_IP>:3000` (e.g., `http://192.168.1.10:3000`).
- You should now see the remote control interface.

## Important Usage Notes
- **Window Focus for Seeking:** For the "Backward 5s" and "Forward 5s" buttons to work, the media application (e.g., VLC, your web browser with YouTube) **must be the active, focused window** on your PC. This is because these buttons simulate the left and right arrow key presses.
- **Compatibility:** This application has been tested on **Windows 11** with the following applications:
  - VLC Media Player
  - YouTube (in Brave)
  - JioCinema (in Brave)

## Bundled Software
This project includes `nircmd.exe`, a freeware command-line utility created by Nir Sofer. For more information, please visit the official NirCmd website: [https://www.nirsoft.net/utils/nircmd.html](https://www.nirsoft.net/utils/nircmd.html)

## License
This project is open source. Feel free to fork it, modify it, and contribute. It is recommended to use an MIT License if you intend to publish your own version.
