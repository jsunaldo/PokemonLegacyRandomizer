/* Shared helpers for all three randomizer pages (crystal / yellow / emerald).
 *
 * Each page sets  window.GAME_KEY = "crystal" | "yellow" | "emerald"
 * BEFORE including this file; it namespaces the remembered-folder storage
 * and lets a page reconnect to a job it started before a reload.
 */

// ── Duplicate-row helper ─────────────────────────────────────────────────────
// Ask how many duplicate copies to create. Returns a clamped count (1–99),
// or 0 if the user cancelled / entered something invalid.
function _askCopies() {
  const raw = prompt('How many copies? (1–99)', '1');
  if (raw === null) return 0;
  const n = parseInt(raw);
  if (isNaN(n) || n < 1) return 0;
  return Math.min(99, n);
}

// ── Donations: copy address + optional QR ───────────────────────────────────
function copyDonate(btn){
  const el=document.getElementById('btcLnAddr'); if(!el) return;
  const v=el.value;
  const flash=function(){ const o=btn.textContent; btn.textContent='✓ Copied'; setTimeout(function(){ btn.textContent=o; },1000); };
  if(navigator.clipboard&&navigator.clipboard.writeText){ navigator.clipboard.writeText(v).then(flash).catch(function(){ el.select(); try{document.execCommand('copy');}catch(e){} flash(); }); }
  else { el.select(); try{document.execCommand('copy');}catch(e){} flash(); }
}
(function(){
  function ready(fn){ document.readyState!=='loading' ? fn() : document.addEventListener('DOMContentLoaded', fn); }
  ready(function(){
    if(window.QRCode){
      const box=document.getElementById('btcQr');
      if(box){ try{ new QRCode(box,{text:'lightning:salmoncobra1@primal.net',width:160,height:160}); box.style.display='block'; }catch(e){} }
    }
  });
})();

// ── Presets + conflict warnings ──────────────────────────────────────────────
// Applies a preset config through the page's applySettings and refreshes the
// conflict box. Presets omit pcPokemon / item lists so they never wipe those.
function applyPreset(preset, name) {
  if (typeof applySettings === 'function') applySettings(preset, false);
  const note = document.getElementById('presetNote');
  if (note) { note.textContent = '✓ Applied: ' + name; setTimeout(function(){ note.textContent=''; }, 2500); }
  if (typeof updateConflictWarnings === 'function') updateConflictWarnings();
}

// Renders warning strings into #conflictBox (empty list clears it).
function renderConflicts(warnings) {
  const box = document.getElementById('conflictBox');
  if (!box) return;
  box.innerHTML = warnings.map(function(w){
    return '<div style="font-size:12px;color:#e6b84c;background:rgba(230,184,76,.08);' +
           'border:1px solid rgba(230,184,76,.3);border-radius:6px;padding:6px 10px;margin-top:6px">⚠️ ' + w + '</div>';
  }).join('');
}

