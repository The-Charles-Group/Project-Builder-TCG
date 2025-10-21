// Harden clear_session call to avoid 422s in logs (server tolerates empty JSON).
(function () {
  const originalFetch = window.fetch;
  
  // Override fetch to intercept clear_session calls
  window.fetch = function(url, options = {}) {
    // Fix clear_session calls to include proper body
    if (url && url.includes('/api/clear_session') && options.method === 'POST') {
      options.headers = options.headers || {};
      options.headers['Content-Type'] = 'application/json';
      if (!options.body) {
        options.body = JSON.stringify({ session_id: window.currentSessionId || '' });
      }
    }
    return originalFetch.call(this, url, options);
  };
  
  // On page load, if your code calls /api/clear_session without a body, do it safely here:
  window.addEventListener('load', () => {
    try {
      fetch('/api/clear_session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: window.currentSessionId || '' })
      }).catch(() => {});
    } catch {}
  });
})();