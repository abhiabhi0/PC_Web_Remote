import threading
from flask import Flask, render_template_string, request, jsonify
import subprocess
import os

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PC Media Controller</title>
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
        button { font-size: 1.5em; margin: 10px; padding: 20px 40px; }
        #status { margin-top: 40px; font-size: 1.2em; color: #333; }
    </style>
</head>
<body>
    <h1>PC Media Controller</h1>
    <button onclick=\"sendCmd('volume-up')\">🔊 Volume Up</button>
    <button onclick="sendCmd('volume-down')">🔉 Volume Down</button>
    <br>
    <button onclick="sendCmd('play-pause')">⏯️ Play/Pause</button>
    <br>
    <button onclick="sendCmd('backward')">⏪ Backward 5s</button>
    <button onclick="sendCmd('forward')">⏩ Forward 5s</button>
    <div id=\"status\"></div>
    <script>
        function sendCmd(cmd) {
            fetch('/' + cmd, {method: 'POST'})
                .then(res => res.json())
                .then(data => {
                    document.getElementById('status').innerText = data.status;
                })
                .catch(() => {
                    document.getElementById('status').innerText = 'Network error';
                });
        }
    </script>
</body>
</html>
"""

NIRCMD_PATH = os.path.join(os.path.dirname(__file__), 'nircmd.exe')

def run_nircmd(args):
    try:
        result = subprocess.run([NIRCMD_PATH] + args, check=True, capture_output=True)
        print(f"NirCmd called: {' '.join(args)} | Success")
        return True
    except FileNotFoundError:
        print(f"NirCmd error: nircmd.exe not found at {NIRCMD_PATH}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"NirCmd error: {' '.join(args)} | {e}")
        return False
    except Exception as e:
        print(f"NirCmd unexpected error: {e}")
        return False

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/volume-up', methods=['POST'])
def volume_up():
    ok = run_nircmd(['sendkey', '0xAF', 'press'])
    msg = 'Volume Up' if ok else 'Failed to change volume'
    print(f"[LOG] /volume-up | {msg}")
    return jsonify(status=msg)

@app.route('/volume-down', methods=['POST'])
def volume_down():
    ok = run_nircmd(['sendkey', '0xAE', 'press'])
    msg = 'Volume Down' if ok else 'Failed to change volume'
    print(f"[LOG] /volume-down | {msg}")
    return jsonify(status=msg)

@app.route('/play-pause', methods=['POST'])
def play_pause():
    ok = run_nircmd(['sendkey', '0xB3', 'press'])
    msg = 'Play/Pause' if ok else 'Failed to Play/Pause'
    print(f"[LOG] /play-pause | {msg}")
    return jsonify(status=msg)

@app.route('/forward', methods=['POST'])
def forward():
    ok = run_nircmd(['sendkeypress', 'right'])
    msg = 'Forwarded 5s' if ok else 'Failed to forward'
    print(f"[LOG] /forward | {msg}")
    return jsonify(status=msg)

@app.route('/backward', methods=['POST'])
def backward():
    ok = run_nircmd(['sendkeypress', 'left'])
    msg = 'Backwarded 5s' if ok else 'Failed to backward'
    print(f"[LOG] /backward | {msg}")
    return jsonify(status=msg)

def run_flask():
    app.run(host='0.0.0.0', port=3000, debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    print("Media Control Server running on your PC!")
    print("Open http://<YOUR_PC_IP>:3000 from your phone to control media.")
    import pystray
    from PIL import Image, ImageDraw
    def create_image():
        img = Image.new('RGB', (64, 64), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.rectangle([16, 24, 48, 40], fill=(255, 255, 255))
        return img
    def on_quit(icon, item):
        icon.stop()
        print("Server stopped.")
    icon = pystray.Icon("MediaControl", create_image(), "Media Control Server", menu=pystray.Menu(
        pystray.MenuItem("Quit", on_quit)
    ))
    icon.run() 