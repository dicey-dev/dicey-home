/* Interactive design study. No browser, terminal, media, or system commands run. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const themes = {
    miasma: {bg: '#222222', deep: '#191919', surface: '#2c2c2c', fg: '#c2c2b0', accent: '#78824b', 'on-accent': '#080b06', warm: '#b36d43'},
    tokyo: {bg: '#1a1b26', deep: '#14151e', surface: '#24283b', fg: '#c0caf5', accent: '#7aa2f7', 'on-accent': '#111b32', warm: '#e0af68'},
    catppuccin: {bg: '#1e1e2e', deep: '#181825', surface: '#313244', fg: '#cdd6f4', accent: '#cba6f7', 'on-accent': '#24152f', warm: '#fab387'},
    everforest: {bg: '#2d353b', deep: '#232a2e', surface: '#343f44', fg: '#d3c6aa', accent: '#a7c080', 'on-accent': '#202817', warm: '#dbbc7f'},
    paper: {bg: '#f4f1e8', deep: '#e9e5da', surface: '#e4e0d5', fg: '#333b36', accent: '#657547', 'on-accent': '#fffdf3', warm: '#976445'},
  };
  const storageKey = 'dicey-home-concept-v1';
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(storageKey) || '{}') || {}; } catch {}
  const tiles = $$('.tile[data-tile]');
  const state = {view: ['control', 'launcher', 'desktop'].includes(saved.view) ? saved.view : 'control', theme: themes[saved.theme] ? saved.theme : 'miasma', hidden: new Set(Array.isArray(saved.hidden) ? saved.hidden : []), demo: true, playing: true, track: 0, elapsed: 94, volume: 42, previousVolume: 42, focus: 1500, focusing: false};
  const tracks = [{title: 'A Walk', artist: 'Tycho · Dive', album: 'dive', duration: 316}, {title: 'Kerala', artist: 'Bonobo · Migration', album: 'migration', duration: 237}, {title: 'Open Eye Signal', artist: 'Jon Hopkins · Immunity', album: 'immunity', duration: 472}];
  const apps = [
    {name: 'Editor', detail: 'Neovim · return to your workspace', icon: 'editor', command: 'omarchy launch editor'},
    {name: 'Terminal', detail: 'Your shell, a little closer', icon: 'terminal', command: 'omarchy launch terminal'},
    {name: 'Browser', detail: 'Your default browser & search engine', icon: 'browser', command: 'omarchy launch browser'},
    {name: 'Activity monitor', detail: 'btop · the pulse of your machine', icon: 'terminal', action: 'monitor'},
    {name: 'Files', detail: 'Folders, projects, and everything else', icon: 'folder', command: 'omarchy launch filemanager'},
    {name: 'Dicey Home', detail: 'Your start surface, expanded', icon: 'grid', action: 'control'},
  ];
  const labels = {editor: 'Editor', terminal: 'Terminal', browser: 'Browser', files: 'Files', notes: 'Notes', activity: 'Activity / btop', network: 'Network traffic', storage: 'Storage / ncdu', media: 'Media player', volume: 'Output volume', focus: 'Focus timer', clock: 'Clock & calendar', quiet: 'Quiet mode', wifi: 'Wi-Fi', appearance: 'Appearance', lock: 'Lock session'};
  let toastTimer;
  let samples = [22, 27, 18, 24, 34, 26, 29, 22, 31, 24, 39, 26, 32, 24, 30, 27, 36, 24, 29, 22, 25];

  function persist() { try { localStorage.setItem(storageKey, JSON.stringify({view: state.view, theme: state.theme, hidden: [...state.hidden]})); } catch {} }
  function toast(message) { $('#toast').textContent = message; $('#toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').classList.remove('visible'), 3000); }
  function theme(value) { state.theme = themes[value] ? value : 'miasma'; Object.entries(themes[state.theme]).forEach(([key, color]) => document.documentElement.style.setProperty(`--${key}`, color)); document.body.dataset.theme = state.theme; document.documentElement.style.colorScheme = state.theme === 'paper' ? 'light' : 'dark'; $('#theme-select').value = state.theme; persist(); }
  function switchView(view, focus = false) { state.view = view; document.body.dataset.view = view; persist(); if (focus) requestAnimationFrame(() => (view === 'control' ? $('#home-search') : view === 'launcher' ? $('#launcher-search') : $('.reopen-button')).focus()); }
  function formatTime(seconds) { return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`; }
  function updateClock() { const now = new Date(); const time = now.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', hour12: false}); $('#bar-time').textContent = time; $('#tile-time').textContent = time; $('#bar-date').textContent = now.toLocaleDateString('en', {weekday: 'long'}); $('#long-date').textContent = now.toLocaleDateString('en', {weekday: 'long', day: 'numeric', month: 'long'}).toUpperCase(); $('#tile-day').textContent = now.toLocaleDateString('en', {weekday: 'long'}).toUpperCase(); $('#tile-date').textContent = now.toLocaleDateString('en', {day: 'numeric', month: 'long', year: 'numeric'}); }

  function filterTiles() {
    const query = $('#home-search').value.trim().toLowerCase();
    const answer = typeof calculate === 'function' ? calculate(query) : null;
    $('#calculation').hidden = answer === null;
    if (answer !== null) $('#calculation-answer').textContent = answer;
    let visible = 0;
    tiles.forEach(tile => { const show = !state.hidden.has(tile.dataset.tile) && (!query || tile.dataset.terms.includes(query)); tile.hidden = !show; if (show) visible++; });
    $$('.tile-group').forEach(group => { group.hidden = ![...group.querySelectorAll('.tile')].some(tile => !tile.hidden); });
    document.body.classList.toggle('is-filtering', Boolean(query));
    $('#empty-state').hidden = visible > 0 || answer !== null;
    $('#tile-canvas').hidden = visible === 0;
    $('#tile-count').textContent = tiles.length - state.hidden.size;
  }

  function openDialog(title, content, terminal = false) {
    $('#dialog-title').textContent = title;
    $('#dialog-content').replaceChildren();
    if (terminal) { const pre = document.createElement('pre'); pre.className = 'terminal-preview'; pre.textContent = content; $('#dialog-content').append(pre); }
    else { const line = document.createElement('div'); line.className = 'command-preview'; const prompt = document.createElement('span'); prompt.textContent = '❯'; const code = document.createElement('code'); code.textContent = content; line.append(prompt, code); const explanation = document.createElement('p'); explanation.className = 'dialog-callout'; explanation.textContent = 'In the native launcher, this tile would open the configured application. This HTML concept previews the interaction and command only.'; $('#dialog-content').append(line, explanation); }
    $('#tile-dialog').showModal();
  }

  function action(name) {
    if (name === 'control') return switchView('control', true);
    if (name === 'appearance') { $('#theme-select').focus(); try { $('#theme-select').showPicker(); } catch { toast('Choose a theme from the selector at the top.'); } return; }
    if (name === 'monitor') { openDialog('A terminal, with room to breathe.', `╭─ btop / CPU ───────────────────────────────────────────────────╮
│  Intel Core i7    8 cores / 16 threads       2.8 GHz     52°C    │
│                                                               │
│  CPU 0  ▐██████████░░░░░░░░░░░░░░░░░░▌ 32%                    │
│  CPU 1  ▐██████░░░░░░░░░░░░░░░░░░░░░░▌ 18%                    │
│  CPU 2  ▐████████░░░░░░░░░░░░░░░░░░░░▌ 24%                    │
│  CPU 3  ▐█████░░░░░░░░░░░░░░░░░░░░░░░▌ 16%                    │
╰───────────────────────────────────────────────────────────────╯
╭─ MEMORY ───────────────────────╮ ╭─ NETWORK ───────────────────╮
│  Used    8.4 GiB / 32 GiB      │ │  ↓ 2.4 MB/s   ↑ 320 KB/s   │
│  Cache   3.1 GiB               │ │  Interface: eth0            │
╰───────────────────────────────╯ ╰─────────────────────────────╯
  PID      PROGRAM          CPU%       MEM       STATE
  18721    chrome           12.4       1.8G      running
  10482    neovim            3.2       124M      running
   2219    quickshell        1.8        86M      sleeping
  23147    spotify           1.2       318M      sleeping

  [m] menu   [p] processes   [q] return to Dicey Home
  DESIGN STUDY · SIMULATED TELEMETRY`, true); return; }
    if (name === 'network') { openDialog('Traffic, without the noise.', `NETWORK / eth0                         CONNECTED

DOWN   ▂▁▂▃▆▄▂▃▅▇▃▁▂▅▆▃▂▃▆▄          2.4 MB/s
UP     ▁▁▂▁▃▂▁▁▂▃▁▁▂▁▃▂▁▁▂▁          320 KB/s

SESSION RECEIVED     842 MB
SESSION SENT         126 MB
LATENCY               12 ms

SIMULATED TELEMETRY / future native network widget`, true); return; }
    if (name === 'calendar') { const now = new Date(); openDialog('A little perspective.', now.toLocaleDateString('en', {weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'}) + '\n\n09:00    Deep work\n12:30    Step outside\n15:00    Build something beautiful\n\nILLUSTRATIVE AGENDA / no calendar integration', true); }
  }

  function renderCompact() {
    const query = $('#launcher-search').value.trim(); const container = $('#compact-results'); container.replaceChildren();
    const answer = typeof calculate === 'function' ? calculate(query) : null;
    const matches = answer !== null ? [{name: answer, detail: `${query} · click to copy answer`, icon: 'terminal', answer}] : apps.filter(app => `${app.name} ${app.detail}`.toLowerCase().includes(query.toLowerCase()));
    if (!matches.length) { const empty = document.createElement('p'); empty.className = 'dialog-callout'; empty.textContent = 'No matching applications in this design study.'; container.append(empty); }
    matches.forEach(app => { const button = document.createElement('button'); button.className = 'compact-row'; button.innerHTML = `<svg class="icon" aria-hidden="true"><use href="#i-${app.icon}"/></svg><span><strong></strong><small></small></span><span aria-hidden="true">↵</span>`; button.querySelector('strong').textContent = app.name; button.querySelector('small').textContent = app.detail; button.addEventListener('click', () => app.answer !== undefined ? copyAnswer(app.answer) : app.action ? action(app.action) : openDialog(app.name, app.command)); container.append(button); });
  }

  async function copyAnswer(answer) { try { await navigator.clipboard.writeText(answer); toast(`Copied ${answer}`); } catch { toast(`Answer: ${answer} · clipboard unavailable in this preview`); } }
  function mediaUI() { const track = tracks[state.track]; $('#track-title').textContent = track.title; $('#track-artist').textContent = track.artist; $('.art-title').textContent = track.album; $('#seek').max = track.duration; $('#seek').value = state.elapsed; $('#elapsed').textContent = formatTime(state.elapsed); $('#duration').textContent = formatTime(track.duration); $('#media-state').textContent = state.playing ? 'NOW PLAYING' : 'ON PAUSE'; $('#play-button').setAttribute('aria-label', state.playing ? 'Pause music' : 'Play music'); $('#play-button').setAttribute('aria-pressed', String(state.playing)); $('#play-icon').setAttribute('href', state.playing ? '#i-pause' : '#i-play'); document.body.classList.toggle('media-paused', !state.playing); }
  function changeTrack(delta) { state.track = (state.track + delta + tracks.length) % tracks.length; state.elapsed = 0; mediaUI(); }
  function volumeUI() { $('#volume').value = state.volume; $('#volume-number').textContent = state.volume; $('#mute-button').setAttribute('aria-pressed', String(state.volume === 0)); $('#mute-button').setAttribute('aria-label', state.volume === 0 ? 'Unmute audio' : 'Mute audio'); $('#volume-icon').setAttribute('href', state.volume === 0 ? '#i-mute' : '#i-volume'); }
  function focusUI() { $('#focus-clock').textContent = formatTime(state.focus); $('#focus-button').textContent = state.focusing ? 'Pause session Ⅱ' : state.focus < 1500 ? 'Resume session ↗' : 'Start session ↗'; }

  function navigation(event) {
    const direction = {ArrowLeft: [-1,0], ArrowRight: [1,0], ArrowUp: [0,-1], ArrowDown: [0,1]}[event.key];
    if (!direction || state.view !== 'control' || document.querySelector('dialog[open]') || /INPUT|SELECT|TEXTAREA/.test(event.target.tagName)) return;
    const candidates = $$('[data-nav]').filter(tile => !tile.hidden && tile.getClientRects().length);
    const current = event.target.closest('[data-nav]');
    if (!current) { if (candidates[0]) { event.preventDefault(); candidates[0].focus(); } return; }
    const box = current.getBoundingClientRect(); const origin = [box.x + box.width / 2, box.y + box.height / 2];
    const next = candidates.filter(tile => tile !== current).map(tile => { const rect = tile.getBoundingClientRect(); const dx = rect.x + rect.width / 2 - origin[0], dy = rect.y + rect.height / 2 - origin[1]; const along = dx * direction[0] + dy * direction[1]; const across = Math.abs(dx * direction[1] + dy * direction[0]); return {tile, along, score: along + across * 2.5}; }).filter(candidate => candidate.along > 10).sort((a,b) => a.score - b.score)[0];
    if (next) { event.preventDefault(); next.tile.focus(); next.tile.scrollIntoView({block: 'nearest', inline: 'nearest'}); }
  }

  $$('[data-switch]').forEach(button => button.addEventListener('click', () => switchView(button.dataset.switch, true)));
  $$('[data-app]').forEach(tile => tile.addEventListener('click', () => openDialog(tile.dataset.app, tile.dataset.command)));
  $$('[data-action]').forEach(tile => tile.addEventListener('click', () => action(tile.dataset.action)));
  $$('.dialog-close').forEach(button => button.addEventListener('click', () => $('#tile-dialog').close()));
  $$('.customize-close').forEach(button => button.addEventListener('click', () => $('#customize-dialog').close()));
  $('#home-search').addEventListener('input', filterTiles); $('#launcher-search').addEventListener('input', renderCompact);
  $('#theme-select').addEventListener('change', event => theme(event.target.value));
  $('#clear-search').addEventListener('click', () => { $('#home-search').value = ''; filterTiles(); $('#home-search').focus(); });
  $('#copy-answer').addEventListener('click', () => copyAnswer($('#calculation-answer').textContent));
  $('#play-button').addEventListener('click', () => { state.playing = !state.playing; mediaUI(); });
  $('#previous-track').addEventListener('click', () => changeTrack(-1)); $('#next-track').addEventListener('click', () => changeTrack(1));
  $('#seek').addEventListener('input', event => { state.elapsed = Number(event.target.value); mediaUI(); });
  $('#volume').addEventListener('input', event => { state.volume = Number(event.target.value); if (state.volume > 0) state.previousVolume = state.volume; volumeUI(); });
  $('#mute-button').addEventListener('click', () => { state.volume = state.volume === 0 ? state.previousVolume : 0; volumeUI(); });
  $('#focus-button').addEventListener('click', () => { state.focusing = !state.focusing; focusUI(); });
  $('#focus-reset').addEventListener('click', () => { state.focus = 1500; state.focusing = false; focusUI(); });
  [['quiet', false], ['wifi', true]].forEach(([name, initial]) => { let enabled = initial; $(`#${name}-button`).addEventListener('click', () => { enabled = !enabled; $(`#${name}-button`).setAttribute('aria-pressed', String(enabled)); $(`#${name}-label`).textContent = enabled ? 'On' : 'Off'; toast(`${name === 'quiet' ? 'Quiet mode' : 'Wi-Fi'} ${enabled ? 'on' : 'off'} · prototype state`); }); });
  $$('.workspace-number').forEach(button => button.addEventListener('click', () => { $$('.workspace-number').forEach(item => { item.classList.remove('active'); item.removeAttribute('aria-current'); }); button.classList.add('active'); button.setAttribute('aria-current', 'true'); toast(`Workspace ${button.textContent} · navigation preview`); }));
  $('#simulation-button').addEventListener('click', () => { state.demo = !state.demo; $('#simulation-button').setAttribute('aria-pressed', String(state.demo)); $('#simulation-button').innerHTML = `<span class="status-dot"></span> Demo ${state.demo ? 'running' : 'paused'}`; document.body.classList.toggle('demo-paused', !state.demo); });
  $('#customize-button').addEventListener('click', () => { const options = $('#tile-options'); options.replaceChildren(); tiles.forEach(tile => { const label = document.createElement('label'); label.className = 'tile-option'; const input = document.createElement('input'); input.type = 'checkbox'; input.checked = !state.hidden.has(tile.dataset.tile); input.addEventListener('change', () => { input.checked ? state.hidden.delete(tile.dataset.tile) : state.hidden.add(tile.dataset.tile); persist(); filterTiles(); }); label.append(input, document.createTextNode(labels[tile.dataset.tile])); options.append(label); }); $('#customize-dialog').showModal(); });
  $('#restore-tiles').addEventListener('click', () => { state.hidden.clear(); $$('#tile-options input').forEach(input => input.checked = true); persist(); filterTiles(); });
  $$('.tile[tabindex]').forEach(tile => tile.addEventListener('keydown', event => { if ((event.key === 'Enter' || event.key === ' ') && event.target === tile) { event.preventDefault(); tile.querySelector('button, input')?.focus(); } }));
  document.addEventListener('keydown', event => {
    const dialog = document.querySelector('dialog[open]');
    if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 'f') { event.preventDefault(); if (dialog) dialog.close(); switchView(state.view === 'control' ? 'launcher' : 'control', true); return; }
    if (event.key === 'Escape') { if (dialog) { event.preventDefault(); dialog.close(); return; } const input = state.view === 'control' ? $('#home-search') : $('#launcher-search'); if (input.value) { input.value = ''; state.view === 'control' ? filterTiles() : renderCompact(); } else switchView(state.view === 'control' ? 'launcher' : 'desktop', true); event.preventDefault(); return; }
    if (dialog) return;
    if (event.key === 'ArrowDown' && (event.target === $('#home-search') || event.target === $('#launcher-search'))) {
      const first = state.view === 'control' ? $$('[data-nav]').find(tile => !tile.hidden && tile.getClientRects().length) : $('.compact-row');
      if (first) { event.preventDefault(); first.focus(); }
      return;
    }
    if (state.view === 'launcher' && event.target.classList.contains('compact-row') && ['ArrowUp', 'ArrowDown'].includes(event.key)) {
      const rows = $$('.compact-row'); const index = rows.indexOf(event.target);
      const next = rows[index + (event.key === 'ArrowDown' ? 1 : -1)];
      event.preventDefault(); if (next) next.focus(); else if (event.key === 'ArrowUp') $('#launcher-search').focus();
      return;
    }
    if (event.key === '/' && !/INPUT|SELECT|TEXTAREA/.test(event.target.tagName)) { event.preventDefault(); if (state.view === 'desktop') switchView('launcher', true); else (state.view === 'control' ? $('#home-search') : $('#launcher-search')).focus(); }
    if (event.key === 'Enter' && event.target === $('#launcher-search')) { event.preventDefault(); $('.compact-row')?.click(); }
    if (event.key === 'Enter' && event.target === $('#home-search')) { if (!$('#calculation').hidden) copyAnswer($('#calculation-answer').textContent); else $$('[data-nav]').find(tile => !tile.hidden && tile.getClientRects().length)?.focus(); }
    navigation(event);
  });

  function telemetry() { if (!state.demo) return; const value = 18 + Math.round(Math.random() * 16); $('#cpu-number').textContent = value; $('#cpu-temp').textContent = 49 + Math.round(value / 7); samples.push(value); samples.shift(); const points = samples.map((sample,index) => `${index * 20},${60 - sample * 1.15}`).join(' '); $('#cpu-line').setAttribute('points', points); $('#cpu-area').setAttribute('d', `M0 60 L${points.replaceAll(' ', ' L')} L400 60Z`); const cores = [value + 7, Math.max(7, value - 6)]; ['one','two'].forEach((core,index) => { $(`#core-${core}`).style.setProperty('--usage', `${cores[index]}%`); $(`#core-${core}-number`).textContent = `${cores[index]}%`; }); }
  theme(state.theme); switchView(state.view); filterTiles(); renderCompact(); mediaUI(); volumeUI(); focusUI(); updateClock(); telemetry();
  setInterval(() => { updateClock(); if (state.demo && state.playing) { state.elapsed++; if (state.elapsed >= tracks[state.track].duration) changeTrack(1); else mediaUI(); } if (state.focusing && state.focus > 0) { state.focus--; focusUI(); if (!state.focus) { state.focusing = false; focusUI(); toast('Focus session complete. Time to take a breath.'); } } }, 1000);
  setInterval(telemetry, 1800);
})();
