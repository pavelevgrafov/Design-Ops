/* gate-annotate.js — click-to-pin annotations (v7.2, П-1 "always-on").
 *
 * Was: pins on gate artifacts only. Now: pins on ANY artifact — skeleton,
 * landing, app — for the whole life of the project.
 *
 * Why this matters more than it looks: a comment is BORN in the artifact (the
 * owner is looking at the heading) and used to be expressed in chat — "that
 * blue button on the third screen, you know the one". Half the revision time
 * went into working out which element was meant. A pin carries selector +
 * viewport + position, so that negotiation disappears; and being
 * machine-readable, a pin can be ROUTED and tracked instead of discussed.
 *
 * Embed:
 *   <script src=".../gate-annotate.js"></script>
 * Zero dependencies, works from file://.
 *
 * Keys: `a` arms the next click, Esc disarms. Pins persist in localStorage
 * per page; "Export" downloads annotations.json for the sorting station
 * (tools/dops_pins.py).
 *
 * annotations.json (v7.2 — additive; every v6 field is still written):
 *   [{id, selector, target_selector, viewport, x, y, kind, text,
 *     created_at, at, status}]
 *   kind:   visual | copy | structure | question — the owner's own cheap
 *           prior for the classifier
 *   status: new | triaged | checked | clarify | rejected | duplicate |
 *           executing | applied
 *
 * П-3 closes the loop: "Import" reads back the checked pins.json, so the
 * checker's answer appears ON the element the owner was looking at — a
 * refusal explained in a chat somewhere else is a refusal the owner has to
 * go and find. Clicking a pin opens it; a pin waiting on the owner
 * (clarify / duplicate) takes their reply right there, keeps the old wording
 * in `supersedes`, and goes back to `new` for re-classification.
 *
 * `screenshot_crop` is deliberately absent: a page cannot screenshot itself
 * without a browser driver, and writing a path to a file that does not exist
 * would be worse than leaving the field out. The pipeline fills it when it
 * has playwright.
 */
