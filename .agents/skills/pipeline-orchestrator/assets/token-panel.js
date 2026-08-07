/* token-panel.js — the self-service panel (v7.2, П-4).
 *
 * The owner turns a knob and the artefact changes in the same second: no
 * assistant, no model, no dev server. "Doing it" becomes "saw it and kept it".
 *
 * This file contains NO design logic and NO contrast maths. Every knob and
 * every option it can offer was computed by `dops panel emit` from the skin
 * and handed over in `window.DOPS_PANEL_CONFIG`. That is deliberate:
 *
 *   - the WCAG formula lives in check-contrast.py and nowhere else [A.10];
 *   - an unsafe value is not warned about, it is unrepresentable — it is
 *     simply not in the list, even if this file has a bug;
 *   - artefacts open from file://, where fetching the skin is blocked, so the
 *     domain arrives as a <script>, which always works.
 *
 * No config -> no button, and the page is untouched. That is not degradation:
 * a panel without compiled tokens has no premise to run on.
 *
 * Embed AFTER the compiled stylesheet:
 *   <script src="./panel-config.js"></script>
 *   <script src=".../token-panel.js"></script>
 *
 * Keys: `t` opens/closes (pins took `a`), Esc closes.
 * Preview is inline CSS variables on <html>; nothing on disk is touched.
 * "Export" downloads token-delta.json for `dops panel apply`, the only door
 * back into tokens.json.
 */
