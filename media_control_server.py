import threading
from flask import Flask, render_template_string, request, jsonify
import subprocess
import os

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PC Web Remote</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <style>
        :root {
            --bg-color: #1a1a1d;
            --remote-bg: #2c2c30;
            --btn-bg: #45454a;
            --btn-active-bg: #5a5a60;
            --text-color: #f0f0f0;
            --accent-color: #007bff;
            --trackpad-bg: #3d3d42;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            -webkit-tap-highlight-color: transparent;
        }
        .remote-container {
            background: linear-gradient(to bottom, #3a3a3e, #2c2c30);
            border-radius: 30px;
            padding: 25px;
            width: 100%;
            max-width: 320px; /* Increased width for trackpad */
            box-shadow: 0 15px 35px rgba(0,0,0,0.5), inset 0 2px 2px rgba(255,255,255,0.1);
            border: 1px solid #444;
        }
        .grid-container {
            display: grid;
            grid-template-columns: 1fr; /* Simplified to a single column layout */
            gap: 25px;
            justify-items: center;
        }
        button {
            font-family: inherit;
            background-color: var(--btn-bg);
            color: var(--text-color);
            border: none;
            cursor: pointer;
            transition: background-color 0.2s, transform 0.1s;
            box-shadow: 0 5px 10px rgba(0,0,0,0.3);
            border: 1px solid #555;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        button:active {
            background-color: var(--btn-active-bg);
            transform: scale(0.95);
        }
        .d-pad {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 15px;
            width: 220px;
            height: 220px;
        }
        .d-pad button {
            width: 100%;
            height: 100%;
            border-radius: 15px;
            font-size: 2em;
        }
        #btn-volume-up    { grid-area: 1 / 2 / 2 / 3; }
        #btn-backward     { grid-area: 2 / 1 / 3 / 2; }
        #btn-play-pause   { grid-area: 2 / 2 / 3 / 3; background-color: var(--accent-color); border-radius: 50%; }
        #btn-forward      { grid-area: 2 / 3 / 3 / 4; }
        #btn-volume-down  { grid-area: 3 / 2 / 4 / 3; }
        
        .function-buttons {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            width: 100%;
        }
        .function-buttons button {
            font-size: 1.2em;
            border-radius: 15px;
            height: 55px;
        }
        
        .trackpad-area {
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        #trackpad {
            width: 100%;
            height: 180px;
            background-color: var(--trackpad-bg);
            border-radius: 15px;
            border: 1px solid #555;
            cursor: crosshair;
            touch-action: none; /* Important for preventing scrolling on touch */
        }
        .mouse-buttons {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .mouse-buttons button {
            height: 50px;
            border-radius: 10px;
            font-size: 1em;
        }
        #status {
            margin-top: 10px;
            font-size: 1em;
            color: #888;
            height: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="remote-container">
        <div class="grid-container">
            <!-- Media Controls -->
            <div class="d-pad">
                <button id="btn-volume-up" onclick="sendCmd('volume-up')"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" class="bi bi-volume-up-fill" viewBox="0 0 16 16"><path d="M11.536 14.01A8.473 8.473 0 0 0 14.026 8a8.473 8.473 0 0 0-2.49-6.01l-.708.707A7.476 7.476 0 0 1 13.025 8c0 2.071-.84 3.946-2.197 5.303l.708.707z"/><path d="M10.121 12.596A6.48 6.48 0 0 0 12.025 8a6.48 6.48 0 0 0-1.904-4.596l-.707.707A5.482 5.482 0 0 1 11.025 8a5.482 5.482 0 0 1-1.61 3.89l.706.706z"/><path d="M8.707 11.182A4.486 4.486 0 0 0 10.025 8a4.486 4.486 0 0 0-1.318-3.182L8 5.525A3.489 3.489 0 0 1 9.025 8 3.49 3.49 0 0 1 8 10.475l.707.707z"/><path fill-rule="evenodd" d="M6.717 3.55A.5.5 0 0 1 7 4v8a.5.5 0 0 1-.812.39L3.825 10.5H1.5A.5.5 0 0 1 1 10V6a.5.5 0 0 1 .5-.5h2.325l2.363-1.89a.5.5 0 0 1 .529-.06z"/></svg></button>
                <button id="btn-backward" onclick="sendCmd('backward')"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" class="bi bi-rewind-fill" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M8.404 7.304a.5.5 0 0 0 0 .692l4.793 3.818a.5.5 0 0 0 .803-.386V4.472a.5.5 0 0 0-.803-.386l-4.793 3.818z"/><path fill-rule="evenodd" d="M1.596 7.304a.5.5 0 0 0 0 .692l4.793 3.818a.5.5 0 0 0 .803-.386V4.472a.5.5 0 0 0-.803-.386L1.596 7.304z"/></svg></button>
                <button id="btn-play-pause" onclick="sendCmd('play-pause')">⏯</button>
                <button id="btn-forward" onclick="sendCmd('forward')"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" class="bi bi-fast-forward-fill" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M7.596 7.304a.5.5 0 0 1 0 .692L2.803 11.886A.5.5 0 0 1 2 11.528V4.472a.5.5 0 0 1 .803-.386l4.793 3.818z"/><path fill-rule="evenodd" d="M14.404 7.304a.5.5 0 0 1 0 .692l-4.793 3.818a.5.5 0 0 1-.803-.386V4.472a.5.5 0 0 1 .803-.386l4.793 3.818z"/></svg></button>
                <button id="btn-volume-down" onclick="sendCmd('volume-down')"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" class="bi bi-volume-down-fill" viewBox="0 0 16 16"><path d="M8.707 11.182A4.486 4.486 0 0 0 10.025 8a4.486 4.486 0 0 0-1.318-3.182L8 5.525A3.489 3.489 0 0 1 9.025 8 3.49 3.49 0 0 1 8 10.475l.707.707z"/><path fill-rule="evenodd" d="M6.717 3.55A.5.5 0 0 1 7 4v8a.5.5 0 0 1-.812.39L3.825 10.5H1.5A.5.5 0 0 1 1 10V6a.5.5 0 0 1 .5-.5h2.325l2.363-1.89a.5.5 0 0 1 .529-.06z"/></svg></button>
            </div>
            <div class="function-buttons">
                <button id="btn-brightness-down" onclick="sendCmd('brightness-down')">☀️-</button>
                <button id="btn-mute" onclick="sendCmd('mute')">🔇</button>
                <button id="btn-brightness-up" onclick="sendCmd('brightness-up')">☀️+</button>
            </div>
            
            <!-- Separator -->
            <hr style="width: 100%; border-color: #444; margin: 10px 0;">

            <!-- Trackpad -->
            <div class="trackpad-area">
                <div id="trackpad"></div>
                <div class="mouse-buttons">
                    <button id="btn-left-click" onclick="sendMouseClick('left')">Left</button>
                    <button id="btn-right-click" onclick="sendMouseClick('right')">Right</button>
                </div>
            </div>
            
            <div id="status">PC Web Remote</div>
        </div>
    </div>
    <script>
        const statusEl = document.getElementById('status');

        function sendCmd(cmd) {
            statusEl.innerText = 'Sending...';
            fetch('/' + cmd, {method: 'POST'})
                .then(res => res.json())
                .then(data => {
                    statusEl.innerText = data.status;
                    setTimeout(() => { statusEl.innerText = 'PC Web Remote'; }, 1500);
                })
                .catch(() => {
                    statusEl.innerText = 'Network Error';
                    setTimeout(() => { statusEl.innerText = 'PC Web Remote'; }, 1500);
                });
        }

        function sendMouseClick(button) {
            statusEl.innerText = 'Sending ' + button + ' click...';
            fetch('/mouse-click', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ button: button })
            })
            .then(res => res.json())
            .then(data => {
                statusEl.innerText = data.status;
                setTimeout(() => { statusEl.innerText = 'PC Web Remote'; }, 1500);
            })
            .catch(() => {
                statusEl.innerText = 'Network Error';
                setTimeout(() => { statusEl.innerText = 'PC Web Remote'; }, 1500);
            });
        }

        const trackpad = document.getElementById('trackpad');
        let lastX = 0;
        let lastY = 0;
        let isDragging = false;

        function handleMove(currentX, currentY) {
            if (!isDragging) return;
            
            const dx = Math.round(currentX - lastX);
            const dy = Math.round(currentY - lastY);
            lastX = currentX;
            lastY = currentY;

            if (dx === 0 && dy === 0) return;

            fetch('/mouse-move', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ dx: dx, dy: dy })
            }); // No need to wait for response for smooth tracking
        }

        function startDrag(x, y) {
            isDragging = true;
            lastX = x;
            lastY = y;
            trackpad.style.backgroundColor = 'var(--btn-active-bg)';
        }

        function endDrag() {
            isDragging = false;
            trackpad.style.backgroundColor = 'var(--trackpad-bg)';
        }

        // Mouse Events
        trackpad.addEventListener('mousedown', (e) => {
            e.preventDefault();
            startDrag(e.clientX, e.clientY);
        });
        trackpad.addEventListener('mousemove', (e) => {
            e.preventDefault();
            handleMove(e.clientX, e.clientY);
        });
        trackpad.addEventListener('mouseup', endDrag);
        trackpad.addEventListener('mouseleave', endDrag);

        // Touch Events
        trackpad.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            startDrag(touch.clientX, touch.clientY);
        });
        trackpad.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            handleMove(touch.clientX, touch.clientY);
        });
        trackpad.addEventListener('touchend', endDrag);
        trackpad.addEventListener('touchcancel', endDrag);

    </script>
