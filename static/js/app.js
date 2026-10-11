/**
 * PC Web Remote - Modern Mobile Frontend Logic
 * Supports Media Mode (Rewind/Play/Forward), Track Navigation, Browser Controls,
 * Touchpad Mouse, Screen Wake Lock, PWA Installation, and Resilient Reconnection.
 */

(function () {
    'use strict';

    // ==========================================
    // State & Configuration
    // ==========================================
    const state = {
        connected: false,
        reconnecting: false,
        systemVolume: 50,
        isMuted: false,
        systemBrightness: 100,
        seekInterval: parseInt(localStorage.getItem('pc_remote_seek_interval') || '10', 10),
        
        // Wake Lock & PWA
        wakeLock: null,
        keepAwake: localStorage.getItem('pc_remote_keep_awake') !== 'false',
        deferredInstallPrompt: null,
        
        // Host & Info
        info: null,
        currentQrType: 'ip'
    };

    // ==========================================
    // DOM Element References
    // ==========================================
    const statusDot = document.getElementById('status-dot');
    const statusLabel = document.getElementById('status-label');
    const actionToast = document.getElementById('action-toast');
    const connectionPill = document.getElementById('connection-pill');
    const btnQuickMute = document.getElementById('btn-quick-mute');
    const headerMuteIcon = document.getElementById('header-mute-icon');

    // Views & Nav
    const navTabs = document.querySelectorAll('.nav-tab');
    const modeViews = document.querySelectorAll('.mode-view');

    // Media Elements
    const volumeSlider = document.getElementById('volume-slider');
    const volumeText = document.getElementById('volume-text');
    const muteIndicator = document.getElementById('mute-indicator');
    const btnVolumeDown = document.getElementById('btn-volume-down');
    const btnVolumeUp = document.getElementById('btn-volume-up');
    const btnMuteToggle = document.getElementById('btn-mute-toggle');
    const muteBtnLabel = document.getElementById('mute-btn-label');
    
    const btnPlayPause = document.getElementById('btn-play-pause');
    const btnSeekBackward = document.getElementById('btn-seek-backward');
    const btnSeekForward = document.getElementById('btn-seek-forward');
    const rewindLabel = document.getElementById('rewind-label');
    const forwardLabel = document.getElementById('forward-label');
    const seekChips = document.getElementById('seek-chips');
    const inputCustomSeek = document.getElementById('input-custom-seek');
    const btnSetCustomSeek = document.getElementById('btn-set-custom-seek');

    const brightnessText = document.getElementById('brightness-text');
    const btnBrightnessDown = document.getElementById('btn-brightness-down');
    const btnBrightnessUp = document.getElementById('btn-brightness-up');

    // Navigation Elements
    const btnMediaPrev = document.getElementById('btn-media-prev');
    const btnMediaNext = document.getElementById('btn-media-next');
    const btnNavBack = document.getElementById('btn-nav-back');
    const btnNavForward = document.getElementById('btn-nav-forward');
    const btnNavRefresh = document.getElementById('btn-nav-refresh');
    const btnNavFullscreen = document.getElementById('btn-nav-fullscreen');
    const btnNavEscape = document.getElementById('btn-nav-escape');
    const btnNavSlidePrev = document.getElementById('btn-nav-slide-prev');
    const btnNavSlideNext = document.getElementById('btn-nav-slide-next');
    const shortcutButtons = document.querySelectorAll('[data-shortcut]');

    // Touchpad & Mouse Elements
    const touchpad = document.getElementById('touchpad');
    const btnMouseLeft = document.getElementById('btn-mouse-left');
    const btnMouseRight = document.getElementById('btn-mouse-right');

    // More & Settings Elements
    const infoStatusVal = document.getElementById('info-status-val');
    const infoHostnameVal = document.getElementById('info-hostname-val');
    const infoIpUrl = document.getElementById('info-ip-url');
    const infoMdnsUrl = document.getElementById('info-mdns-url');
    const infoHostUrl = document.getElementById('info-host-url');
    const btnReconnectNow = document.getElementById('btn-reconnect-now');
    const chipQrIp = document.getElementById('chip-qr-ip');
    const chipQrMdns = document.getElementById('chip-qr-mdns');
    const qrImage = document.getElementById('qr-image');
    const qrCaption = document.getElementById('qr-caption');
    
    const settingWakeLock = document.getElementById('setting-wake-lock');
    const btnPwaInstall = document.getElementById('btn-pwa-install');

    // ==========================================
    // UI Helpers & Feedback
    // ==========================================
    let toastTimeout = null;
    function showToast(text, duration = 1600) {
        if (!actionToast) return;
        actionToast.textContent = text;
        if (toastTimeout) clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => {
            actionToast.textContent = state.connected ? 'PC Web Remote' : 'Disconnected';
        }, duration);
    }

    function triggerHaptic(duration = 15) {
        if (typeof navigator !== 'undefined' && navigator.vibrate) {
            try { navigator.vibrate(duration); } catch (e) {}
        }
    }

    function setConnectionStatus(status) {
        if (status === 'online') {
            state.connected = true;
            state.reconnecting = false;
            statusDot.className = 'status-dot online';
            statusLabel.textContent = 'Connected';
            if (infoStatusVal) {
                infoStatusVal.textContent = 'Connected';
                infoStatusVal.style.color = 'var(--status-green)';
            }
        } else if (status === 'reconnecting') {
            state.connected = false;
            state.reconnecting = true;
            statusDot.className = 'status-dot reconnecting';
            statusLabel.textContent = 'Reconnecting...';
            if (infoStatusVal) {
                infoStatusVal.textContent = 'Reconnecting...';
                infoStatusVal.style.color = 'var(--status-amber)';
            }
        } else {
            state.connected = false;
            state.reconnecting = false;
            statusDot.className = 'status-dot offline';
            statusLabel.textContent = 'Offline';
            if (infoStatusVal) {
                infoStatusVal.textContent = 'Offline';
                infoStatusVal.style.color = 'var(--status-red)';
            }
        }
    }

    // ==========================================
    // API Communication
    // ==========================================
    async function sendRequest(endpoint, method = 'POST', payload = null) {
        const options = {
            method: method,
            headers: {}
        };
        if (payload) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(payload);
        }

        try {
            const res = await fetch(endpoint, options);
            if (!res.ok) {
                throw new Error(`Server returned HTTP ${res.status}`);
            }
            const data = await res.json();
            if (!state.connected) {
                setConnectionStatus('online');
            }
            return data;
        } catch (err) {
            console.warn(`Request failed for ${endpoint}:`, err);
            setConnectionStatus('reconnecting');
            showToast('Network error');
            return null;
        }
    }

    // ==========================================
    // Connection Check & Info Sync
    // ==========================================
    async function syncInfo() {
        try {
            const res = await fetch('/api/info', { cache: 'no-store' });
            if (!res.ok) throw new Error('Info fetch failed');
            const data = await res.json();
            state.info = data;
            setConnectionStatus('online');

            // Update Volume State
            if (typeof data.volume === 'number') {
                updateVolumeUI(data.volume, data.muted);
            }

            // Update Brightness State
            if (typeof data.brightness === 'number') {
                updateBrightnessUI(data.brightness);
            }

            // Update More Tab Info
            if (infoHostnameVal) infoHostnameVal.textContent = data.hostname || 'Unknown';
            if (infoIpUrl) infoIpUrl.textContent = data.urls ? data.urls.ip : `http://${data.ip}:3000`;
            if (infoMdnsUrl) infoMdnsUrl.textContent = data.urls ? data.urls.mdns : `http://${data.hostname.toLowerCase()}.local:3000`;
            if (infoHostUrl) infoHostUrl.textContent = data.urls ? data.urls.hostname : `http://${data.hostname}:3000`;

            return true;
        } catch (err) {
            setConnectionStatus('reconnecting');
            return false;
        }
    }

    setInterval(() => {
        if (document.visibilityState === 'visible') {
            syncInfo();
        }
    }, 6000);

    // ==========================================
    // Volume Management
    // ==========================================
    function updateVolumeUI(level, muted) {
        state.systemVolume = level;
        state.isMuted = !!muted;

        if (volumeSlider) volumeSlider.value = level;
        if (volumeText) volumeText.textContent = `${level}%`;

        if (muted) {
            if (muteIndicator) muteIndicator.style.display = 'inline-block';
            if (muteBtnLabel) muteBtnLabel.textContent = 'Unmute';
            if (btnQuickMute) btnQuickMute.classList.add('active');
        } else {
            if (muteIndicator) muteIndicator.style.display = 'none';
            if (muteBtnLabel) muteBtnLabel.textContent = 'Mute';
            if (btnQuickMute) btnQuickMute.classList.remove('active');
        }
    }

    async function setVolume(level) {
        level = Math.max(0, Math.min(100, Math.round(level)));
        updateVolumeUI(level, state.isMuted);
        showToast(`Volume ${level}%`);
        const data = await sendRequest('/volume', 'POST', { volume: level });
        if (data && typeof data.volume === 'number') {
            updateVolumeUI(data.volume, data.muted);
        }
    }

    let volumeDebounce = null;
    if (volumeSlider) {
        volumeSlider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value, 10);
            updateVolumeUI(val, state.isMuted);
            if (volumeDebounce) clearTimeout(volumeDebounce);
            volumeDebounce = setTimeout(() => {
                setVolume(val);
            }, 60);
        });
    }

    if (btnVolumeDown) {
        btnVolumeDown.addEventListener('click', async () => {
            triggerHaptic(12);
            showToast('Volume Down');
            const data = await sendRequest('/volume-down', 'POST');
            if (data && typeof data.volume === 'number') {
                updateVolumeUI(data.volume, data.muted);
            }
        });
    }

    if (btnVolumeUp) {
        btnVolumeUp.addEventListener('click', async () => {
            triggerHaptic(12);
            showToast('Volume Up');
            const data = await sendRequest('/volume-up', 'POST');
            if (data && typeof data.volume === 'number') {
                updateVolumeUI(data.volume, data.muted);
            }
        });
    }

    async function toggleMute() {
        triggerHaptic(15);
        const data = await sendRequest('/mute', 'POST');
        if (data) {
            showToast(data.muted ? 'Muted' : 'Unmuted');
            if (typeof data.volume === 'number') {
                updateVolumeUI(data.volume, data.muted);
            } else {
                updateVolumeUI(state.systemVolume, !state.isMuted);
            }
        }
    }

    if (btnMuteToggle) btnMuteToggle.addEventListener('click', toggleMute);
    if (btnQuickMute) btnQuickMute.addEventListener('click', toggleMute);

    // ==========================================
    // Media Playback & Configurable Seeking
    // ==========================================
    if (btnPlayPause) {
        btnPlayPause.addEventListener('click', async () => {
            triggerHaptic(20);
            showToast('Play / Pause');
            await sendRequest('/play-pause', 'POST');
        });
    }

    function updateSeekIntervalUI(interval) {
        interval = Math.max(1, Math.min(600, parseInt(interval, 10) || 10));
        state.seekInterval = interval;
        localStorage.setItem('pc_remote_seek_interval', interval.toString());

        if (rewindLabel) rewindLabel.textContent = `−${interval} sec`;
        if (forwardLabel) forwardLabel.textContent = `+${interval} sec`;

        if (seekChips) {
            seekChips.querySelectorAll('.chip').forEach((chip) => {
                if (parseInt(chip.dataset.interval, 10) === interval) {
                    chip.classList.add('active');
                } else {
                    chip.classList.remove('active');
                }
            });
        }
    }

    if (seekChips) {
        seekChips.addEventListener('click', (e) => {
            const chip = e.target.closest('.chip');
            if (!chip) return;
            const interval = parseInt(chip.dataset.interval, 10);
            if (!isNaN(interval)) {
                triggerHaptic(10);
                updateSeekIntervalUI(interval);
                showToast(`Seek: ${interval}s`);
            }
        });
    }

    if (btnSetCustomSeek && inputCustomSeek) {
        btnSetCustomSeek.addEventListener('click', () => {
            const val = parseInt(inputCustomSeek.value, 10);
            if (!isNaN(val) && val > 0) {
                triggerHaptic(12);
                updateSeekIntervalUI(val);
                showToast(`Custom seek: ${val}s`);
                inputCustomSeek.value = '';
            } else {
                showToast('Enter valid positive seconds');
            }
        });

        inputCustomSeek.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                btnSetCustomSeek.click();
            }
        });
    }

    if (btnSeekBackward) {
        btnSeekBackward.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast(`Rewind −${state.seekInterval}s`);
            await sendRequest('/seek', 'POST', { direction: 'backward', seconds: state.seekInterval });
        });
    }

    if (btnSeekForward) {
        btnSeekForward.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast(`Forward +${state.seekInterval}s`);
            await sendRequest('/seek', 'POST', { direction: 'forward', seconds: state.seekInterval });
        });
    }

    // ==========================================
    // Brightness Controls
    // ==========================================
    function updateBrightnessUI(b) {
        state.systemBrightness = b;
        if (brightnessText) brightnessText.textContent = `${b}%`;
    }

    if (btnBrightnessDown) {
        btnBrightnessDown.addEventListener('click', async () => {
            triggerHaptic(12);
            showToast('Dimming Screen...');
            const data = await sendRequest('/brightness-down', 'POST');
            if (data && typeof data.brightness === 'number') {
                updateBrightnessUI(data.brightness);
                showToast(`Brightness: ${data.brightness}%`);
            }
        });
    }

    if (btnBrightnessUp) {
        btnBrightnessUp.addEventListener('click', async () => {
            triggerHaptic(12);
            showToast('Brightening Screen...');
            const data = await sendRequest('/brightness-up', 'POST');
            if (data && typeof data.brightness === 'number') {
                updateBrightnessUI(data.brightness);
                showToast(`Brightness: ${data.brightness}%`);
            }
        });
    }

    // ==========================================
    // Track Navigation (Navigate Mode)
    // ==========================================
    if (btnMediaPrev) {
        btnMediaPrev.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast('Previous Track');
            await sendRequest('/media-prev', 'POST');
        });
    }

    if (btnMediaNext) {
        btnMediaNext.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast('Next Track');
            await sendRequest('/media-next', 'POST');
        });
    }

    // ==========================================
    // Browser Navigation & PC Shortcuts
    // ==========================================
    if (btnNavBack) {
        btnNavBack.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast('Browser Back (PC)');
            await sendRequest('/nav/back', 'POST');
        });
    }

    if (btnNavForward) {
        btnNavForward.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast('Browser Forward (PC)');
            await sendRequest('/nav/forward', 'POST');
        });
    }

    if (btnNavRefresh) {
        btnNavRefresh.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast('Refresh (F5)');
            await sendRequest('/nav/refresh', 'POST');
        });
    }

    if (btnNavFullscreen) {
        btnNavFullscreen.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast('Fullscreen (F11)');
            await sendRequest('/nav/fullscreen', 'POST');
        });
    }

    if (btnNavEscape) {
        btnNavEscape.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast('Escape (Esc)');
            await sendRequest('/nav/escape', 'POST');
        });
    }

    if (btnNavSlidePrev) {
        btnNavSlidePrev.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast('Slide Previous');
            await sendRequest('/nav/slide-prev', 'POST');
        });
    }

    if (btnNavSlideNext) {
        btnNavSlideNext.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast('Slide Next');
            await sendRequest('/nav/slide-next', 'POST');
        });
    }

    shortcutButtons.forEach((btn) => {
        btn.addEventListener('click', async () => {
            const key = btn.dataset.shortcut;
            if (!key) return;
            triggerHaptic(15);
            showToast(`Key: ${btn.textContent.trim()}`);
            await sendRequest('/nav/shortcut', 'POST', { key: key });
        });
    });

    // ==========================================
    // Touchpad & Mouse Control
    // ==========================================
    let touchStartX = 0, touchStartY = 0;
    let lastTouchX = 0, lastTouchY = 0;
    let isTouchActive = false;
    let touchMoveDistance = 0;

    let pendingDx = 0, pendingDy = 0;
    let isSendingMouseMove = false;

    async function flushMouseMove() {
        if (isSendingMouseMove || (pendingDx === 0 && pendingDy === 0)) return;
        const dx = Math.round(pendingDx);
        const dy = Math.round(pendingDy);
        pendingDx -= dx;
        pendingDy -= dy;

        isSendingMouseMove = true;
        try {
            await fetch('/mouse-move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dx: dx, dy: dy })
            });
        } catch (e) {}
        isSendingMouseMove = false;
    }

    if (touchpad) {
        touchpad.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const t = e.touches[0];
            isTouchActive = true;
            touchStartX = t.clientX;
            touchStartY = t.clientY;
            lastTouchX = t.clientX;
            lastTouchY = t.clientY;
            touchMoveDistance = 0;
            touchpad.classList.add('active-touch');
        }, { passive: false });

        touchpad.addEventListener('touchmove', (e) => {
            e.preventDefault();
            if (!isTouchActive) return;
            const t = e.touches[0];
            const dx = t.clientX - lastTouchX;
            const dy = t.clientY - lastTouchY;
            lastTouchX = t.clientX;
            lastTouchY = t.clientY;

            touchMoveDistance += Math.abs(dx) + Math.abs(dy);
            pendingDx += dx * 1.3;
            pendingDy += dy * 1.3;

            flushMouseMove();
        }, { passive: false });

        touchpad.addEventListener('touchend', (e) => {
            e.preventDefault();
            isTouchActive = false;
            touchpad.classList.remove('active-touch');

            // Tap gesture detection (under 8px movement = left click)
            if (touchMoveDistance < 8) {
                triggerHaptic(15);
                sendRequest('/mouse-click', 'POST', { button: 'left' });
                showToast('Left Click');
            }
        }, { passive: false });

        touchpad.addEventListener('touchcancel', () => {
            isTouchActive = false;
            touchpad.classList.remove('active-touch');
        });
    }

    if (btnMouseLeft) {
        btnMouseLeft.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast('Left Click');
            await sendRequest('/mouse-click', 'POST', { button: 'left' });
        });
    }

    if (btnMouseRight) {
        btnMouseRight.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast('Right Click');
            await sendRequest('/mouse-click', 'POST', { button: 'right' });
        });
    }

    // ==========================================
    // Screen Wake Lock API
    // ==========================================
    async function requestWakeLock() {
        if (!state.keepAwake) return;
        if ('wakeLock' in navigator && !state.wakeLock) {
            try {
                state.wakeLock = await navigator.wakeLock.request('screen');
                state.wakeLock.addEventListener('release', () => {
                    state.wakeLock = null;
                });
            } catch (err) {
                console.warn('Wake Lock request failed:', err);
            }
        }
    }

    function releaseWakeLock() {
        if (state.wakeLock) {
            state.wakeLock.release().catch(() => {});
            state.wakeLock = null;
        }
    }

    if (settingWakeLock) {
        settingWakeLock.checked = state.keepAwake;
        settingWakeLock.addEventListener('change', (e) => {
            state.keepAwake = e.target.checked;
            localStorage.setItem('pc_remote_keep_awake', state.keepAwake.toString());
            if (state.keepAwake) {
                requestWakeLock();
                showToast('Screen will stay awake');
            } else {
                releaseWakeLock();
                showToast('Normal screen timeout');
            }
        });
    }

    // ==========================================
    // Browser Lifecycle & Background Handling
    // ==========================================
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            syncInfo();
            requestWakeLock();
        } else {
            releaseWakeLock();
        }
    });

    window.addEventListener('online', () => {
        syncInfo();
        showToast('Network restored');
    });

    window.addEventListener('offline', () => {
        setConnectionStatus('offline');
        showToast('No Wi-Fi connection');
    });

    // ==========================================
    // QR Code & More Tab Options
    // ==========================================
    function setQrType(type) {
        state.currentQrType = type;
        if (qrImage) qrImage.src = `/api/qr?type=${type}&t=${Date.now()}`;
        if (chipQrIp) chipQrIp.classList.toggle('active', type === 'ip');
        if (chipQrMdns) chipQrMdns.classList.toggle('active', type === 'mdns');
        if (qrCaption) {
            qrCaption.textContent = type === 'ip' 
                ? 'Scan to connect directly via IP (works on every phone).' 
                : 'Scan to connect via .local mDNS hostname.';
        }
    }

    if (chipQrIp) chipQrIp.addEventListener('click', () => setQrType('ip'));
    if (chipQrMdns) chipQrMdns.addEventListener('click', () => setQrType('mdns'));

    if (btnReconnectNow) {
        btnReconnectNow.addEventListener('click', async () => {
            triggerHaptic(15);
            showToast('Reconnecting...');
            const ok = await syncInfo();
            showToast(ok ? 'Connected to PC!' : 'Could not reach PC');
        });
    }

    if (connectionPill) {
        connectionPill.addEventListener('click', async () => {
            triggerHaptic(10);
            showToast('Checking connection...');
            await syncInfo();
        });
    }

    // ==========================================
    // Mode Switching (Tabs)
    // ==========================================
    navTabs.forEach((tab) => {
        tab.addEventListener('click', () => {
            const targetId = tab.dataset.target;
            if (!targetId) return;

            triggerHaptic(12);

            navTabs.forEach((t) => t.classList.remove('active'));
            tab.classList.add('active');

            modeViews.forEach((view) => {
                if (view.id === targetId) {
                    view.classList.add('active');
                } else {
                    view.classList.remove('active');
                }
            });
        });
    });

    // ==========================================
    // PWA & Home Screen Installation
    // ==========================================
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    if (isStandalone && btnPwaInstall) {
        btnPwaInstall.style.display = 'none';
    }

    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        state.deferredInstallPrompt = e;
        if (btnPwaInstall && !isStandalone) {
            btnPwaInstall.style.display = 'block';
            btnPwaInstall.addEventListener('click', async () => {
                if (!state.deferredInstallPrompt) return;
                state.deferredInstallPrompt.prompt();
                const choice = await state.deferredInstallPrompt.userChoice;
                if (choice.outcome === 'accepted') {
                    showToast('Installing Web Remote...');
                }
                state.deferredInstallPrompt = null;
                btnPwaInstall.style.display = 'none';
            });
        }
    });

    window.addEventListener('appinstalled', () => {
        state.deferredInstallPrompt = null;
        if (btnPwaInstall) btnPwaInstall.style.display = 'none';
        showToast('PC Web Remote installed!');
    });

    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js').catch((err) => {
                console.warn('Service worker registration failed:', err);
            });
        });
    }

    // ==========================================
    // Initialization
    // ==========================================
    updateSeekIntervalUI(state.seekInterval);
    syncInfo();
    requestWakeLock();

})();
