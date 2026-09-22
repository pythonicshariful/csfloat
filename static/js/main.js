/* =========================================================
   STATE
   ========================================================= */
const state = {
  profiles: 3,
  tabs:     2,
};

let _codeTimer = null;   // countdown interval
let _codeExpiry = 0;     // unix seconds when current code expires

/* =========================================================
   GET 2FA CODES
   ========================================================= */
async function getCodes() {
  const btn     = document.getElementById('getCodesBtn');
  const raw     = document.getElementById('cookieInput').value.trim();
  const panel   = document.getElementById('codesPanel');
  const grid    = document.getElementById('codesGrid');

  if (!raw) { toast('Paste accounts first', 'error'); return; }

  btn.textContent = '⏳ Loading…';
  btn.disabled = true;

  try {
    const res  = await fetch('/get_codes', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ cookies: raw }),
    });
    const data = await res.json();

    grid.innerHTML = data.codes.map(c => `
      <div class="code-chip">
        <span class="code-user">${escHtml(c.username)}</span>
        <span class="code-value">${escHtml(c.code)}</span>
        ${c.error ? `<span class="code-err">⚠ ${escHtml(c.error)}</span>` : ''}
      </div>
    `).join('');

    panel.classList.remove('hidden');
    startCodeTimer();
    log(`🔑 Generated ${data.codes.length} Steam Guard code(s)`, 'ok');
  } catch (err) {
    toast('Failed to get codes — is Flask running?', 'error');
  } finally {
    btn.textContent = '⚡ Get Codes';
    btn.disabled = false;
  }
}

function startCodeTimer() {
  if (_codeTimer) clearInterval(_codeTimer);

  // Steam codes align to 30-second UTC windows
  const now     = Math.floor(Date.now() / 1000);
  const secsLeft = 30 - (now % 30);
  _codeExpiry   = now + secsLeft;

  document.getElementById('timerVal').textContent = secsLeft;

  _codeTimer = setInterval(() => {
    const remaining = _codeExpiry - Math.floor(Date.now() / 1000);
    if (remaining <= 0) {
      clearInterval(_codeTimer);
      document.getElementById('timerVal').textContent = '0';
      // Auto-refresh the codes when window expires
      getCodes();
    } else {
      document.getElementById('timerVal').textContent = remaining;
    }
  }, 1000);
}

/* =========================================================
   COUNTER HELPERS
   ========================================================= */
function adjust(key, delta) {
  const min = 1, max = key === 'profiles' ? 20 : 30;
  state[key] = Math.min(max, Math.max(min, state[key] + delta));
  document.getElementById(`${key}Val`).textContent    = state[key];
  document.getElementById(`${key}Slider`).value       = state[key];
  updateSummary();
}

function syncSlider(key, val) {
  state[key] = parseInt(val, 10);
  document.getElementById(`${key}Val`).textContent = state[key];
  updateSummary();
}

function updateSummary() {
  const total = state.profiles * state.tabs;
  document.getElementById('totalTabsStat').textContent = total;
  document.getElementById('profilesStat').textContent  = state.profiles;
}

/* =========================================================
   COOKIE PARSER / PREVIEW
   ========================================================= */
function parseAccounts(raw) {
  return raw.trim().split('\n')
    .map(l => l.trim()).filter(Boolean)
    .map((line, i) => {
      const parts  = line.split(':::');
      const lp     = parts[0].split(':');
      const user   = lp[0] || '';
      const pass   = lp.slice(1).join(':') || '';
      return {
        index:          i + 1,
        username:       user,
        password:       pass,
        sharedSecret:   parts[1] || '',
        identitySecret: parts[2] || '',
      };
    });
}

function parseCookiesPreview() {
  const raw      = document.getElementById('cookieInput').value;
  const accounts = parseAccounts(raw);
  const preview  = document.getElementById('accountPreview');

  if (!accounts.length) { preview.classList.add('hidden'); return; }

  preview.innerHTML = accounts.map(a => `
    <div class="acc-chip">
      <div class="acc-idx">${a.index}</div>
      <div>
        <div class="acc-user">${escHtml(a.username)}</div>
        <div class="acc-meta">pass: ${a.password ? '••••' : '—'} &nbsp;·&nbsp; SS: ${a.sharedSecret ? '✓' : '—'} &nbsp;·&nbsp; IS: ${a.identitySecret ? '✓' : '—'}</div>
      </div>
      <div class="acc-ok">✓</div>
    </div>
  `).join('');
  preview.classList.remove('hidden');
}

function clearCookies() {
  document.getElementById('cookieInput').value = '';
  document.getElementById('accountPreview').classList.add('hidden');
  log('Cookie input cleared.', 'warn');
}

