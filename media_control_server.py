import logging
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
import subprocess
import os
import base64
from io import BytesIO
import signal
import sys
import qrcode
import socket
import ctypes
import time
import queue

# Configure logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename=os.path.join(log_dir, 'media_control.log'),
                    filemode='w')

# Windows specific imports
try:
    import win32api
    import win32con
    import win32com.client
    from PIL import Image, ImageDraw
    import comtypes
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    import tkinter as tk
    IS_WINDOWS = True
except ImportError:
    IS_WINDOWS = False

# Zeroconf for mDNS
try:
    from zeroconf import Zeroconf, ServiceInfo
    HAS_ZEROCONF = True
except ImportError:
    HAS_ZEROCONF = False

app = Flask(__name__, template_folder='templates', static_folder='static')
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

NIRCMD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nircmd.exe')

def run_nircmd(args):
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run([NIRCMD_PATH] + args, check=True, capture_output=True, startupinfo=startupinfo)
        logging.debug(f"NirCmd command '{' '.join(args)}' executed successfully.")
        return True
    except Exception as e:
        logging.error(f"NirCmd error: {e}")
        return False

# ==============================================================================
# Non-Intrusive On-Screen Display (OSD) Overlay
# ==============================================================================
class OSDOverlay:
    """Displays a modern, transparent on-screen overlay on the Windows desktop

    without stealing focus from full-screen media players or games."""
    def __init__(self):
        self.queue = queue.Queue()
        self._thread = None
        if IS_WINDOWS:
            try:
                self._thread = threading.Thread(target=self._run_tk, daemon=True)
                self._thread.start()
            except Exception as e:
                logging.error(f"Failed to start OSD thread: {e}")

    def show(self, text, icon=""):
        if IS_WINDOWS and self._thread:
            self.queue.put((text, icon))

    def _run_tk(self):
        try:
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes('-topmost', True)
            root.attributes('-alpha', 0.92)
            root.configure(bg='#12151d')

            # Apply WS_EX_NOACTIVATE so this window never steals focus
            try:
                hwnd = root.winfo_id()
                GWL_EXSTYLE = -20
                WS_EX_NOACTIVATE = 0x08000000
                WS_EX_TOOLWINDOW = 0x00000080
                cur_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, cur_style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
            except Exception:
                pass

            w, h = 280, 58
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            x = (sw - w) // 2
            y = sh - h - 80
            root.geometry(f'{w}x{h}+{x}+{y}')
            root.withdraw()

            label = tk.Label(root, text='', fg='#f8fafc', bg='#12151d', font=('Segoe UI', 13, 'bold'))
            label.pack(expand=True)

            hide_timer = [None]

            def hide():
                root.withdraw()

            def process_queue():
                try:
                    while True:
                        text, icon = self.queue.get_nowait()
                        label.config(text=f"{icon}  {text}")
                        root.deiconify()
                        if hide_timer[0]:
                            root.after_cancel(hide_timer[0])
                        hide_timer[0] = root.after(1600, hide)
                except queue.Empty:
                    pass
                root.after(40, process_queue)

            process_queue()
            root.mainloop()
        except Exception as e:
            logging.error(f"OSD Tkinter runtime error: {e}")

osd_overlay = OSDOverlay()

# ==============================================================================
# Windows System Volume & Audio Utilities
# ==============================================================================
class AudioManager:
    _volume = None

    @classmethod
    def get_interface(cls):
        try:
            comtypes.CoInitialize()
            if cls._volume is None:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                cls._volume = cast(interface, POINTER(IAudioEndpointVolume))
            return cls._volume
        except Exception:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                cls._volume = cast(interface, POINTER(IAudioEndpointVolume))
                return cls._volume
            except Exception:
                return None

def trigger_native_volume_key(vk_code):
    """Simulates hardware media key press with extended flag to trigger native Windows OSD."""
    if IS_WINDOWS:
        try:
            win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_EXTENDEDKEY, 0)
            time.sleep(0.01)
            win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP, 0)
            return True
        except Exception as e:
            logging.error(f"Error triggering native volume key {vk_code}: {e}")
    return False