// ── Job runner shared by all three pages ────────────────────────────────────
// Handles: starting a job, streaming the log, showing the phase, the result
// panel (seed / ROM path / Reveal in Finder), reconnecting after a reload,
// and warning before the tab is closed mid-build.
const PLR = (function () {
  let logOffset = 0, timer = null, running = false, lastPhase = '', platform = '';

  const PHASES = {
    starting:    'Starting…',
    parsing:     'Parsing source files…',
    randomizing: 'Randomizing…',
    writing:     'Writing randomized source…',
    building:    'Building ROM — this can take a few minutes…',
    done:        'Done!',
  };

  function $(id) { return document.getElementById(id); }
  function els() {
    return {
      btn:     $('randBtn') || $('btn-randomize'),
      spinner: $('spinner'),
      status:  $('statusText'),
      log:     $('log-box'),
      toggle:  $('logToggle') || document.querySelector('.log-toggle'),
      result:  $('resultBox'),
      seed:    $('seed'),
    };
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function gameKey() { return window.GAME_KEY || 'game'; }

  function ensureLogVisible() {
    const { log, toggle } = els();
    if (!log) return;
    const hidden = log.style.display === 'none' || getComputedStyle(log).display === 'none';
    if (hidden && toggle) toggle.click();
  }
  function appendLog(lines) {
    const { log } = els();
    if (!log || !lines || !lines.length) return;
    log.textContent += lines.join('\n') + '\n';
    log.scrollTop = log.scrollHeight;
  }
  function clearLog() {
    const { log } = els();
    if (log) log.textContent = '';
    logOffset = 0;
  }
  function setStatus(msg, kind) {
    const { status } = els();
    if (!status) return;
    status.textContent = msg;
    status.style.color = kind === 'error' ? 'var(--red)' : kind === 'ok' ? 'var(--green)' : 'var(--muted)';
    status.title = '';
  }
  function setRunning(on, msg) {
    running = on;
    const { btn, spinner } = els();
    if (btn) btn.disabled = on;
    if (spinner) spinner.style.display = on ? 'block' : 'none';
    if (msg) setStatus(msg);
  }
  function hideResult() {
    const { result } = els();
    if (result) { result.style.display = 'none'; result.innerHTML = ''; }
  }

  function showResult(st) {
    const { result, seed } = els();
    if (!result) return;
    const rows = [];
    if (st.kind === 'fetch' && !st.error) {
      rows.push('<div class="plr-result-title plr-ok">✅ ' + 'Source code ready' + '</div>');
      if (st.source_dir)
        rows.push('<div class="plr-result-row"><span>Source</span><code>' + esc(st.source_dir) + '</code></div>');
      rows.push('<div class="plr-hint">The Source Directory field has been filled in. Now pick an Output Directory (a new, empty folder) and click Randomize.</div>');
      result.innerHTML = rows.join('');
      result.style.display = 'block';
      return;
    }
    if (st.error) {
      const lines = String(st.error).split('\n');
      rows.push('<div class="plr-result-title plr-err">❌ ' + esc(lines[0]) + '</div>');
      const rest = lines.slice(1).join('\n').trim();
      if (rest) rows.push('<pre class="plr-result-pre">' + esc(rest) + '</pre>');
      rows.push('<div class="plr-result-actions">' +
                '<button type="button" class="btn-secondary" onclick="PLR.showLogNow()">Show full log</button>' +
                '<span class="plr-hint">Your source folder was not touched. Fix the problem above and click Randomize again.</span>' +
                '</div>');
    } else {
      rows.push('<div class="plr-result-title plr-ok">✅ ' + (st.built ? 'ROM built successfully' : 'Randomized source saved') + '</div>');
      if (st.seed !== undefined && st.seed !== null)
        rows.push('<div class="plr-result-row"><span>Seed</span><code>' + esc(st.seed) + '</code></div>');
      if (st.rom_path)
        rows.push('<div class="plr-result-row"><span>ROM</span><code>' + esc(st.rom_path) + '</code></div>');
      if (st.out_dir)
        rows.push('<div class="plr-result-row"><span>Output</span><code>' + esc(st.out_dir) + '</code></div>');
      const acts = [];
      const mac = platform === 'darwin';
      if (st.rom_path)
        acts.push('<button type="button" class="btn-secondary" onclick="PLR.reveal(\'rom\')">' + (mac ? '📂 Reveal ROM in Finder' : '📂 Show ROM') + '</button>');
      if (st.out_dir)
        acts.push('<button type="button" class="btn-secondary" onclick="PLR.reveal(\'out\')">📁 Open output folder</button>');
      if (st.seed !== undefined && st.seed !== null)
        acts.push('<button type="button" class="btn-secondary" onclick="PLR.copyText(\'' + esc(String(st.seed)) + '\', this)">📋 Copy seed</button>');
      rows.push('<div class="plr-result-actions">' + acts.join('') + '</div>');
      if (!st.built)
        rows.push('<div class="plr-hint">To compile it yourself, open Terminal in the output folder and run <code>make</code>.</div>');
      rows.push('<div class="plr-hint"><code>spoiler_log.txt</code> and <code>settings_used.json</code> are saved in the output folder — attach settings_used.json to any bug report.</div>');
    }
    result.innerHTML = rows.join('');
    result.style.display = 'block';
    // A blank/auto seed: show the one the server actually used.
    if (seed && st.seed !== undefined && st.seed !== null && !String(seed.value).trim()) seed.value = st.seed;
  }

  function finish(st) {
    if (timer) { clearInterval(timer); timer = null; }
    setRunning(false);
    if (st.kind === 'fetch' && !st.error && st.source_dir) {
      const src = $('srcDir'), out = $('outDir');
      if (src) { src.value = st.source_dir; src.dispatchEvent(new Event('input')); }
      if (out && !out.value.trim() && st.suggested_out) { out.value = st.suggested_out; out.dispatchEvent(new Event('input')); }
      setStatus('Source ready — now choose an Output Directory and click Randomize.', 'ok');
      showResult(st);
      return;
    }
    if (st.error) {
      setStatus('Error: ' + String(st.error).split('\n')[0], 'error');
      const { status } = els(); if (status) status.title = st.error;
    } else {
      setStatus(st.built ? 'Done! ✅  ROM built.' : 'Done! ✅  Randomized source saved.', 'ok');
    }
    showResult(st);   // rendered directly under the Randomize button — no auto-scroll
  }

  async function pollOnce() {
    try {
      const [lr, sr] = await Promise.all([
        fetch('/api/log?since=' + logOffset),
        fetch('/api/status'),
      ]);
      const ld = await lr.json();
      const st = await sr.json();
      if (ld.lines && ld.lines.length) { appendLog(ld.lines); logOffset = ld.total; }
      if (st.platform) platform = st.platform;
      if (st.phase && st.phase !== lastPhase && !st.done) {
        lastPhase = st.phase;
        setStatus(PHASES[st.phase] || st.phase);
      }
      if (st.done || !st.running) finish(st);
    } catch (e) { /* server momentarily busy — try again next tick */ }
  }

  async function begin(endpoint, payload) {
    hideResult();
    clearLog();
    ensureLogVisible();
    lastPhase = '';
    setRunning(true, 'Starting…');
    let d;
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      d = await res.json();
    } catch (e) {
      setRunning(false);
      setStatus('Could not reach the randomizer server — is the app still running?', 'error');
      return false;
    }
    if (!d.ok) {
      setRunning(false);
      setStatus('Error: ' + (d.error || 'Unknown'), 'error');
      alert('Error: ' + (d.error || 'Unknown'));
      return false;
    }
    timer = setInterval(pollOnce, 700);
    return true;
  }

  // Reconnect to a job belonging to this page after a reload / navigation.
  async function resume() {
    try {
      const st = await (await fetch('/api/status')).json();
      if (st.platform) platform = st.platform;
      if (st.game !== gameKey()) return;
      if (!st.running && !st.done) return;
      const ld = await (await fetch('/api/log?since=0')).json();
      clearLog();
      appendLog(ld.lines || []);
      logOffset = ld.total || 0;
      if (st.running) {
        ensureLogVisible();
        lastPhase = st.phase || '';
        setRunning(true, PHASES[st.phase] || 'Reconnected — job still running…');
        timer = setInterval(pollOnce, 700);
      } else {
        finish(st);
      }
    } catch (e) { /* no server yet */ }
  }

  async function reveal(what) {
    try {
      const d = await (await fetch('/api/reveal', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ what }),
      })).json();
      if (!d.ok) alert(d.error || 'Could not open the location.');
    } catch (e) { alert('Could not open the location: ' + e); }
  }

  function copyText(text, btn) {
    const flash = () => { if (!btn) return; const o = btn.textContent; btn.textContent = '✓ Copied'; setTimeout(() => btn.textContent = o, 900); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(flash).catch(flash);
    else flash();
  }

  function showLogNow() {
    ensureLogVisible();
    const { log } = els();
    if (log) { log.scrollIntoView({ block: 'end', behavior: 'smooth' }); log.scrollTop = log.scrollHeight; }
  }

  function isRunning() { return running; }

  // "Get source" button: clone the game's Legacy repo into ~/Pokemon Legacy Sources
  async function fetchSource() {
    if (running) return;
    const game = gameKey();
    await begin('/api/fetch_source', { game });
    setStatus('Downloading the ' + game + ' Legacy source from GitHub…');
  }

  return { begin, resume, reveal, copyText, showLogNow, appendLog, setStatus, setRunning, isRunning, els, fetchSource };
})();