(function () {
  'use strict';
  var KEY = 'dops-pins:' + location.pathname;
  var LEGACY = 'gate-annotations';
  var armed = false;

  var KINDS = ['visual', 'copy', 'structure', 'question'];
  var LANE_COLOR = { A: '#15803d', B: '#1d4ed8', C: '#b45309', D: '#7c3aed' };
  /* The status ribbon (П-3 §1.3). A pin's own colour outranks its lane
   * colour: what the owner needs to see first is whether this one is waiting
   * on THEM. */
  var STATUS_MARK = {
    'new': '⚪', triaged: '🔵', checked: '🔵', clarify: '❓',
    rejected: '🔴', duplicate: '❓', executing: '🟡', applied: '🟢'
  };
  var STATUS_COLOR = {
    clarify: '#b45309', duplicate: '#b45309', rejected: '#b91c1c',
    executing: '#a16207', applied: '#15803d'
  };
  var NEEDS_OWNER = { clarify: 1, duplicate: 1 };

  function load() {
    try {
      var raw = localStorage.getItem(KEY) || localStorage.getItem(LEGACY) || '[]';
      var list = JSON.parse(raw);
      return Array.isArray(list) ? list : [];
    } catch (e) { return []; }
  }
  function save(list) { localStorage.setItem(KEY, JSON.stringify(list)); }

  function nextId(list) {
    var n = 0;
    list.forEach(function (a) {
      var m = /^a-(\d+)$/.exec(a.id || '');
      if (m) { n = Math.max(n, parseInt(m[1], 10)); }
    });
    n += 1;
    return 'a-' + (n < 1000 ? ('000' + n).slice(-4) : String(n));
  }

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
    'font:13px system-ui,sans-serif;display:flex;gap:6px;align-items:center;';
  bar.innerHTML =
    '<span id="ga-count" style="padding:6px 8px;border-radius:6px;' +
    'background:#111;color:#fff"></span>' +
    '<button id="ga-arm" style="padding:6px 10px;border:1px solid #999;' +
    'background:#fff;border-radius:6px;cursor:pointer">Comment (a)</button>' +
    '<button id="ga-export" style="padding:6px 10px;border:1px solid #999;' +
    'background:#fff;border-radius:6px;cursor:pointer">Export</button>' +
    '<label id="ga-import" style="padding:6px 10px;border:1px solid #999;' +
    'background:#fff;border-radius:6px;cursor:pointer">Import' +
    '<input type="file" accept="application/json" style="display:none"></label>';
  document.body.appendChild(bar);

  function describe(a) {
    var c = a.check || {};
    var out = (a.lane ? '[lane ' + a.lane + '] ' : '') +
      (a.kind ? a.kind + ': ' : '') + a.text;
    if (a.status) out += '\n' + (STATUS_MARK[a.status] || '') + ' ' + a.status;
    if (c.reason) out += '\nwhy: ' + c.reason;
    (c.alternatives || []).forEach(function (alt) { out += '\nor:  ' + alt; });
    if (c.question) out += '\nask: ' + c.question;
    if (c.conflict_ref) out += '\nref: ' + c.conflict_ref;
    if (NEEDS_OWNER[a.status]) out += '\n\n(click the pin to answer)';
    return out;
  }

  /* A pin waiting on the owner takes their reply where the question was
   * asked. The old wording is kept, never overwritten: the checker has to be
   * able to see what changed. */
  function openPin(a, list) {
    if (!NEEDS_OWNER[a.status]) { window.alert(describe(a)); return; }
    var reply = window.prompt(describe(a) + '\n\nYour answer:', a.text || '');
    if (reply === null) return;
    a.supersedes = a.text;
    a.text = reply;
    a.status = 'new';
    a.answered_at = new Date().toISOString();
    delete a.check;
    save(list);
    renderPins();
  }

  function renderPins() {
    var old = document.querySelectorAll('.ga-pin');
    Array.prototype.forEach.call(old, function (p) { p.remove(); });
    var list = load();
    list.forEach(function (a, i) {
      var pin = document.createElement('div');
      pin.className = 'ga-pin';
      pin.textContent = String(i + 1);
      pin.title = describe(a);
      pin.style.cssText = 'position:absolute;left:' + (a.x - 10) + 'px;top:' +
        (a.y - 10) + 'px;width:20px;height:20px;border-radius:50%;' +
        'background:' + (STATUS_COLOR[a.status] || LANE_COLOR[a.lane] ||
          '#b91c1c') + ';color:#fff;' +
        'font:700 11px/20px system-ui;text-align:center;z-index:99998;' +
        'cursor:pointer;box-shadow:0 0 0 2px #fff;';
      pin.addEventListener('click', function (e) {
        e.preventDefault(); e.stopPropagation(); openPin(a, list);
      }, true);
      document.body.appendChild(pin);
    });
    var waiting = list.filter(function (a) { return NEEDS_OWNER[a.status]; }).length;
    document.getElementById('ga-count').textContent =
      (list.length ? list.length + ' pin' + (list.length > 1 ? 's' : '') : 'no pins') +
      (waiting ? ' · ' + waiting + ' need you' : '');
  }

  function setArmed(on) {
    armed = on;
    document.getElementById('ga-arm').style.background = armed ? '#fee2e2' : '#fff';
    document.body.style.cursor = armed ? 'crosshair' : '';
  }

  document.getElementById('ga-arm').addEventListener('click', function () {
    setArmed(!armed);
  });
  document.addEventListener('keydown', function (e) {
    if (/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
    if (e.key === 'a') setArmed(!armed);
    if (e.key === 'Escape') setArmed(false);
  });

  document.addEventListener('click', function (e) {
    if (!armed || bar.contains(e.target)) return;
    e.preventDefault();
    e.stopPropagation();
    var text = window.prompt('What is wrong with this element?');
    if (text) {
      var kind = (window.prompt(
        'Kind — ' + KINDS.join(' / ') + ' (Enter = visual):', 'visual') || 'visual');
      kind = kind.trim().toLowerCase();
      if (KINDS.indexOf(kind) === -1) kind = 'visual';
      var list = load();
      var selector = selectorFor(e.target);
      var now = new Date().toISOString();
      list.push({
        id: nextId(list),
        selector: selector,
        target_selector: selector,   /* v6 field name — annotations-log.py */
        viewport: window.innerWidth,
        x: Math.round(e.pageX),
        y: Math.round(e.pageY),
        kind: kind,
        text: text,
        created_at: now,
        at: now,                     /* v6 field name */
        status: 'new'
      });
      save(list);
      renderPins();
    }
    setArmed(false);
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

  /* Import: the checker's verdicts come back onto the element they are about.
   * Accepts either a raw annotations array or a dops pins.json report, and
   * merges by pin id — the owner's own x/y/selector are never overwritten by
   * a machine round-trip. */
  bar.querySelector('#ga-import input').addEventListener('change', function (e) {
    var file = e.target.files && e.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      var incoming;
      try { incoming = JSON.parse(reader.result); } catch (err) {
        window.alert('Import: not valid JSON'); return;
      }
      if (incoming && !Array.isArray(incoming) && Array.isArray(incoming.pins)) {
        incoming = incoming.pins;
      }
      if (!Array.isArray(incoming)) { window.alert('Import: expected a list of pins'); return; }
      var list = load();
      var byId = {};
      list.forEach(function (a) { if (a.id) byId[a.id] = a; });
      var merged = 0;
      incoming.forEach(function (n) {
        var a = n.id && byId[n.id];
        if (!a) { list.push(n); merged += 1; return; }
        ['lane', 'plan', 'status', 'check', 'duplicate_of'].forEach(function (k) {
          if (n[k] !== undefined) a[k] = n[k];
        });
        merged += 1;
      });
      save(list);
      renderPins();
      window.alert('Import: ' + merged + ' pin(s) updated from the checker');
    };
    reader.readAsText(file);
    e.target.value = '';
  });

  renderPins();
})();