def get_system_volume():
    if not IS_WINDOWS:
        return 50, False
    try:
        vol = AudioManager.get_interface()
        if vol:
            scalar = vol.GetMasterVolumeLevelScalar()
            muted = bool(vol.GetMute())
            return int(round(scalar * 100)), muted
    except Exception as e:
        logging.error(f"Error getting volume via pycaw: {e}")
    return 50, False

def set_system_volume(level_percent):
    if not IS_WINDOWS:
        return False
    try:
        vol = AudioManager.get_interface()
        if vol:
            scalar = max(0.0, min(1.0, float(level_percent) / 100.0))
            vol.SetMasterVolumeLevelScalar(scalar, None)
            return True
    except Exception as e:
        logging.error(f"Error setting volume via pycaw: {e}")
    # Fallback to NirCmd (0-65535)
    nircmd_val = int((max(0, min(100, level_percent)) / 100.0) * 65535)
    return run_nircmd(['setsysvolume', str(nircmd_val)])

def toggle_system_mute():
    if not IS_WINDOWS:
        return False
    try:
        vol = AudioManager.get_interface()
        if vol:
            cur = bool(vol.GetMute())
            vol.SetMute(not cur, None)
            return not cur
    except Exception as e:
        logging.error(f"Error toggling mute via pycaw: {e}")
    run_nircmd(['mutesysvolume', '2'])
    return False

# ==============================================================================
# Screen Brightness Utilities
# ==============================================================================
def get_system_brightness():
    if not IS_WINDOWS:
        return 100
    try:
        wmi = win32com.client.GetObject('winmgmts:\\\\.\\root\\wmi')
        for item in wmi.InstancesOf('WmiMonitorBrightness'):
            return int(item.CurrentBrightness)
    except Exception as e:
        logging.debug(f"Could not read brightness via WMI: {e}")
    return 100

def change_system_brightness(delta):
    ok = run_nircmd(['changebrightness', str(delta)])
    new_b = get_system_brightness()
    osd_overlay.show(f"Brightness: {new_b}%", "☀️")
    return ok, new_b

# ==============================================================================
# Network, Hostname & mDNS Services
# ==============================================================================
def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_hostname():
    try:
        return socket.gethostname()
    except Exception:
        return "localhost"

