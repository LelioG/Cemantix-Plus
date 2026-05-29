const els = {
  modeSwitch: document.getElementById('modeSwitch'),
  currentModeLabel: document.getElementById('currentModeLabel'),
  secretMask: document.getElementById('secretMask'),
  guessCount: document.getElementById('guessCount'),
  engineLabel: document.getElementById('engineLabel'),
  displayNameInput: document.getElementById('displayNameInput'),
  saveProfileBtn: document.getElementById('saveProfileBtn'),
  customRow: document.getElementById('customRow'),
  customSecretInput: document.getElementById('customSecretInput'),
  startCustomBtn: document.getElementById('startCustomBtn'),
  gameMeta: document.getElementById('gameMeta'),
  guessInput: document.getElementById('guessInput'),
  guessBtn: document.getElementById('guessBtn'),
  hintBtn: document.getElementById('hintBtn'),
  newGameBtn: document.getElementById('newGameBtn'),
  shareBtn: document.getElementById('shareBtn'),
  messageBox: document.getElementById('messageBox'),
  statGrid: document.getElementById('statGrid'),
  hintCounter: document.getElementById('hintCounter'),
  hintList: document.getElementById('hintList'),
  leaderboardMeta: document.getElementById('leaderboardMeta'),
  leaderboardList: document.getElementById('leaderboardList'),
  guessTable: document.getElementById('guessTable'),
  guessRowTemplate: document.getElementById('guessRowTemplate'),
};

const pageMode = document.body.dataset.initialMode || 'daily';

const state = {
  user: null,
  currentMode: pageMode,
  game: null,
  stats: null,
  leaderboard: null,
  engine: null,
  modes: {},
};

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || 'Requête échouée.');
  }
  return payload;
}

function setMessage(text, tone = 'neutral') {
  els.messageBox.textContent = text || '';
  els.messageBox.dataset.tone = tone;
}

function applyPayload(payload) {
  if (payload.user) state.user = payload.user;
  if (payload.current_mode) state.currentMode = payload.current_mode;
  if (payload.game) state.game = payload.game;
  if (payload.stats) state.stats = payload.stats;
  if (payload.leaderboard) state.leaderboard = payload.leaderboard;
  if (payload.engine) state.engine = payload.engine;
  if (payload.modes) state.modes = payload.modes;
  render();
}

function render() {
  renderModes();
  renderProfile();
  renderGame();
  renderStats();
  renderHints();
  renderLeaderboard();
  renderGuesses();
}

function renderModes() {
  els.currentModeLabel.textContent = state.currentMode;
  els.customRow.style.display = state.currentMode === 'custom' ? 'grid' : 'none';
  [...els.modeSwitch.querySelectorAll('[data-mode]')].forEach((button) => {
    const mode = button.dataset.mode;
    const enabled = state.modes[mode] !== false;
    button.disabled = !enabled;
    button.classList.toggle('active', mode === state.currentMode);
  });
}

function renderProfile() {
  if (state.user) {
    els.displayNameInput.value = state.user.display_name || '';
  }
}

function renderGame() {
  if (!state.game) {
    return;
  }
  els.secretMask.textContent = state.game.secret_mask;
  els.guessCount.textContent = state.game.guess_count;
  els.engineLabel.textContent = state.engine?.name || 'n/a';

  const dailyTag = state.game.daily_date ? ` • ${state.game.daily_date}` : '';
  const winTag = state.game.won ? ' • gagné' : '';
  els.gameMeta.textContent = `${state.game.mode}${dailyTag} • ${state.game.guess_count} essai(s) • ${state.game.hints_used} indice(s)${winTag}`;

  els.hintBtn.disabled = state.game.won || state.game.hints.length >= state.game.available_hints;
  els.guessBtn.disabled = state.game.won;
  els.guessInput.disabled = state.game.won;
  els.shareBtn.disabled = false;
}

function renderStats() {
  const stats = state.stats || {};
  const cards = [
    ['Parties', stats.played ?? 0],
    ['Victoires', stats.won ?? 0],
    ['Win rate', `${stats.win_rate ?? 0}%`],
    ['Best score', stats.best_score ?? 0],
    ['Moy. essais win', stats.average_attempts_on_win ?? 0],
    ['Indices utilisés', stats.total_hints_used ?? 0],
  ];
  els.statGrid.innerHTML = '';
  cards.forEach(([label, value]) => {
    const div = document.createElement('div');
    div.className = 'stat-card';
    div.innerHTML = `<strong>${value}</strong><span>${label}</span>`;
    els.statGrid.appendChild(div);
  });
}

function renderHints() {
  const hints = state.game?.hints || [];
  const available = state.game?.available_hints || 0;
  els.hintCounter.textContent = `${hints.length} / ${available}`;
  els.hintList.innerHTML = '';
  if (!hints.length) {
    els.hintList.innerHTML = '<li>Aucun indice révélé pour le moment.</li>';
    return;
  }
  hints.forEach((hint) => {
    const li = document.createElement('li');
    li.innerHTML = `<strong>Niveau ${hint.level}</strong><span>${hint.content}</span>`;
    els.hintList.appendChild(li);
  });
}