/* =========================================================
   LAUNCH
   ========================================================= */
async function launch() {
  const btn     = document.getElementById('launchBtn');
  const cookies = document.getElementById('cookieInput').value;
  const url     = document.getElementById('targetUrl').value.trim() || 'https://csfloat.com/db';
  const filterSort = document.getElementById('filterSort').value;
  const filterRarity = document.getElementById('filterRarity').value;
  const filterMinFloat = document.getElementById('filterMinFloat').value;
  const filterMaxFloat = document.getElementById('filterMaxFloat').value;
  const filterPaintSeed = document.getElementById('filterPaintSeed').value;
  const filterMinAge = document.getElementById('filterMinAge').value;
  const filterMaxAge = document.getElementById('filterMaxAge').value;
  const filterStatTrak = document.getElementById('filterStatTrak').checked;
  const filterSouvenir = document.getElementById('filterSouvenir').checked;
  const filterNormal = document.getElementById('filterNormal').checked;
  const filterStickers = document.getElementById('filterStickers').value;
  const filterCharm = document.getElementById('filterCharm').value;
  const filterSource = document.getElementById('filterSource').value;
  const filterSteamId = document.getElementById('filterSteamId').value;


  btn.disabled = true;
  setStatus('running', 'Running…');

  log(`▶ Launching ${state.profiles} profile(s) · ${state.tabs} tab(s) each → ${url}`, 'info');

  try {
    const res  = await fetch('/launch', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        profiles: state.profiles,
        tabs:     state.tabs,
        cookies:  cookies,
        url:      url,
        filterSort,
        filterRarity,
        filterMinFloat,
        filterMaxFloat,
        filterPaintSeed,
        filterMinAge,
        filterMaxAge,
        filterStatTrak,
        filterSouvenir,
        filterNormal,
        filterStickers,
        filterCharm,
        filterSource,
        filterSteamId
      }),
    });

    const data = await res.json();

    if (data.results) {
      data.results.forEach(r => {
        if (r.ok) {
          log(`✔ Profile ${r.profile} launched successfully`, 'ok');
        } else {
          log(`✘ Profile ${r.profile} failed: ${r.error}`, 'err');
        }
      });
    }

    const allOk = data.results && data.results.every(r => r.ok);
    const anyOk = data.results && data.results.some(r => r.ok);

    setStatus(allOk ? 'success' : anyOk ? 'success' : 'error',
              allOk ? 'Running'  : anyOk ? 'Partial'  : 'Error');
    toast(allOk
      ? `✔ ${data.launched} of ${data.total} profiles launched`
      : `⚠ ${data.launched} of ${data.total} launched`,
      allOk ? 'success' : 'error');

    log(`─── Done: ${data.launched}/${data.total} OK ───`, 'info');

  } catch (err) {
    log(`✘ Network error: ${err.message}`, 'err');
    setStatus('error', 'Error');
    toast('✘ Network error — is Flask running?', 'error');
  } finally {
    btn.disabled = false;
  }
}

/* =========================================================
   CLOSE ALL
   ========================================================= */
async function closeAll() {
  log('⏹ Closing all Chrome instances…', 'warn');
  try {
    await fetch('/close_all', { method: 'POST' });
    log('✔ All windows closed.', 'ok');
    setStatus('idle', 'Idle');
    toast('All windows closed', 'success');
  } catch (err) {
    log(`✘ ${err.message}`, 'err');
  }
}

/* =========================================================
   LOG
   ========================================================= */
function log(msg, type = 'info') {
  const out  = document.getElementById('logOutput');
  const ph   = out.querySelector('.log-placeholder');
  if (ph) ph.remove();

  const now  = new Date().toLocaleTimeString('en-GB', { hour12: false });
  const line = document.createElement('div');
  line.className = 'log-line';
  line.innerHTML = `<span class="log-ts">${now}</span><span class="log-${type}">${escHtml(msg)}</span>`;
  out.appendChild(line);
  out.scrollTop = out.scrollHeight;
}

function clearLog() {
  const out = document.getElementById('logOutput');
  out.innerHTML = '<div class="log-placeholder">Waiting for launch…</div>';
}

/* =========================================================
   STATUS
   ========================================================= */
function setStatus(type, label) {
  const badge = document.getElementById('globalStatus');
  const dot   = badge.querySelector('.status-dot');
  dot.className = `status-dot ${type}`;
  badge.querySelector('span:last-child').textContent = label;
}

/* =========================================================
   TOAST
   ========================================================= */
function toast(msg, type = 'info') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className   = `toast ${type}`;
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => el.classList.add('hidden'), 3500);
}

/* =========================================================
   UTILS
   ========================================================= */
function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

/* =========================================================
   INIT
   ========================================================= */
updateSummary();