def generate_qr_image(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")

zeroconf_instance = None
zeroconf_info = None

def start_mdns_service():
    global zeroconf_instance, zeroconf_info
    if not HAS_ZEROCONF:
        logging.info("zeroconf library not installed; skipping mDNS advertisement.")
        return
    try:
        ip = get_ip_address()
        host = get_hostname().lower()
        desc = {'service': 'PC Web Remote'}
        zeroconf_info = ServiceInfo(
            '_http._tcp.local.',
            f'PC-Remote._http._tcp.local.',
            addresses=[socket.inet_aton(ip)],
            port=3000,
            properties=desc,
            server=f'{host}.local.'
        )
        zeroconf_instance = Zeroconf()
        zeroconf_instance.register_service(zeroconf_info)
        logging.info(f"mDNS service registered as http://{host}.local:3000")
    except Exception as e:
        logging.warning(f"Could not initialize mDNS service: {e}")

def stop_mdns_service():
    global zeroconf_instance, zeroconf_info
    try:
        if zeroconf_instance and zeroconf_info:
            zeroconf_instance.unregister_service(zeroconf_info)
            zeroconf_instance.close()
            logging.info("mDNS service stopped.")
    except Exception as e:
        logging.error(f"Error stopping mDNS: {e}")

# ==============================================================================
# Web Routes
# ==============================================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manifest.webmanifest')
@app.route('/manifest.json')
def manifest():
    filename = 'manifest.webmanifest' if os.path.exists(os.path.join(app.static_folder, 'manifest.webmanifest')) else 'manifest.json'
    return send_from_directory('static', filename, mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    response = send_from_directory('static', 'sw.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    return response

@app.route('/api/info', methods=['GET'])
def api_info():
    ip = get_ip_address()
    host = get_hostname()
    vol, muted = get_system_volume()
    brightness = get_system_brightness()
    return jsonify({
        "status": "online",
        "hostname": host,
        "ip": ip,
        "port": 3000,
        "urls": {
            "ip": f"http://{ip}:3000",
            "hostname": f"http://{host}:3000",
            "mdns": f"http://{host}.local:3000"
        },
        "volume": vol,
        "muted": muted,
        "brightness": brightness
    })

@app.route('/api/qr', methods=['GET'])
def api_qr():
    qr_type = request.args.get('type', 'ip')
    if qr_type == 'hostname':
        host = get_hostname()
        url = f"http://{host}:3000"
    elif qr_type == 'mdns':
        host = get_hostname()
        url = f"http://{host}.local:3000"
    else:
        ip = get_ip_address()
        url = f"http://{ip}:3000"
        
    img = generate_qr_image(url)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

# ==============================================================================
# Media Routes
# ==============================================================================
@app.route('/volume', methods=['GET', 'POST'])
def handle_volume():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        vol = data.get('volume')
        if vol is not None:
            try:
                vol_int = int(vol)
                set_system_volume(vol_int)
                trigger_native_volume_key(win32con.VK_VOLUME_UP if IS_WINDOWS else 0xAF)
                new_vol, muted = get_system_volume()
                osd_overlay.show(f"Volume: {new_vol}%", "🔊" if not muted else "🔇")
                return jsonify(status="OK", volume=new_vol, muted=muted)
            except ValueError:
                return jsonify(status="Invalid volume parameter"), 400
        return jsonify(status="Missing volume parameter"), 400
    else:
        vol, muted = get_system_volume()
        return jsonify(volume=vol, muted=muted)

@app.route('/volume-up', methods=['POST'])
def volume_up():
    cur_vol, cur_mute = get_system_volume()
    new_vol = min(100, cur_vol + 5)
    set_system_volume(new_vol)
    trigger_native_volume_key(win32con.VK_VOLUME_UP if IS_WINDOWS else 0xAF)
    new_vol, cur_mute = get_system_volume()
    osd_overlay.show(f"Volume: {new_vol}%", "🔊")
    return jsonify(status="Volume Up", volume=new_vol, muted=cur_mute)

@app.route('/volume-down', methods=['POST'])
def volume_down():
    cur_vol, cur_mute = get_system_volume()
    new_vol = max(0, cur_vol - 5)
    set_system_volume(new_vol)
    trigger_native_volume_key(win32con.VK_VOLUME_DOWN if IS_WINDOWS else 0xAE)
    new_vol, cur_mute = get_system_volume()
    osd_overlay.show(f"Volume: {new_vol}%", "🔊")
    return jsonify(status="Volume Down", volume=new_vol, muted=cur_mute)

@app.route('/mute', methods=['POST'])
def mute():
    new_mute = toggle_system_mute()
    trigger_native_volume_key(win32con.VK_VOLUME_MUTE if IS_WINDOWS else 0xAD)
    vol, _ = get_system_volume()
    if new_mute:
        osd_overlay.show("Volume: Muted", "🔇")
    else:
        osd_overlay.show(f"Volume: {vol}%", "🔊")
    return jsonify(status="Mute Toggled", volume=vol, muted=new_mute)

@app.route('/play-pause', methods=['POST'])
def play_pause():
    ok = run_nircmd(['sendkey', '0xB3', 'press'])
    return jsonify(status='Play/Pause' if ok else 'Failed')

@app.route('/media-prev', methods=['POST'])
def media_prev():
    ok = run_nircmd(['sendkey', '0xB1', 'press'])
    return jsonify(status='Previous Track' if ok else 'Failed')

@app.route('/media-next', methods=['POST'])
def media_next():
    ok = run_nircmd(['sendkey', '0xB0', 'press'])
    return jsonify(status='Next Track' if ok else 'Failed')

@app.route('/seek', methods=['POST'])
def seek():
    data = request.get_json(silent=True) or {}
    direction = data.get('direction', 'forward')
    if direction not in ['forward', 'backward']:
        return jsonify(status="Invalid seek direction"), 400
    try:
        seconds = int(data.get('seconds', 10))
        if seconds <= 0 or seconds > 600:
            seconds = 10
    except (ValueError, TypeError):
        seconds = 10
    
    # 5 seconds per standard player left/right arrow press
    steps = max(1, round(seconds / 5))
    key = 'right' if direction == 'forward' else 'left'
    for _ in range(steps):
        run_nircmd(['sendkeypress', key])
        time.sleep(0.02)
        
    return jsonify(status=f"Seek {direction.capitalize()} {seconds}s", seconds=seconds, direction=direction)

@app.route('/forward', methods=['POST'])
def forward():
    data = request.get_json(silent=True) or {}
    try:
        seconds = int(data.get('seconds', 10))
        if seconds <= 0 or seconds > 600:
            seconds = 10
    except (ValueError, TypeError):
        seconds = 10
    steps = max(1, round(seconds / 5))
    for _ in range(steps):
        run_nircmd(['sendkeypress', 'right'])
        time.sleep(0.02)
    return jsonify(status=f'Forward {seconds}s', seconds=seconds)

@app.route('/backward', methods=['POST'])
def backward():
    data = request.get_json(silent=True) or {}
    try:
        seconds = int(data.get('seconds', 10))
        if seconds <= 0 or seconds > 600:
            seconds = 10
    except (ValueError, TypeError):
        seconds = 10
    steps = max(1, round(seconds / 5))
    for _ in range(steps):
        run_nircmd(['sendkeypress', 'left'])
        time.sleep(0.02)
    return jsonify(status=f'Backward {seconds}s', seconds=seconds)

@app.route('/brightness-up', methods=['POST'])
def brightness_up():
    ok, new_b = change_system_brightness(10)
    return jsonify(status=f'Brightness {new_b}%' if ok else 'Failed', brightness=new_b)

@app.route('/brightness-down', methods=['POST'])
def brightness_down():
    ok, new_b = change_system_brightness(-10)
    return jsonify(status=f'Brightness {new_b}%' if ok else 'Failed', brightness=new_b)

# ==============================================================================
# Navigation & Shortcut Routes
# ==============================================================================
@app.route('/nav/back', methods=['POST'])
def nav_back():
    ok = run_nircmd(['sendkey', '0xA6', 'press'])
    return jsonify(status='Browser Back' if ok else 'Failed')

@app.route('/nav/forward', methods=['POST'])
def nav_forward():
    ok = run_nircmd(['sendkey', '0xA7', 'press'])
    return jsonify(status='Browser Forward' if ok else 'Failed')

@app.route('/nav/refresh', methods=['POST'])
def nav_refresh():
    ok = run_nircmd(['sendkey', '0x74', 'press']) # F5
    return jsonify(status='Refresh' if ok else 'Failed')

@app.route('/nav/fullscreen', methods=['POST'])
def nav_fullscreen():
    ok = run_nircmd(['sendkey', '0x7A', 'press']) # F11
    return jsonify(status='Fullscreen' if ok else 'Failed')

@app.route('/nav/escape', methods=['POST'])
def nav_escape():
    ok = run_nircmd(['sendkey', '0x1B', 'press']) # Escape
    return jsonify(status='Escape' if ok else 'Failed')

@app.route('/nav/slide-prev', methods=['POST'])
def nav_slide_prev():
    ok = run_nircmd(['sendkey', '0x21', 'press']) # Page Up
    return jsonify(status='Slide Previous' if ok else 'Failed')

@app.route('/nav/slide-next', methods=['POST'])
def nav_slide_next():
    ok = run_nircmd(['sendkey', '0x22', 'press']) # Page Down
    return jsonify(status='Slide Next' if ok else 'Failed')

@app.route('/nav/shortcut', methods=['POST'])
def nav_shortcut():
    data = request.get_json(silent=True) or {}
    key = data.get('key')
    
    shortcut_map = {
        'tab': ['sendkey', '0x09', 'press'],
        'enter': ['sendkey', '0x0D', 'press'],
        'space': ['sendkey', '0x20', 'press'],
        'win-d': ['sendkeypress', 'rwin+d'],
        'alt-tab': ['sendkeypress', 'alt+tab'],
        'alt-f4': ['sendkeypress', 'alt+f4'],
        'subtitles': ['sendkeypress', 'c'],
        'arrow-up': ['sendkeypress', 'up'],
        'arrow-down': ['sendkeypress', 'down'],
        'arrow-left': ['sendkeypress', 'left'],
        'arrow-right': ['sendkeypress', 'right']
    }
    
    if key not in shortcut_map:
        return jsonify(status="Invalid shortcut key"), 400
        
    ok = run_nircmd(shortcut_map[key])
    return jsonify(status=f"Shortcut {key}" if ok else "Failed")

@app.route('/arrow', methods=['POST'])
def handle_arrow():
    data = request.get_json(silent=True) or {}
    direction = str(data.get('direction', '')).lower()
    
    arrow_keys = {
        'up': (win32con.VK_UP if IS_WINDOWS else 0x26, 'up'),
        'down': (win32con.VK_DOWN if IS_WINDOWS else 0x28, 'down'),
        'left': (win32con.VK_LEFT if IS_WINDOWS else 0x25, 'left'),
        'right': (win32con.VK_RIGHT if IS_WINDOWS else 0x27, 'right')
    }
    
    if direction not in arrow_keys:
        return jsonify(status="Invalid arrow direction"), 400
        
    vk, nircmd_name = arrow_keys[direction]
    if IS_WINDOWS:
        try:
            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_EXTENDEDKEY, 0)
            time.sleep(0.02)
            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP, 0)
            return jsonify(status=f"Arrow {direction.capitalize()}", direction=direction)
        except Exception as e:
            logging.error(f"win32api arrow key event error: {e}")
            
    ok = run_nircmd(['sendkeypress', nircmd_name])
    return jsonify(status=f"Arrow {direction.capitalize()}" if ok else "Failed", direction=direction)

# ==============================================================================
# Mouse Routes (Touchpad Support)
# ==============================================================================
@app.route('/mouse-move', methods=['POST'])
def mouse_move():
    data = request.get_json(silent=True) or {}
    try:
        dx = int(data.get('dx', 0))
        dy = int(data.get('dy', 0))
    except (ValueError, TypeError):
        return jsonify(status="Invalid coordinates"), 400
        
    if dx == 0 and dy == 0:
        return jsonify(status="OK")
        
    if IS_WINDOWS:
        try:
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy, 0, 0)
            return jsonify(status="OK")
        except Exception as e:
            logging.error(f"win32api mouse move error: {e}")
            
    run_nircmd(['movecursor', str(dx), str(dy)])
    return jsonify(status="OK")

