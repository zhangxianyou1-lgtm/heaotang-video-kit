(() => {
  'use strict';
  const cache = new Map();
  const handled = new WeakSet();

  function cameraFrame(src) {
    if (!cache.has(src)) cache.set(src, new Promise((resolve, reject) => {
      const image = new Image();
      image.onerror = () => reject(new Error('Camera source could not be loaded'));
      image.onload = () => {
        try {
          const canvas = document.createElement('canvas');
          canvas.width = 640;
          canvas.height = 480;
          const ctx = canvas.getContext('2d');
          if (!ctx) throw new Error('Canvas 2D unavailable');
          ctx.fillStyle = '#202824';
          ctx.fillRect(0, 0, 640, 480);
          const scale = Math.min(640 / image.naturalWidth, 480 / image.naturalHeight);
          const width = image.naturalWidth * scale;
          const height = image.naturalHeight * scale;
          // Native 480p sampling plus JPEG compression gives camera texture without blurring the digits.
          ctx.imageSmoothingEnabled = true;
          ctx.imageSmoothingQuality = 'low';
          ctx.drawImage(image, (640 - width) / 2, (480 - height) / 2, width, height);
          resolve(canvas.toDataURL('image/jpeg', 0.48));
        } catch (error) { reject(error); }
      };
      image.src = src;
    }));
    return cache.get(src);
  }

  async function apply(image) {
    if (handled.has(image)) return;
    handled.add(image);
    try {
      image.src = await cameraFrame(image.currentSrc || image.src);
      await image.decode();
      image.dataset.nativeResolution = '640x480';
    } catch (error) {
      image.dataset.cameraError = error.name || 'Error';
      console.warn('480p camera rendering unavailable; original image retained.', error);
    }
  }

  function scan(node) {
    if (node.nodeType !== 1) return;
    if (node.matches('img.meter-photo')) apply(node);
    node.querySelectorAll('img.meter-photo').forEach(apply);
  }
  scan(document.documentElement);
  // Only inserted nodes are watched, so replacing src with the cached JPEG cannot trigger a loop.
  new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(scan)))
    .observe(document.documentElement, { childList: true, subtree: true });
})();
