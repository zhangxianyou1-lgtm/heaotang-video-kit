(function (root) {
  'use strict';
  const sensitive = /青禾(?:物业|雅苑|生活|社区|商场|广场|购物中心)?|QINGHE(?:\s*(?:PROPERTY|COMMUNITY))?|[周陈李王赵刘吴郑孙徐朱胡何林高罗梁马][*＊]{1,3}/gi;

  function sensitiveRanges(text, context = '') {
    const ranges = [];
    for (const match of text.matchAll(new RegExp(sensitive.source, sensitive.flags))) {
      const end = match.index + match[0].length;
      ranges.push([match.index, end]);
    }
    if (context === 'identity' && text.trim()) ranges.push([0, text.length]);
    ranges.sort((a, b) => a[0] - b[0]);
    const merged = [];
    for (const range of ranges) {
      const previous = merged.at(-1);
      if (previous && range[0] <= previous[1]) previous[1] = Math.max(previous[1], range[1]);
      else merged.push(range.slice());
    }
    return merged;
  }

  if (typeof module === 'object' && module.exports) { module.exports = { sensitiveRanges }; return; }
  if (typeof document === 'undefined') return;

  const skip = 'script,style,noscript,template,textarea,input,select,option,canvas,svg,.privacy-mask,[data-privacy-ignore]';
  const dirty = new Set();
  let queued = false;
  const raster = document.createElement('canvas');
  const reduced = document.createElement('canvas');
  const rasterContext = raster.getContext('2d', { willReadFrequently: true });
  const reducedContext = reduced.getContext('2d', { willReadFrequently: true });

  function paint(mask) {
    if (!mask.isConnected || !mask.offsetWidth || !mask.offsetHeight) return;
    const style = getComputedStyle(mask);
    const ink = getComputedStyle(mask.parentElement).color;
    const size = parseFloat(style.fontSize) || 13;
    const width = mask.offsetWidth, height = mask.offsetHeight;
    const block = 3.6;
    raster.width = width; raster.height = height;
    rasterContext.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    rasterContext.fillStyle = ink;
    rasterContext.textBaseline = 'middle';
    if ('letterSpacing' in rasterContext) rasterContext.letterSpacing = style.letterSpacing;
    rasterContext.fillText(mask.textContent, 0, height / 2 + size * .035);
    const columns = Math.max(1, Math.ceil(width / block));
    const lines = Math.max(1, Math.ceil(height / block));
    reduced.width = columns; reduced.height = lines;
    reducedContext.drawImage(raster, 0, 0, columns, lines);
    const pixels = reducedContext.getImageData(0, 0, columns, lines).data;
    reducedContext.clearRect(0, 0, columns, lines);
    reducedContext.fillStyle = ink;
    // Mix nearby glyph cells so large brand names retain a fine unreadable mosaic.
    const radius = Math.max(1, Math.floor(size / 12));
    for (let y = 0; y < lines; y++) {
      for (let x = 0; x < columns; x++) {
        let alpha = 0, count = 0;
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -radius; dx <= radius; dx++) {
            const px = x + dx, py = y + dy;
            if (px >= 0 && px < columns && py >= 0 && py < lines) {
              alpha += pixels[(py * columns + px) * 4 + 3]; count++;
            }
          }
        }
        const noise = .65 + ((x * 17 + y * 31 + mask.textContent.length * 7) % 13) / 15;
        reducedContext.globalAlpha = Math.min(.9, alpha / (count * 255) * noise * 1.4);
        reducedContext.fillRect(x, y, 1, 1);
      }
    }
    reducedContext.globalAlpha = 1;
    mask.style.backgroundImage = `url("${reduced.toDataURL()}")`;
  }

  function contextFor(parent) {
    if (parent.closest('.brand-mark,.project-icon') || (parent.closest('.avatar') && /^[周陈李王赵刘吴郑]$/.test(parent.textContent.trim()))) return 'identity';
    return '';
  }

  function wrap(node) {
    const parent = node.parentElement;
    if (!parent || parent.closest(skip)) return;
    const text = node.nodeValue;
    const ranges = sensitiveRanges(text, contextFor(parent));
    if (!ranges.length) return;
    const fragment = document.createDocumentFragment();
    let end = 0;
    for (const [from, to] of ranges) {
      fragment.append(document.createTextNode(text.slice(end, from)));
      const mask = document.createElement('span');
      mask.className = 'privacy-mask';
      mask.textContent = text.slice(from, to);
      fragment.append(mask);
      end = to;
    }
    fragment.append(document.createTextNode(text.slice(end)));
    node.replaceWith(fragment);
  }

  function control(input) {
    const value = input.value || '';
    const hide = Boolean(value && (sensitiveRanges(value).length || /^[周陈李王赵刘吴郑孙徐朱胡何林高罗梁马]$/.test(value.trim())));
    input.classList.toggle('privacy-control', hide);
  }

  function inspect(element) {
    if (!element?.isConnected) return;
    if (element.nodeType === Node.TEXT_NODE) element = element.parentElement;
    if (!element || element.nodeType !== Node.ELEMENT_NODE) return;
    if (!element.matches(skip)) {
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      nodes.forEach(wrap);
    }
    if (element.matches('.privacy-mask')) paint(element);
    element.querySelectorAll('.privacy-mask').forEach(paint);
    if (element.matches('input,select')) control(element);
    element.querySelectorAll('input,select').forEach(control);
  }

  const observer = new MutationObserver(records => {
    for (const record of records) {
      if (record.type === 'childList') {
        for (const added of record.addedNodes) queue(added.nodeType === Node.TEXT_NODE ? added.parentElement : added);
      } else queue(record.target.nodeType === Node.TEXT_NODE ? record.target.parentElement : record.target);
    }
  });
  const observe = () => observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['class','style','open','value'] });

  function flush() {
    queued = false;
    // Capture listeners can queue this flush before a later handler replaces rows.
    // Drain those not-yet-delivered mutations before disconnect discards them.
    for (const record of observer.takeRecords()) {
      if (record.type === 'childList') {
        for (const added of record.addedNodes) dirty.add(added.nodeType === Node.TEXT_NODE ? added.parentElement : added);
      } else dirty.add(record.target.nodeType === Node.TEXT_NODE ? record.target.parentElement : record.target);
    }
    observer.disconnect();
    const roots = [...dirty].filter(element => element?.isConnected);
    dirty.clear();
    try {
      for (const element of roots) {
        if (!roots.some(other => other !== element && other.contains?.(element))) inspect(element);
      }
    } finally { observe(); }
  }
  function queue(element) {
    if (!element) return;
    dirty.add(element);
    if (!queued) { queued = true; queueMicrotask(flush); }
  }
  function start() {
    inspect(document.body);
    observe();
    document.addEventListener('input', event => { if (event.target.matches('input,select')) queue(event.target); }, true);
    document.addEventListener('change', event => { if (event.target.matches('input,select')) queue(event.target); }, true);
    window.addEventListener('resize', () => queue(document.body));
    root.PropertyPrivacy = { refresh: () => queue(document.body), sensitiveRanges };
    document.documentElement.dataset.privacyReady = 'true';
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})(typeof window === 'undefined' ? globalThis : window);