@app.route('/mouse-click', methods=['POST'])
def mouse_click():
    data = request.get_json(silent=True) or {}
    button = data.get('button', 'left')
    action = data.get('action', 'click')
    
    if button not in ['left', 'right', 'middle']:
        return jsonify(status="Invalid button"), 400
    if action not in ['click', 'down', 'up']:
        return jsonify(status="Invalid action"), 400
        
    if IS_WINDOWS:
        try:
            if button == 'left':
                down_flag = win32con.MOUSEEVENTF_LEFTDOWN
                up_flag = win32con.MOUSEEVENTF_LEFTUP
            elif button == 'right':
                down_flag = win32con.MOUSEEVENTF_RIGHTDOWN
                up_flag = win32con.MOUSEEVENTF_RIGHTUP
            elif button == 'middle':
                down_flag = win32con.MOUSEEVENTF_MIDDLEDOWN
                up_flag = win32con.MOUSEEVENTF_MIDDLEUP
                
            if action == 'down':
                win32api.mouse_event(down_flag, 0, 0, 0, 0)
                return jsonify(status=f"{button.capitalize()} Down", button=button, action=action)
            elif action == 'up':
                win32api.mouse_event(up_flag, 0, 0, 0, 0)
                return jsonify(status=f"{button.capitalize()} Up", button=button, action=action)
            else:
                win32api.mouse_event(down_flag, 0, 0, 0, 0)
                win32api.mouse_event(up_flag, 0, 0, 0, 0)
                return jsonify(status=f"{button.capitalize()} Click", button=button, action=action)
        except Exception as e:
            logging.error(f"win32api mouse event error: {e}")
            
    cmd_action = 'down' if action == 'down' else ('up' if action == 'up' else 'click')
    ok = run_nircmd(['sendmouse', button, cmd_action])
    return jsonify(status=f"{button.capitalize()} {action.capitalize()}" if ok else "Failed", button=button, action=action)