(function () {
  'use strict';
  var CFG = window.DOPS_PANEL_CONFIG;
  if (!CFG || !CFG.knobs || !CFG.knobs.length) return;

  var KEY = 'dops-panel:' + location.pathname;
  var root = document.documentElement;
  var open = false;

  function load() {
    try {
      var raw = JSON.parse(localStorage.getItem(KEY) || '{}');
      return raw && typeof raw === 'object' && raw.changes ? raw : blank();
    } catch (e) { return blank(); }
  }
  function blank() {
    return {
      panel_version: CFG.panel_version, skin: CFG.skin,
      tokens_sha256: CFG.tokens_sha256, changes: []
    };
  }
  function save(d) { localStorage.setItem(KEY, JSON.stringify(d)); }

  var delta = load();
  /* A delta collected against a different skin is not ours: the paths may not
   * exist any more and `apply` would refuse it anyway. Dropping it here means
   * the owner is never left holding changes that cannot land. */
  if (delta.tokens_sha256 !== CFG.tokens_sha256) { delta = blank(); save(delta); }

  function knobById(id) {
    for (var i = 0; i < CFG.knobs.length; i++) {
      if (CFG.knobs[i].id === id) return CFG.knobs[i];
    }
    return null;
  }
  function changeFor(path) {
    for (var i = 0; i < delta.changes.length; i++) {
      if (delta.changes[i].path === path) return delta.changes[i];
    }
    return null;
  }
  function currentTheme() {
    return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  /* ---- preview -------------------------------------------------------- */
  /* Inline properties on <html> beat every selector, including the dark
   * layer's own [data-theme="dark"] block. So overrides are re-applied on
   * every theme switch and only the ones belonging to the visible theme are
   * written — otherwise a colour picked in the light theme would silently
   * leak into the dark one. */
  function cssFor(knob, option) {
    if (option.css) return option.css;
    var out = {};
    if (knob.css_var) out[knob.css_var] = option.literal || option.value;
    return out;
  }

  function repaint() {
    CFG.knobs.forEach(function (k) {
      Object.keys(cssFor(k, k.options[0] || {})).forEach(function (v) {
        root.style.removeProperty(v);
      });
      if (k.options) {
        k.options.forEach(function (o) {
          Object.keys(cssFor(k, o)).forEach(function (v) {
            root.style.removeProperty(v);
          });
        });
      }
    });
    var theme = currentTheme();
    delta.changes.forEach(function (ch) {
      var k = knobById(ch.knob);
      if (!k || (k.theme !== 'both' && k.theme !== theme)) return;
      var opt = null;
      k.options.forEach(function (o) {
        if (JSON.stringify(o.value) === JSON.stringify(ch.to)) opt = o;
      });
      if (!opt) return;
      var css = cssFor(k, opt);
      Object.keys(css).forEach(function (v) {
        root.style.setProperty(v, css[v]);
      });
    });
  }

  function pick(knob, option) {
    if (knob.kind === 'theme-toggle') {
      if (option.value === 'dark') root.setAttribute('data-theme', 'dark');
      else root.removeAttribute('data-theme');
      repaint();
      render();
      return;
    }
    var ch = changeFor(knob.path);
    if (JSON.stringify(option.value) === JSON.stringify(knob.current)) {
      /* back to what the skin already says — that is not a change */
      delta.changes = delta.changes.filter(function (c) { return c.path !== knob.path; });
    } else if (ch) {
      ch.to = option.value;
      ch.at = new Date().toISOString();
    } else {
      delta.changes.push({
        knob: knob.id, path: knob.path, from: knob.current, to: option.value,
        theme: knob.theme === 'both' ? 'both' : knob.theme,
        at: new Date().toISOString()
      });
    }
    save(delta);
    repaint();
    render();
  }

  function revert(path) {
    delta.changes = delta.changes.filter(function (c) { return c.path !== path; });
    save(delta);
    repaint();
    render();
  }

  function resetAll() {
    delta = blank();
    save(delta);
    root.removeAttribute('data-theme');
    repaint();
    render();
  }

  /* ---- chrome --------------------------------------------------------- */
  var bar = document.createElement('div');
  bar.id = 'dops-panel';
  bar.style.cssText = 'position:fixed;right:190px;bottom:12px;z-index:99999;' +
    'font:13px system-ui,sans-serif;';
  document.body.appendChild(bar);

  /* Ф-1: sit clear of the pins bar by MEASURING it, not by remembering how
   * wide it was. `right:190px` was chosen when that bar held three controls;
   * it has four now, and the panel landed on top of Export/Import — the
   * closed button overlapping, the open panel swallowing the whole bar and
   * intercepting its clicks. A number describing another element's size is
   * wrong the moment that element changes, so it is not a number any more.
   * Stacking the panel above the bar was the other candidate and is worse:
   * the pins feed already lives there (`bottom:52px`), so the fix would have
   * moved the collision one layer up instead of removing it. */
  var GAP = 12;
  function keepClear() {
    var pins = document.getElementById('ga-bar');
    var width = pins ? Math.ceil(pins.getBoundingClientRect().width) : 0;
    bar.style.right = (width ? width + GAP * 2 : GAP) + 'px';
  }
  keepClear();
  window.addEventListener('resize', keepClear);
  window.addEventListener('load', keepClear);
  /* The bar is written by another script that may load after this one, and it
   * re-renders whenever a pin is added. Watching it is the only way the
   * clearance stays true without the two files agreeing on a constant. */
  if (window.ResizeObserver) {
    var watch = new ResizeObserver(keepClear);
    var attach = function () {
      var pins = document.getElementById('ga-bar');
      if (pins) { watch.observe(pins); return true; }
      return false;
    };
    if (!attach()) {
      var tries = 0;
      var poll = setInterval(function () {
        if (attach() || ++tries > 20) clearInterval(poll);
      }, 100);
    }
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function render() {
    if (!open) {
      bar.innerHTML = '<button id="dops-panel-open" style="padding:6px 10px;' +
        'border:1px solid #999;background:#fff;border-radius:6px;' +
        'cursor:pointer">Tokens (t)' +
        (delta.changes.length ? ' · ' + delta.changes.length : '') + '</button>';
      bar.querySelector('#dops-panel-open').addEventListener('click', function () {
        open = true; render();
      });
      return;
    }
    var theme = currentTheme();
    var html = '<div style="width:320px;max-height:70vh;overflow:auto;' +
      'background:#fff;color:#111;border:1px solid #999;border-radius:8px;' +
      'padding:10px 12px;box-shadow:0 6px 24px rgba(0,0,0,.18)">' +
      '<div style="display:flex;justify-content:space-between;align-items:center">' +
      '<strong>Tokens</strong>' +
      '<button data-act="close" style="border:0;background:none;cursor:pointer;' +
      'font-size:16px">×</button></div>';

    CFG.knobs.forEach(function (k) {
      if (k.kind !== 'theme-toggle' && k.theme !== 'both' && k.theme !== theme) return;
      var ch = changeFor(k.path);
      var active = ch ? ch.to : (k.kind === 'theme-toggle' ? theme : k.current);
      html += '<div style="margin:10px 0 4px"><div style="font-size:12px;' +
        'color:#555">' + esc(k.label) + '</div><div style="display:flex;' +
        'flex-wrap:wrap;gap:4px;margin-top:4px">';
      k.options.forEach(function (o, i) {
        var on = JSON.stringify(o.value) === JSON.stringify(active);
        var swatch = k.kind === 'color'
          ? '<span style="display:inline-block;width:10px;height:10px;' +
            'border-radius:2px;border:1px solid #0002;vertical-align:-1px;' +
            'background:' + esc(o.literal || '') + '"></span> ' : '';
        html += '<button data-knob="' + esc(k.id) + '" data-opt="' + i + '" ' +
          'title="' + esc(o.contrast || '') + '" style="padding:3px 7px;' +
          'border:1px solid ' + (on ? '#111' : '#ccc') + ';border-radius:5px;' +
          'background:' + (on ? '#f0efed' : '#fff') + ';cursor:pointer;' +
          'font:12px system-ui">' + swatch + esc(o.label) +
          (o.contrast ? ' <span style="color:#666">' + esc(o.contrast) +
            '</span>' : '') + '</button>';
      });
      html += '</div></div>';
    });

    html += '<hr style="border:0;border-top:1px solid #eee;margin:10px 0">';
    if (delta.changes.length) {
      html += '<div style="font-size:12px;color:#555;margin-bottom:4px">' +
        delta.changes.length + ' change(s)</div>';
      delta.changes.forEach(function (c) {
        html += '<div style="display:flex;justify-content:space-between;gap:6px;' +
          'font:11px/1.5 ui-monospace,monospace;padding:2px 0">' +
          '<span>' + esc(c.path.split('.').pop()) + '</span>' +
          '<button data-revert="' + esc(c.path) + '" style="border:0;' +
          'background:none;color:#b91c1c;cursor:pointer;font:11px system-ui">' +
          'откатить</button></div>';
      });
    } else {
      html += '<div style="font-size:12px;color:#777">Ничего не изменено</div>';
    }
    html += '<div style="display:flex;gap:6px;margin-top:10px">' +
      '<button data-act="export" style="flex:1;padding:5px;border:1px solid #999;' +
      'background:#fff;border-radius:6px;cursor:pointer">Export</button>' +
      '<button data-act="reset" style="flex:1;padding:5px;border:1px solid #999;' +
      'background:#fff;border-radius:6px;cursor:pointer">Сбросить всё</button>' +
      '</div><div style="font-size:10px;color:#888;margin-top:8px">' +
      'Применяется командой <code>dops panel apply</code> — только она пишет в ' +
      'tokens.json. Скин ' + esc(CFG.skin) + ' · ' +
      esc(String(CFG.tokens_sha256).slice(0, 8)) + '</div></div>';

    bar.innerHTML = html;
    bar.querySelectorAll('[data-knob]').forEach(function (b) {
      b.addEventListener('click', function () {
        var k = knobById(b.getAttribute('data-knob'));
        if (k) pick(k, k.options[parseInt(b.getAttribute('data-opt'), 10)]);
      });
    });
    bar.querySelectorAll('[data-revert]').forEach(function (b) {
      b.addEventListener('click', function () { revert(b.getAttribute('data-revert')); });
    });
    bar.querySelectorAll('[data-act]').forEach(function (b) {
      b.addEventListener('click', function () {
        var act = b.getAttribute('data-act');
        if (act === 'close') { open = false; render(); }
        if (act === 'reset') resetAll();
        if (act === 'export') exportDelta();
      });
    });
  }

  function exportDelta() {
    var out = {
      panel_version: CFG.panel_version, skin: CFG.skin,
      tokens_sha256: CFG.tokens_sha256,
      changes: delta.changes.map(function (c) {
        return { path: c.path, from: c.from, to: c.to, theme: c.theme, at: c.at };
      })
    };
    var blob = new Blob([JSON.stringify(out, null, 2)], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'token-delta.json';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  document.addEventListener('keydown', function (e) {
    if (/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
    if (e.key === 't') { open = !open; render(); }
    if (e.key === 'Escape' && open) { open = false; render(); }
  });

  repaint();
  render();
})();
