// DoctorHealthy1 Service Worker for PWA and Performance Optimization
const CACHE_NAME = 'doctorhealthy1-v1.0.1';
const STATIC_CACHE = 'doctorhealthy1-static-v1.0.1';
const DYNAMIC_CACHE = 'doctorhealthy1-dynamic-v1.0.1';

// Resources to cache immediately
const STATIC_ASSETS = [
  '/frontend/',
  '/frontend/index.html',
  '/frontend/css/styles.css?v=1.0.1',
  '/frontend/js/app.js?v=1.0.1',
  '/frontend/js/pages.js?v=1.0.1',
  '/frontend/js/error_handling.js?v=1.0.1',
  '/frontend/manifest.json',
  '/frontend/icons/icon-192x192.png',
  '/frontend/icons/icon-512x512.png',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap'
];

// API endpoints to cache
const API_ENDPOINTS = [
  '/api/v1/health',
  '/api/v1/recipes',
  '/api/v1/workouts',
  '/api/v1/nutrition-plans'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    Promise.all([
      caches.open(STATIC_CACHE).then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      }),
      self.skipWaiting()
    ])
  );
});

// Activate event - cleanup old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    Promise.all([
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      self.clients.claim()
    ])
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Handle different types of requests
  if (request.method === 'GET') {
    // Static assets - Cache First strategy
    if (isStaticAsset(request)) {
      event.respondWith(cacheFirst(request));
    }
    // API requests - Network First strategy
    else if (isAPIRequest(request)) {
      event.respondWith(networkFirst(request));
    }
    // HTML pages - Network First with fallback
    else if (isHTMLRequest(request)) {
      event.respondWith(networkFirstWithFallback(request));
    }
    // Everything else - Network First
    else {
      event.respondWith(networkFirst(request));
    }
  }
});

// Cache First strategy for static assets
async function cacheFirst(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('[SW] Cache first failed:', error);
    return new Response('Offline', { status: 503 });
  }
}

// Network First strategy for API calls
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', error);
    const cachedResponse = await caches.match(request);
    return cachedResponse || new Response('Offline', { status: 503 });
  }
}

// Network First with offline fallback for HTML pages
async function networkFirstWithFallback(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache for HTML:', error);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Return offline page or main index
    return caches.match('/frontend/index.html') || new Response('Offline', { status: 503 });
  }
}

// Helper functions
function isStaticAsset(request) {
  return request.url.includes('/frontend/') &&
         (request.url.includes('.css') ||
          request.url.includes('.js') ||
          request.url.includes('.png') ||
          request.url.includes('.jpg') ||
          request.url.includes('.svg') ||
          request.url.includes('.woff') ||
          request.url.includes('.woff2'));
}

function isAPIRequest(request) {
  return request.url.includes('/api/') || request.url.includes('/health');
}

function isHTMLRequest(request) {
  return request.headers.get('accept')?.includes('text/html');
}

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);

  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

async function doBackgroundSync() {
  // Handle offline actions when back online
  console.log('[SW] Performing background sync...');

  // Example: sync user preferences, form submissions, etc.
  // Implementation depends on specific offline requirements
}

// Push notifications (if needed in the future)
self.addEventListener('push', (event) => {
  console.log('[SW] Push received:', event);

  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: '/frontend/icons/icon-192x192.png',
      badge: '/frontend/icons/badge-72x72.png',
      vibrate: [100, 50, 100],
      data: {
        dateOfArrival: Date.now(),
        primaryKey: data.primaryKey
      }
    };

    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event);

  event.notification.close();

  event.waitUntil(
    clients.openWindow(event.notification.data.url || '/')
  );
});

// Error handling
self.addEventListener('error', (event) => {
  console.error('[SW] Service worker error:', event.error);
});

self.addEventListener('unhandledrejection', (event) => {
  console.error('[SW] Service worker unhandled promise:', event.reason);
  event.preventDefault();
});