# ==============================================================================
# Server & System Tray
# ==============================================================================
def run_flask():
    app.run(host='0.0.0.0', port=3000, debug=False, use_reloader=False)

icon = None

def on_quit(icon, item):
    logging.debug("Stopping server...")
    stop_mdns_service()
    icon.stop()

def show_qr_ip(icon, item):
    ip = get_ip_address()
    url = f"http://{ip}:3000"
    img = generate_qr_image(url)
    img.show()

def show_qr_mdns(icon, item):
    host = get_hostname().lower()
    url = f"http://{host}.local:3000"
    img = generate_qr_image(url)
    img.show()

def show_connection_info(icon, item):
    ip = get_ip_address()
    host = get_hostname().lower()
    msg = (
        f"PC Web Remote Connection Options:\n\n"
        f"1. IP Address URL (Recommended - 100% Reliable):\n"
        f"   http://{ip}:3000\n\n"
        f"2. mDNS Local Hostname URL:\n"
        f"   http://{host}.local:3000\n\n"
        f"3. Windows Computer Name URL:\n"
        f"   http://{host}:3000\n\n"
        f"Android Note: Standard Android browsers resolve '.local' via mDNS or direct IP addresses. "
        f"If '{host}' does not open on your phone, use http://{ip}:3000 or http://{host}.local:3000."
    )
    if IS_WINDOWS:
        ctypes.windll.user32.MessageBoxW(0, msg, "PC Web Remote Connection Info", 0x40 | 0x0)
    else:
        print(msg)

