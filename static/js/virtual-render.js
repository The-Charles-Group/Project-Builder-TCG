// Progressive list rendering to avoid long main-thread stalls.
// Renders in chunks using requestAnimationFrame/requestIdleCallback.

(function () {
  function progressiveListRender(items, renderItem, target, opts = {}) {
    const chunk = Math.max(10, opts.chunkSize || 20);
    const delay = Math.max(0, opts.delay || 0);
    let i = 0;
    target.innerHTML = ''; // cheap clear

    function step() {
      const frag = document.createDocumentFragment();
      for (let c = 0; c < chunk && i < items.length; c++, i++) {
        const node = renderItem(items[i], i) || document.createTextNode('');
        frag.appendChild(node);
      }
      target.appendChild(frag);

      if (i < items.length) {
        if (delay > 0) {
          setTimeout(() => requestAnimationFrame(step), delay);
        } else {
          requestAnimationFrame(step);
        }
      } else if (typeof opts.onComplete === 'function') {
        opts.onComplete();
      }
    }

    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => requestAnimationFrame(step), { timeout: 16 });
    } else {
      requestAnimationFrame(step);
    }
  }

  window.progressiveListRender = progressiveListRender;
})();