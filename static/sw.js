/**
 * PC Web Remote - Service Worker
 * Implements offline shell caching for PWA installability while ensuring
 * all live PC control actions and dynamic API requests always bypass the cache.
 */

const CACHE_NAME = 'pc-remote-v2';

const STATIC_SHELL_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/manifest.webmanifest',
  '/manifest.json',
  '/static/manifest.webmanifest',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_SHELL_ASSETS).catch((err) => {
        console.warn('Service worker asset caching skipped some files:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // CRITICAL: Never intercept or cache non-GET requests (e.g. volume, playback, seek, mouse)
  // or dynamic API endpoints that query real-time PC state.
  if (
    event.request.method !== 'GET' ||
    url.pathname.startsWith('/api/') ||
    url.pathname === '/volume' ||
    url.pathname === '/play-pause' ||
    url.pathname === '/seek'
  ) {
    return;
  }

  // Network-first strategy for static app shell:
  // Always fetches fresh files when connected; falls back to cache only when PC/Wi-Fi is disconnected.
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
        }
        return networkResponse;
      })
      .catch(() => {
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          if (event.request.mode === 'navigate') {
            return caches.match('/');
          }
        });
      })
  );
});