</body>
</html>
"""

NIRCMD_PATH = os.path.join(os.path.dirname(__file__), 'nircmd.exe')

def run_nircmd(args):
    try:
        # Using CREATE_NO_WINDOW flag to prevent cmd window from flashing
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run([NIRCMD_PATH] + args, check=True, capture_output=True, startupinfo=startupinfo)
        print(f"NirCmd called: {' '.join(args)} | Success")
        return True
    except FileNotFoundError:
        print(f"NirCmd error: nircmd.exe not found at {NIRCMD_PATH}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"NirCmd error: {' '.join(args)} | {e.stderr.decode(errors='ignore').strip()}")
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
    return jsonify(status='Volume Up' if ok else 'Failed')

@app.route('/volume-down', methods=['POST'])
def volume_down():
    ok = run_nircmd(['sendkey', '0xAE', 'press'])
    return jsonify(status='Volume Down' if ok else 'Failed')

@app.route('/play-pause', methods=['POST'])
def play_pause():
    ok = run_nircmd(['sendkey', '0xB3', 'press'])
    return jsonify(status='Play/Pause' if ok else 'Failed')

@app.route('/forward', methods=['POST'])
def forward():
    ok = run_nircmd(['sendkeypress', 'right'])
    return jsonify(status='Forward 5s' if ok else 'Failed')

@app.route('/backward', methods=['POST'])
def backward():
    ok = run_nircmd(['sendkeypress', 'left'])
    return jsonify(status='Backward 5s' if ok else 'Failed')

@app.route('/mute', methods=['POST'])
def mute():
    ok = run_nircmd(['mutesysvolume', '2'])
    return jsonify(status='Mute Toggled' if ok else 'Failed')

@app.route('/brightness-up', methods=['POST'])
def brightness_up():
    ok = run_nircmd(['changebrightness', '10'])
    return jsonify(status='Brightness Up' if ok else 'Failed')

@app.route('/brightness-down', methods=['POST'])
def brightness_down():
    ok = run_nircmd(['changebrightness', '-10'])
    return jsonify(status='Brightness Down' if ok else 'Failed')

@app.route('/mouse-move', methods=['POST'])
def mouse_move():
    data = request.get_json()
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)
    run_nircmd(['movecursor', str(dx), str(dy)])
    return jsonify(status="OK") # No need to show status for every micro-movement

@app.route('/mouse-click', methods=['POST'])
def mouse_click():
    data = request.get_json()
    button = data.get('button', 'left') # Default to left click
    if button not in ['left', 'right']:
        return jsonify(status="Invalid button"), 400
    
    ok = run_nircmd(['sendmouse', button, 'click'])
    return jsonify(status=f'{button.capitalize()} Click' if ok else 'Failed')

def run_flask():
    app.run(host='0.0.0.0', port=3000, debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    print("PC Web Remote Server running!")
    print("Open http://<YOUR_PC_IP>:3000 from your phone to control media.")
    import pystray
    from PIL import Image, ImageDraw
    def create_image():
        # Simple remote icon
        img = Image.new('RGB', (64, 64), color='black')
        d = ImageDraw.Draw(img)
        # Remote body
        d.rectangle([20, 10, 44, 54], fill=(180, 180, 180))
        # Screen
        d.rectangle([24, 14, 40, 30], fill=(50, 50, 50))
        # Button
        d.ellipse([28, 36, 36, 44], fill=(255, 0, 0))
        return img
    def on_quit(icon, item):
        icon.stop()
        print("Server stopped.")
    icon = pystray.Icon("PCWebRemote", create_image(), "PC Web Remote", menu=pystray.Menu(
        pystray.MenuItem("Quit", on_quit)
    ))
    icon.run()