function renderLeaderboard() {
  const board = state.leaderboard || { entries: [] };
  els.leaderboardMeta.textContent = board.date
    ? `Classement daily du ${board.date}`
    : `Classement ${board.mode || state.currentMode} all-time`;
  els.leaderboardList.innerHTML = '';
  if (!board.entries.length) {
    els.leaderboardList.innerHTML = '<p class="empty-state">Aucune entrée pour ce scope.</p>';
    return;
  }
  board.entries.forEach((entry) => {
    const item = document.createElement('div');
    item.className = 'leaderboard-entry';
    item.innerHTML = `
      <span class="position">${entry.position}</span>
      <div>
        <strong>${entry.display_name}</strong>
        <small>${entry.attempts_count} essais • ${entry.hints_used} indices • ${entry.duration_seconds}s</small>
      </div>
      <span class="mono">${entry.best_score}</span>
    `;
    els.leaderboardList.appendChild(item);
  });
}

function renderGuesses() {
  const guesses = state.game?.guesses || [];
  els.guessTable.innerHTML = '';
  if (!guesses.length) {
    els.guessTable.innerHTML = '<tr><td colspan="6" class="empty-row">Aucune tentative pour le moment.</td></tr>';
    return;
  }
  guesses.forEach((guess) => {
    const row = els.guessRowTemplate.content.firstElementChild.cloneNode(true);
    if (guess.exact) {
      row.classList.add('is-exact');
    }
    row.querySelector('.attempt').textContent = guess.attempt_number;
    row.querySelector('.word').textContent = guess.word;
    row.querySelector('.score').textContent = guess.score;
    row.querySelector('.rank').textContent = `#${guess.semantic_rank}`;
    row.querySelector('.percentile').textContent = `${guess.percentile}%`;
    row.querySelector('.temperature').textContent = guess.temperature;
    els.guessTable.appendChild(row);
  });
}

async function bootstrap(mode = state.currentMode) {
  try {
    const payload = await api(`/api/v1/bootstrap?mode=${encodeURIComponent(mode)}`);
    applyPayload(payload);
    setMessage('Application prête.', 'neutral');
  } catch (error) {
    setMessage(error.message, 'danger');
  }
}

async function switchMode(mode, newGame = false, customWord = null) {
  try {
    const payload = await api('/api/v1/game/select', {
      method: 'POST',
      body: JSON.stringify({
        mode,
        new_game: newGame,
        custom_word: customWord,
      }),
    });
    applyPayload(payload);
    setMessage(`Mode ${mode} chargé.`, 'success');
  } catch (error) {
    setMessage(error.message, 'danger');
  }
}

async function submitGuess() {
  const word = els.guessInput.value.trim();
  if (!word) {
    setMessage('Entre un mot à tester.', 'warning');
    return;
  }
  try {
    const payload = await api('/api/v1/game/guess', {
      method: 'POST',
      body: JSON.stringify({ word }),
    });
    applyPayload(payload);
    els.guessInput.value = '';
    els.guessInput.focus();
    setMessage(payload.message, payload.game.won ? 'success' : 'neutral');
  } catch (error) {
    setMessage(error.message, 'danger');
  }
}

async function requestHint() {
  try {
    const payload = await api('/api/v1/game/hint', {
      method: 'POST',
      body: JSON.stringify({}),
    });
    applyPayload(payload);
    setMessage(payload.hint.content, 'success');
  } catch (error) {
    setMessage(error.message, 'warning');
  }
}

async function saveProfile() {
  try {
    const payload = await api('/api/v1/profile', {
      method: 'PUT',
      body: JSON.stringify({ display_name: els.displayNameInput.value }),
    });
    applyPayload(payload);
    setMessage('Pseudo mis à jour.', 'success');
  } catch (error) {
    setMessage(error.message, 'danger');
  }
}

async function startCustomGame() {
  const secret = els.customSecretInput.value.trim();
  if (!secret) {
    setMessage('Entre un mot secret valide pour le mode custom.', 'warning');
    return;
  }
  await switchMode('custom', true, secret);
}

async function newGame() {
  if (state.currentMode === 'daily') {
    setMessage('Le mode daily conserve le mot du jour.', 'warning');
    return;
  }
  const customWord = state.currentMode === 'custom' ? els.customSecretInput.value.trim() : null;
  await switchMode(state.currentMode, true, customWord || null);
}

async function shareGame() {
  if (!state.game) {
    return;
  }
  try {
    await navigator.clipboard.writeText(state.game.share_line);
    setMessage('Texte de partage copié.', 'success');
  } catch (_error) {
    setMessage(state.game.share_line, 'neutral');
  }
}

els.modeSwitch.addEventListener('click', (event) => {
  const button = event.target.closest('[data-mode]');
  if (!button || button.disabled) {
    return;
  }
  const mode = button.dataset.mode;
  if (mode === 'custom') {
    els.customRow.style.display = 'grid';
    setMessage('Entre un mot secret puis clique sur Démarrer.', 'neutral');
    return;
  }
  switchMode(mode);
});

els.guessBtn.addEventListener('click', submitGuess);
els.guessInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    submitGuess();
  }
});
els.hintBtn.addEventListener('click', requestHint);
els.newGameBtn.addEventListener('click', newGame);
els.saveProfileBtn.addEventListener('click', saveProfile);
els.startCustomBtn.addEventListener('click', startCustomGame);
els.shareBtn.addEventListener('click', shareGame);

bootstrap(pageMode);
