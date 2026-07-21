/* gate-annotate.js — click-to-pin annotations on gate artifacts (v6.0, TZ-9).
 *
 * Embed in any gate artifact (contact sheet, sitemap.html):
 *   <script src=".../gate-annotate.js"></script>
 * or inline. Zero dependencies, works from file://.
 *
 * Usage: click the "Annotate" button (bottom-right) or press `a` to arm;
 * the next click drops a pin and opens a comment field. Annotations are
 * kept in localStorage; "Export" downloads annotations.json:
 *   [{target_selector, x, y, text, at}]
 * The orchestrator collects annotations.json after the gate, discusses the
 * notes first thing after the gate, and mirrors each into the decision log.
 */
(function () {
  'use strict';
  var KEY = 'gate-annotations';
  var armed = false;

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || '[]'); }
    catch (e) { return []; }
  }
  function save(list) { localStorage.setItem(KEY, JSON.stringify(list)); }

  function selectorFor(el) {
    if (el.id) return '#' + el.id;
    var parts = [];
    while (el && el.nodeType === 1 && el.tagName !== 'BODY') {
      var sel = el.tagName.toLowerCase();
      if (el.className && typeof el.className === 'string') {
        var cls = el.className.trim().split(/\s+/).slice(0, 2).join('.');
        if (cls) sel += '.' + cls;
      }
      var parent = el.parentElement;
      if (parent) {
        var same = Array.prototype.filter.call(parent.children, function (c) {
          return c.tagName === el.tagName;
        });
        if (same.length > 1) sel += ':nth-of-type(' + (same.indexOf(el) + 1) + ')';
      }
      parts.unshift(sel);
      el = parent;
      if (parts.length > 4) break;
    }
    return parts.join(' > ');
  }

  var bar = document.createElement('div');
  bar.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:99999;' +
    'font:13px system-ui,sans-serif;display:flex;gap:6px;';
  bar.innerHTML =
    '<button id="ga-arm" style="padding:6px 10px;border:1px solid #999;' +
    'background:#fff;border-radius:6px;cursor:pointer">Annotate (a)</button>' +
    '<button id="ga-export" style="padding:6px 10px;border:1px solid #999;' +
    'background:#fff;border-radius:6px;cursor:pointer">Export</button>';
  document.body.appendChild(bar);

  function renderPins() {
    document.querySelectorAll('.ga-pin').forEach(function (p) { p.remove(); });
    load().forEach(function (a, i) {
      var pin = document.createElement('div');
      pin.className = 'ga-pin';
      pin.textContent = String(i + 1);
      pin.title = a.text;
      pin.style.cssText = 'position:absolute;left:' + (a.x - 10) + 'px;top:' +
        (a.y - 10) + 'px;width:20px;height:20px;border-radius:50%;' +
        'background:#b91c1c;color:#fff;font:700 11px/20px system-ui;' +
        'text-align:center;z-index:99998;cursor:default;';
      document.body.appendChild(pin);
    });
  }

  function arm() {
    armed = !armed;
    document.getElementById('ga-arm').style.background = armed ? '#fee2e2' : '#fff';
    document.body.style.cursor = armed ? 'crosshair' : '';
  }

  document.getElementById('ga-arm').addEventListener('click', arm);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'a' && !/INPUT|TEXTAREA/.test(e.target.tagName)) arm();
  });

  document.addEventListener('click', function (e) {
    if (!armed || bar.contains(e.target)) return;
    e.preventDefault();
    e.stopPropagation();
    var text = window.prompt('Annotation for this spot:');
    if (text) {
      var list = load();
      list.push({
        target_selector: selectorFor(e.target),
        x: Math.round(e.pageX),
        y: Math.round(e.pageY),
        text: text,
        at: new Date().toISOString()
      });
      save(list);
      renderPins();
    }
    arm();
  }, true);

  document.getElementById('ga-export').addEventListener('click', function () {
    var blob = new Blob([JSON.stringify(load(), null, 2)],
      { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'annotations.json';
    a.click();
    URL.revokeObjectURL(a.href);
  });

  renderPins();
})();