def open_in_browser(icon, item):
    try:
        subprocess.run(['cmd', '/c', 'start', 'http://localhost:3000'], check=False)
    except Exception as e:
        logging.error(f"Failed to open browser: {e}")

if __name__ == '__main__':
    if not IS_WINDOWS:
        logging.error("This application requires Windows-specific libraries to run.")
        sys.exit(1)

    # Start mDNS local announcement
    start_mdns_service()

    # Run Flask in background daemon thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    import pystray
    def create_tray_image():
        img = Image.new('RGB', (64, 64), color=(15, 17, 23))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([12, 6, 52, 58], radius=10, fill=(30, 36, 50), outline=(59, 130, 246), width=2)
        d.ellipse([26, 20, 38, 32], fill=(59, 130, 246))
        d.rectangle([22, 42, 42, 46], fill=(100, 116, 139))
        return img
        
    icon = pystray.Icon("PCWebRemote", create_tray_image(), "PC Web Remote", menu=pystray.Menu(
        pystray.MenuItem("Show QR Code (IP - Recommended)", show_qr_ip),
        pystray.MenuItem("Show QR Code (.local Hostname)", show_qr_mdns),
        pystray.MenuItem("Show Connection Info", show_connection_info),
        pystray.MenuItem("Open in Browser", open_in_browser),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit)
    ))
    
    ip_address = get_ip_address()
    hostname = get_hostname().lower()
    print("=" * 60)
    print("PC Web Remote Server Running!")
    print(f"Direct IP URL:      http://{ip_address}:3000 (Recommended)")
    print(f"mDNS Local URL:     http://{hostname}.local:3000")
    print(f"Hostname URL:       http://{hostname}:3000")
    print("=" * 60)
    print("Right-click the system tray icon for QR codes and connection info.")

    try:
        icon.run()
    except KeyboardInterrupt:
        logging.debug("\nCtrl+C received. Stopping server...")
    finally:
        stop_mdns_service()
        if icon:
            icon.stop()
        logging.debug("Exiting application.")
        sys.exit(0)
