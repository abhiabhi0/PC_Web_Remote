import unittest
import json
from unittest.mock import patch, MagicMock
from media_control_server import app, get_ip_address, get_hostname

class TestPCWebRemoteServer(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_index_page(self):
        """Index page should load successfully with Media, Navigate, and More modes."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('PC Web Remote', html)
        self.assertIn('view-media', html)
        self.assertIn('view-nav', html)
        self.assertIn('view-more', html)
        self.assertIn('styled-slider', html)
        
        # Verify Media section contains Rewind, Play/Pause, Forward
        self.assertIn('btn-seek-backward', html)
        self.assertIn('btn-play-pause', html)
        self.assertIn('btn-seek-forward', html)
        self.assertIn('input-custom-seek', html)
        self.assertIn('rewind-label', html)
        self.assertIn('forward-label', html)

        # Verify Track Navigation is in Navigate view
        self.assertIn('btn-media-prev', html)
        self.assertIn('btn-media-next', html)

        # Verify Motion controls have been removed
        self.assertNotIn('btn-motion-toggle-nav', html)
        self.assertNotIn('motion-hud', html)
        self.assertNotIn('setting-motion-enable', html)

    def test_pwa_manifest_and_sw(self):
        """Manifest and Service Worker should be served at root with correct headers."""
        res_webmanifest = self.client.get('/manifest.webmanifest')
        self.assertEqual(res_webmanifest.status_code, 200)
        data = json.loads(res_webmanifest.data.decode('utf-8'))
        self.assertEqual(data.get('name'), 'PC Web Remote')
        self.assertEqual(data.get('short_name'), 'PC Remote')
        self.assertEqual(data.get('display'), 'standalone')

        res_manifest = self.client.get('/manifest.json')
        self.assertEqual(res_manifest.status_code, 200)

        res_sw = self.client.get('/sw.js')
        self.assertEqual(res_sw.status_code, 200)
        self.assertEqual(res_sw.headers.get('Service-Worker-Allowed'), '/')

    def test_api_info(self):
        """API info route should return online status, hostname, IP, and URLs."""
        response = self.client.get('/api/info')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'online')
        self.assertIn('hostname', data)
        self.assertIn('ip', data)
        self.assertIn('urls', data)
        self.assertIn('volume', data)
        self.assertIn('muted', data)
        self.assertIn('brightness', data)

    def test_api_qr(self):
        """QR code route should generate valid PNG image for IP, hostname, and mdns."""
        res_ip = self.client.get('/api/qr?type=ip')
        self.assertEqual(res_ip.status_code, 200)
        self.assertEqual(res_ip.mimetype, 'image/png')
        self.assertTrue(len(res_ip.data) > 100)

        res_host = self.client.get('/api/qr?type=hostname')
        self.assertEqual(res_host.status_code, 200)
        self.assertEqual(res_host.mimetype, 'image/png')

        res_mdns = self.client.get('/api/qr?type=mdns')
        self.assertEqual(res_mdns.status_code, 200)
        self.assertEqual(res_mdns.mimetype, 'image/png')

    @patch('media_control_server.set_system_volume')
    @patch('media_control_server.get_system_volume')
    def test_volume_routes(self, mock_get_vol, mock_set_vol):
        """Volume GET, POST, volume-up, volume-down, and mute routes."""
        mock_get_vol.return_value = (60, False)
        mock_set_vol.return_value = True

        # GET /volume
        res_get = self.client.get('/volume')
        self.assertEqual(res_get.status_code, 200)
        data = json.loads(res_get.data.decode('utf-8'))
        self.assertEqual(data['volume'], 60)
        self.assertEqual(data['muted'], False)

        # POST /volume
        res_post = self.client.post('/volume', json={'volume': 75})
        self.assertEqual(res_post.status_code, 200)
        mock_set_vol.assert_called_with(75)

        # POST /volume-up
        res_up = self.client.post('/volume-up')
        self.assertEqual(res_up.status_code, 200)
        data_up = json.loads(res_up.data.decode('utf-8'))
        self.assertEqual(data_up['status'], 'Volume Up')

        # POST /volume-down
        res_down = self.client.post('/volume-down')
        self.assertEqual(res_down.status_code, 200)
        data_down = json.loads(res_down.data.decode('utf-8'))
        self.assertEqual(data_down['status'], 'Volume Down')

        # POST /mute
        with patch('media_control_server.toggle_system_mute', return_value=True):
            res_mute = self.client.post('/mute')
            self.assertEqual(res_mute.status_code, 200)
            data_mute = json.loads(res_mute.data.decode('utf-8'))
            self.assertEqual(data_mute['status'], 'Mute Toggled')

    @patch('media_control_server.run_nircmd', return_value=True)
    def test_playback_and_seek_routes(self, mock_nircmd):
        """Playback and configurable seek endpoints."""
        res_pp = self.client.post('/play-pause')
        self.assertEqual(res_pp.status_code, 200)
        mock_nircmd.assert_called_with(['sendkey', '0xB3', 'press'])

        # Previous Track and Next Track invoke distinct media commands
        res_prev = self.client.post('/media-prev')
        self.assertEqual(res_prev.status_code, 200)
        mock_nircmd.assert_called_with(['sendkey', '0xB1', 'press'])

        res_next = self.client.post('/media-next')
        self.assertEqual(res_next.status_code, 200)
        mock_nircmd.assert_called_with(['sendkey', '0xB0', 'press'])

        # POST /seek forward 10s (default 2 steps of 5s)
        res_seek = self.client.post('/seek', json={'direction': 'forward', 'seconds': 10})
        self.assertEqual(res_seek.status_code, 200)
        data_seek = json.loads(res_seek.data.decode('utf-8'))
        self.assertEqual(data_seek['seconds'], 10)
        self.assertEqual(data_seek['direction'], 'forward')

        # POST /seek backward custom 25s
        res_seek_custom = self.client.post('/seek', json={'direction': 'backward', 'seconds': 25})
        self.assertEqual(res_seek_custom.status_code, 200)
        data_custom = json.loads(res_seek_custom.data.decode('utf-8'))
        self.assertEqual(data_custom['seconds'], 25)
        self.assertEqual(data_custom['direction'], 'backward')

        # POST /forward and /backward
        res_fwd = self.client.post('/forward', json={'seconds': 15})
        self.assertEqual(res_fwd.status_code, 200)
        data_fwd = json.loads(res_fwd.data.decode('utf-8'))
        self.assertEqual(data_fwd['seconds'], 15)

        res_bwd = self.client.post('/backward', json={'seconds': 5})
        self.assertEqual(res_bwd.status_code, 200)
        data_bwd = json.loads(res_bwd.data.decode('utf-8'))
        self.assertEqual(data_bwd['seconds'], 5)

        # Invalid direction should return 400
        res_invalid_dir = self.client.post('/seek', json={'direction': 'invalid', 'seconds': 10})
        self.assertEqual(res_invalid_dir.status_code, 400)

    @patch('media_control_server.change_system_brightness', return_value=(True, 90))
    def test_brightness_routes(self, mock_bright):
        """Brightness up and down routes return updated level."""
        res_up = self.client.post('/brightness-up')
        self.assertEqual(res_up.status_code, 200)
        data_up = json.loads(res_up.data.decode('utf-8'))
        self.assertEqual(data_up['brightness'], 90)

        res_down = self.client.post('/brightness-down')
        self.assertEqual(res_down.status_code, 200)
        data_down = json.loads(res_down.data.decode('utf-8'))
        self.assertEqual(data_down['brightness'], 90)

    @patch('media_control_server.run_nircmd', return_value=True)
    def test_navigation_routes(self, mock_nircmd):
        """Browser navigation and presentation shortcuts."""
        res_back = self.client.post('/nav/back')
        self.assertEqual(res_back.status_code, 200)
        mock_nircmd.assert_called_with(['sendkey', '0xA6', 'press'])

        res_fwd = self.client.post('/nav/forward')
        self.assertEqual(res_fwd.status_code, 200)
        mock_nircmd.assert_called_with(['sendkey', '0xA7', 'press'])

        res_ref = self.client.post('/nav/refresh')
        self.assertEqual(res_ref.status_code, 200)
        mock_nircmd.assert_called_with(['sendkey', '0x74', 'press'])

        res_fs = self.client.post('/nav/fullscreen')
        self.assertEqual(res_fs.status_code, 200)
        mock_nircmd.assert_called_with(['sendkey', '0x7A', 'press'])

        res_esc = self.client.post('/nav/escape')
        self.assertEqual(res_esc.status_code, 200)
        mock_nircmd.assert_called_with(['sendkey', '0x1B', 'press'])

        res_sp = self.client.post('/nav/slide-prev')
        self.assertEqual(res_sp.status_code, 200)
        mock_nircmd.assert_called_with(['sendkey', '0x21', 'press'])

        res_sn = self.client.post('/nav/slide-next')
        self.assertEqual(res_sn.status_code, 200)
        mock_nircmd.assert_called_with(['sendkey', '0x22', 'press'])

    @patch('media_control_server.run_nircmd', return_value=True)
    def test_shortcut_whitelisting(self, mock_nircmd):
        """Only whitelisted shortcuts should be executed, others rejected with 400."""
        valid_keys = ['tab', 'enter', 'space', 'win-d', 'alt-tab', 'subtitles']
        for k in valid_keys:
            res = self.client.post('/nav/shortcut', json={'key': k})
            self.assertEqual(res.status_code, 200)

        # Invalid key should be rejected
        res_bad = self.client.post('/nav/shortcut', json={'key': 'rmdir /s'})
        self.assertEqual(res_bad.status_code, 400)

    @patch('media_control_server.win32api.mouse_event')
    def test_mouse_routes(self, mock_mouse_event):
        """Mouse move and click endpoints."""
        res_move = self.client.post('/mouse-move', json={'dx': 12, 'dy': -8})
        self.assertEqual(res_move.status_code, 200)
        mock_mouse_event.assert_called_with(1, 12, -8, 0, 0) # 1 is MOUSEEVENTF_MOVE

        res_click_left = self.client.post('/mouse-click', json={'button': 'left'})
        self.assertEqual(res_click_left.status_code, 200)

        res_click_right = self.client.post('/mouse-click', json={'button': 'right'})
        self.assertEqual(res_click_right.status_code, 200)

        res_click_bad = self.client.post('/mouse-click', json={'button': 'invalid'})
        self.assertEqual(res_click_bad.status_code, 400)

    def test_removed_window_switcher(self):
        """Ensure /windows and /switch-window endpoints have been completely removed."""
        res_windows = self.client.get('/windows')
        self.assertEqual(res_windows.status_code, 404)

        res_switch = self.client.post('/switch-window', json={'hwnd': 12345})
        self.assertEqual(res_switch.status_code, 404)

if __name__ == '__main__':
    unittest.main()
