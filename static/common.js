/* Shared helpers for all three randomizer pages (crystal / yellow / emerald).
 *
 * Each page sets  window.GAME_KEY = "crystal" | "yellow" | "emerald"
 * BEFORE including this file; it namespaces the remembered-folder storage.
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

// ── Quick UX: remember last folders + copy-seed button ──────────────────────
(function(){
  function ready(fn){ document.readyState!=='loading' ? fn() : document.addEventListener('DOMContentLoaded', fn); }
  ready(function(){
    const GAME = window.GAME_KEY || 'game';
    ['srcDir','outDir'].forEach(function(id){
      const el = document.getElementById(id);
      if (!el) return;
      const key = 'legacyRand:'+GAME+':'+id;
      try { const saved = localStorage.getItem(key); if (saved && !el.value) el.value = saved; } catch(e){}
      const save = function(){ try { localStorage.setItem(key, el.value); } catch(e){} };
      el.addEventListener('change', save);
      el.addEventListener('input', save);
    });
    const seed = document.getElementById('seed');
    if (seed && !document.getElementById('copySeedBtn')) {
      const btn = document.createElement('button');
      btn.id = 'copySeedBtn'; btn.type = 'button'; btn.className = 'btn-dice';
      btn.textContent = '📋'; btn.title = 'Copy seed to clipboard';
      btn.style.marginLeft = '4px';
      btn.onclick = function(){
        const v = (seed.value || '').trim();
        if (!v) return;
        const flash = function(){ const o = btn.textContent; btn.textContent = '✓'; setTimeout(function(){ btn.textContent = o; }, 900); };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(v).then(flash).catch(function(){ try{ seed.select(); document.execCommand('copy'); }catch(e){} flash(); });
        } else { try{ seed.select(); document.execCommand('copy'); }catch(e){} flash(); }
      };
      const row = seed.closest('.rand-seed-row') || seed.parentElement;
      (row || seed.parentElement).appendChild(btn);
    }
  });
})();
