/**
 * DAVID CHAMBERS — Service Worker v1.0
 * Enables offline access and fast loading
 */

const CACHE_NAME   = 'dc-legal-v1';
const STATIC_CACHE = 'dc-static-v1';
const API_CACHE    = 'dc-api-v1';

// Files to cache immediately on install (app shell)
const SHELL_FILES = [
  '/',
  '/index.html',
  '/pages/about.html',
  '/pages/practice-areas.html',
  '/pages/services.html',
  '/pages/contact.html',
  '/pages/booking.html',
  '/pages/portal.html',
  '/css/main.css',
  '/js/app.js',
  '/manifest.json',
];

// External resources to cache
const EXTERNAL = [
  'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=DM+Sans:wght@300;400;500;600&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
];

// ── INSTALL: cache the app shell ─────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => {
      // Cache shell files — don't fail if some external resources are blocked
      const localFiles = cache.addAll(SHELL_FILES);
      const extFiles   = Promise.allSettled(EXTERNAL.map(url => cache.add(url)));
      return Promise.all([localFiles, extFiles]);
    }).then(() => self.skipWaiting())
  );
});

// ── ACTIVATE: clean old caches ────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== STATIC_CACHE && k !== API_CACHE)
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ── FETCH: serve from cache, fall back to network ─────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and browser extension requests
  if (request.method !== 'GET') return;
  if (!url.protocol.startsWith('http')) return;

  // API requests: network first, no cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(() =>
        new Response(
          JSON.stringify({ error: 'You are offline. Please check your connection.' }),
          { status: 503, headers: { 'Content-Type': 'application/json' } }
        )
      )
    );
    return;
  }

  // Admin panel: network first (always needs fresh data)
  if (url.pathname.includes('admin.html')) {
    event.respondWith(
      fetch(request).catch(() => caches.match(request))
    );
    return;
  }

  // Images: cache first, then network
  if (request.destination === 'image') {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request).then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(STATIC_CACHE).then(cache => cache.put(request, clone));
          }
          return response;
        }).catch(() => cached);
      })
    );
    return;
  }

  // Everything else: cache first, then network, update cache
  event.respondWith(
    caches.match(request).then(cached => {
      const networkFetch = fetch(request).then(response => {
        if (response.ok && url.origin === location.origin) {
          const clone = response.clone();
          caches.open(STATIC_CACHE).then(cache => cache.put(request, clone));
        }
        return response;
      });
      return cached || networkFetch;
    })
  );
});

// ── BACKGROUND SYNC placeholder ───────────────────────
self.addEventListener('sync', event => {
  if (event.tag === 'sync-bookings') {
    // Future: sync pending bookings made offline
    console.log('[SW] Background sync: bookings');
  }
});

// ── PUSH NOTIFICATIONS placeholder ───────────────────
self.addEventListener('push', event => {
  if (!event.data) return;
  const data = event.data.json();
  self.registration.showNotification(data.title || 'DAVID CHAMBERS', {
    body:    data.body    || 'You have a new update.',
    icon:    '/images/icons/icon-192.png',
    badge:   '/images/icons/icon-72.png',
    vibrate: [200, 100, 200],
    data:    { url: data.url || '/' }
  });
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data?.url || '/')
  );
});