// ── Page wiring: styles, remembered folders/tab, copy-seed, seed hygiene ───
(function(){
  function ready(fn){ document.readyState!=='loading' ? fn() : document.addEventListener('DOMContentLoaded', fn); }

  // Result-panel styles (shared so the three pages stay identical)
  const css = document.createElement('style');
  css.textContent = `
    .plr-result{width:100%;max-width:700px;margin-top:6px;background:var(--card,#1a2744);border:1px solid var(--border,#243561);
      border-radius:10px;padding:14px 18px;font-size:13px;text-align:left}
    .plr-result-title{font-weight:700;font-size:14px;margin-bottom:8px}
    .plr-ok{color:var(--green,#4caf7d)} .plr-err{color:var(--red,#e94560)}
    .plr-result-row{display:flex;gap:10px;align-items:baseline;margin:4px 0;color:var(--muted,#7a8ba8)}
    .plr-result-row span{min-width:56px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em}
    .plr-result-row code{word-break:break-all;color:var(--text,#dce3f0);font-size:12px}
    .plr-result-pre{white-space:pre-wrap;font-size:11.5px;color:var(--muted,#7a8ba8);margin:6px 0;max-height:180px;overflow:auto;
      background:var(--input-bg,#0d1b35);border:1px solid var(--border,#243561);border-radius:6px;padding:8px}
    .plr-result-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;align-items:center}
    .plr-result-actions .btn-secondary{font-size:12px;padding:6px 12px}
    .plr-hint{font-size:11.5px;color:var(--muted,#7a8ba8);margin-top:8px;line-height:1.5}
    .plr-version{position:fixed;right:10px;bottom:6px;font-size:10.5px;color:var(--muted,#7a8ba8);opacity:.7;pointer-events:none}
    .plr-paths-hint{grid-column:1 / -1;font-size:11.5px;color:var(--muted,#7a8ba8);line-height:1.5;margin-top:2px}
    .plr-paths-hint strong{color:var(--text,#dce3f0);font-weight:600}
  `;
  document.head.appendChild(css);

  ready(function(){
    const GAME = window.GAME_KEY || 'game';

    // Remember the last-used folders per game
    ['srcDir','outDir'].forEach(function(id){
      const el = document.getElementById(id);
      if (!el) return;
      const key = 'legacyRand:'+GAME+':'+id;
      try { const saved = localStorage.getItem(key); if (saved && !el.value) el.value = saved; } catch(e){}
      const save = function(){ try { localStorage.setItem(key, el.value); } catch(e){} };
      el.addEventListener('change', save);
      el.addEventListener('input', save);
    });

    // "Get source" button + a one-line explanation under the directory fields
    const srcEl = document.getElementById('srcDir');
    const srcRow = srcEl && srcEl.closest('.input-row');
    if (srcRow && !document.getElementById('getSourceBtn')) {
      const b = document.createElement('button');
      b.id = 'getSourceBtn'; b.type = 'button'; b.className = 'btn-secondary';
      b.textContent = '⬇ Get source';
      b.title = 'Download the Legacy source code from GitHub into ~/Pokemon Legacy Sources (one-time)';
      b.onclick = function(){ PLR.fetchSource(); };
      srcRow.appendChild(b);
    }
    const paths = document.querySelector('.paths');
    if (paths && !document.getElementById('pathsHint')) {
      const h = document.createElement('div');
      h.id = 'pathsHint'; h.className = 'plr-paths-hint';
      h.innerHTML = '<strong>Source</strong> = the Legacy hack\'s <em>source-code</em> repo (the folder with the Makefile) — not a ROM file or ROM folder. ' +
                    'No copy yet? Click <strong>Get source</strong>. &nbsp; <strong>Output</strong> = a new, empty folder; the ROM is built there.';
      paths.appendChild(h);
    }

    // Seed field: digits only, plus a copy button
    const seed = document.getElementById('seed');
    if (seed) {
      seed.setAttribute('inputmode', 'numeric');
      seed.addEventListener('input', function(){
        const clean = seed.value.replace(/[^0-9]/g, '');
        if (clean !== seed.value) seed.value = clean;
      });
      if (!document.getElementById('copySeedBtn')) {
        const btn = document.createElement('button');
        btn.id = 'copySeedBtn'; btn.type = 'button'; btn.className = 'btn-dice';
        btn.textContent = '📋'; btn.title = 'Copy seed to clipboard';
        btn.style.marginLeft = '4px';
        btn.onclick = function(){
          const v = (seed.value || '').trim();
          if (!v) return;
          PLR.copyText(v, btn);
        };
        const row = seed.closest('.rand-seed-row') || seed.parentElement;
        (row || seed.parentElement).appendChild(btn);
      }
    }

    // Remember the active tab per game, and wrap the page's showTab
    const tabKey = 'legacyRand:'+GAME+':tab';
    if (typeof window.showTab === 'function') {
      const orig = window.showTab;
      window.showTab = function(name, btn){
        orig(name, btn);
        try { localStorage.setItem(tabKey, name); } catch(e){}
      };
      try {
        const saved = localStorage.getItem(tabKey);
        if (saved) {
          const btn = Array.from(document.querySelectorAll('.tab-btn'))
            .find(b => (b.getAttribute('onclick')||'').indexOf("showTab('"+saved+"'") >= 0);
          if (btn) orig(saved, btn);
        }
      } catch(e){}
    }

    // Version badge
    fetch('/api/version').then(r => r.json()).then(d => {
      if (!d || !d.version) return;
      const v = document.createElement('div');
      v.className = 'plr-version'; v.textContent = 'v' + d.version;
      document.body.appendChild(v);
    }).catch(function(){});

    // Don't lose a running build by closing the tab
    window.addEventListener('beforeunload', function(e){
      if (PLR.isRunning()) { e.preventDefault(); e.returnValue = ''; }
    });

    // Reconnect to a job that is still running (or just finished)
    PLR.resume();
  });
})();
