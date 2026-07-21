/* inp-beacon.js — D15 field companion to the v5.2 lab INP-proxy.
 * <=2 KB, no dependencies: uses the Event Timing API directly, reports p75
 * of event durations to the local /beacon endpoint. Deploy on preview/prod
 * only; report field values as a SEPARATE line from the lab proxy.
 * Threshold: p75 <= 200 ms; a violation caps at ready_with_caveats (never blocks).
 */
(function () {
  if (!("PerformanceObserver" in window) ||
      !PerformanceObserver.supportedEntryTypes ||
      PerformanceObserver.supportedEntryTypes.indexOf("event") < 0) {
    window.__inpBeacon = { supported: false };
    return;
  }
  var durations = [];
  try {
    new PerformanceObserver(function (list) {
      list.getEntries().forEach(function (e) {
        if (e.duration >= 16) durations.push(Math.round(e.duration));
      });
    }).observe({ type: "event", durationThreshold: 16, buffered: true });
  } catch (err) { window.__inpBeacon = { supported: false }; return; }

  function p75(a) {
    if (!a.length) return 0;
    var s = a.slice().sort(function (x, y) { return x - y; });
    return s[Math.min(s.length - 1, Math.floor(s.length * 0.75))];
  }
  function flush() {
    if (!durations.length) return;
    var body = JSON.stringify({
      metric: "inp-field", p75: p75(durations), n: durations.length,
      url: location.pathname, at: Date.now()
    });
    if (navigator.sendBeacon) navigator.sendBeacon("/beacon", body);
    durations = [];
  }
  addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") flush();
  });
  addEventListener("pagehide", flush);
  window.__inpBeacon = { supported: true, flush: flush };
})();
