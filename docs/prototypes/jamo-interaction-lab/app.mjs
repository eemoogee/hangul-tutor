import {MODES, VOWELS, CONSONANTS, TASKS, createSession, currentTarget, compose, setMode,
  select, rotate, chooseRotatedVowel, place, undo, clearBlock, beginTasks, check, next,
  exportSession, record} from './model.mjs';

const s = createSession();
const $ = (id) => document.getElementById(id);
const els = {
  phase: $('phase-label'), title: $('activity-title'), progress: $('task-progress'), prompt: $('prompt'),
  map: $('sound-map'), initial: $('initial-slot'), side: $('side-slot'), below: $('below-slot'),
  formed: $('formed-block'), blockName: $('block-name'), geometry: $('geometry-note'),
  consonants: $('consonants'), vowels: $('vowels'), vowelInstruction: $('vowel-instruction'),
  dragAlternative: $('drag-alternative'), rotateNote: $('rotate-note'), feedback: $('feedback'),
  undo: $('undo-button'), clear: $('clear-button'), main: $('main-button'), note: $('observer-note'),
  download: $('download-log'), count: $('log-count'),
};

function pieceButton(glyph, type) {
  const b = document.createElement('button');
  b.type = 'button'; b.className = 'piece'; b.textContent = glyph;
  b.dataset.type = type; b.dataset.glyph = glyph;
  b.setAttribute('aria-label', `Select ${type === 'initial' ? 'consonant' : 'vowel'} ${glyph}`);
  b.setAttribute('aria-pressed', String(s.selection?.glyph === glyph && s.selection?.type === type));
  b.addEventListener('click', () => {
    if (suppressClick) { suppressClick = false; return; }
    select(s, type, glyph, s.mode === 'drag' ? 'tap_alternative' : 'tap'); render();
  });
  b.addEventListener('pointerdown', (event) => beginDrag(event, b, type, glyph));
  return b;
}

let suppressClick = false;
let drag = null;
function beginDrag(event, source, type, glyph) {
  if (s.mode !== 'drag' || event.button !== 0 || s.awaitingNext || s.phase === 'done') return;
  drag = {pointerId: event.pointerId, source, type, glyph, x: event.clientX, y: event.clientY, active: false, ghost: null};
  source.setPointerCapture(event.pointerId);
}
function hoveredSlot(x, y) { return document.elementFromPoint(x, y)?.closest('[data-slot]') || null; }
function clearHover() { document.querySelectorAll('.slot.is-target').forEach(el => el.classList.remove('is-target')); }
document.addEventListener('pointermove', (event) => {
  if (!drag || event.pointerId !== drag.pointerId) return;
  if (!drag.active && Math.hypot(event.clientX - drag.x, event.clientY - drag.y) > 7) {
    drag.active = true;
    drag.source.classList.add('is-dragging');
    drag.ghost = document.createElement('div'); drag.ghost.className = 'drag-ghost';
    drag.ghost.textContent = drag.glyph; document.body.appendChild(drag.ghost);
  }
  if (!drag.active) return;
  event.preventDefault();
  drag.ghost.style.left = `${event.clientX}px`; drag.ghost.style.top = `${event.clientY}px`;
  clearHover(); hoveredSlot(event.clientX, event.clientY)?.classList.add('is-target');
});
document.addEventListener('pointerup', (event) => {
  if (!drag || event.pointerId !== drag.pointerId) return;
  if (drag.active) {
    const slot = hoveredSlot(event.clientX, event.clientY)?.dataset.slot;
    select(s, drag.type, drag.glyph, 'drag');
    if (slot) {
      const result = place(s, slot, 'drag');
      if (!result.ok) s.feedback = result.reason;
    } else {
      record(s, 'drag_cancel', {glyph: drag.glyph});
      s.feedback = 'Release a piece over a block position to place it.';
    }
    suppressClick = true;
    setTimeout(() => { suppressClick = false; }, 0);
  }
  drag.source.classList.remove('is-dragging'); drag.ghost?.remove(); drag = null;
  clearHover(); render();
});
document.addEventListener('pointercancel', () => {
  if (!drag) return;
  drag.source.classList.remove('is-dragging'); drag.ghost?.remove(); drag = null; clearHover();
});

let inventoryMode = null;
function renderInventory() {
  // Keep button identity across ordinary renders so keyboard focus survives selection.
  if (!els.consonants.children.length) els.consonants.append(...CONSONANTS.map(g => pieceButton(g, 'initial')));
  if (inventoryMode !== s.mode) {
    els.vowels.replaceChildren();
    inventoryMode = s.mode;
    if (s.mode === 'rotate') {
    const left = document.createElement('button'); left.type = 'button'; left.className = 'rotate-control';
    left.textContent = '↶'; left.setAttribute('aria-label', 'Rotate vowel counterclockwise');
    left.addEventListener('click', () => { rotate(s, -1); render(); });
    const piece = document.createElement('button'); piece.type = 'button'; piece.className = 'piece rotated-piece';
    piece.textContent = s.orientation; piece.setAttribute('aria-label', `Select rotated vowel ${s.orientation}`);
    piece.setAttribute('aria-pressed', String(s.selection?.type === 'vowel'));
    piece.addEventListener('click', () => { chooseRotatedVowel(s); render(); });
    const right = document.createElement('button'); right.type = 'button'; right.className = 'rotate-control';
    right.textContent = '↷'; right.setAttribute('aria-label', 'Rotate vowel clockwise');
    right.addEventListener('click', () => { rotate(s, 1); render(); });
      els.vowels.append(left, piece, right);
    } else els.vowels.append(...VOWELS.map(g => pieceButton(g, 'vowel')));
  }
  els.consonants.querySelectorAll('.piece').forEach(b => b.setAttribute('aria-pressed',
    String(s.selection?.type === 'initial' && s.selection.glyph === b.dataset.glyph)));
  if (s.mode === 'rotate') {
    const piece = els.vowels.querySelector('.rotated-piece');
    piece.textContent = s.orientation;
    piece.setAttribute('aria-label', `Select rotated vowel ${s.orientation}`);
    piece.setAttribute('aria-pressed', String(s.selection?.type === 'vowel'));
  } else els.vowels.querySelectorAll('.piece').forEach(b => b.setAttribute('aria-pressed',
    String(s.selection?.type === 'vowel' && s.selection.glyph === b.dataset.glyph)));
}

function render() {
  document.querySelectorAll('.mode-button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mode === s.mode)));
  const target = currentTarget(s);
  if (s.phase === 'explore') {
    els.phase.textContent = 'FREE EXPLORATION'; els.title.textContent = 'What can these pieces make?';
    els.progress.textContent = 'No score'; els.prompt.textContent = 'Try a consonant and a vowel. No move is wrong here.';
  } else if (s.phase === 'tasks') {
    els.phase.textContent = 'TARGETED BUILDS'; els.title.textContent = `Build “${target.cue}”`;
    els.progress.textContent = `${s.taskIndex + 1} / ${TASKS.length}`;
    els.prompt.textContent = 'Use the letters and positions to make this sound.';
  } else if (s.phase === 'transfer') {
    els.phase.textContent = 'UNTUTORED TRANSFER'; els.title.textContent = `Build “${target.cue}”`;
    els.progress.textContent = 'One attempt';
    els.prompt.textContent = 'New starting consonant. Make the block on your own, then submit once.';
  } else {
    els.phase.textContent = 'CONDITION COMPLETE'; els.title.textContent = 'What did you notice?';
    els.progress.textContent = 'Recorded';
    els.prompt.textContent = 'Add an observation below, download the log, or try another interaction.';
  }
  els.map.hidden = s.phase === 'transfer' || s.phase === 'done';
  els.dragAlternative.hidden = s.mode !== 'drag'; els.rotateNote.hidden = s.mode !== 'rotate';
  els.vowelInstruction.textContent = 'ㅗ · ㅏ · ㅜ · ㅓ';
  for (const [slot, glyph] of [['initial', s.initial], ['side', s.vowelSlot === 'side' ? s.vowel : ''], ['below', s.vowelSlot === 'below' ? s.vowel : '']]) {
    const el = els[slot]; el.querySelector('.slot-glyph').textContent = glyph;
    el.dataset.filled = String(Boolean(glyph));
    el.setAttribute('aria-label', `${slot === 'initial' ? 'Starting consonant' : slot === 'side' ? 'Side vowel' : 'Lower vowel'} position${glyph ? `, ${glyph}` : ', empty'}. Place selected piece.`);
  }
  const block = compose(s.initial, s.vowel, s.vowelSlot);
  els.formed.textContent = block || '—';
  els.blockName.textContent = block ? `You made ${block}` : 'Your block';
  els.geometry.textContent = s.vowel && !block ? 'Try the other vowel position.' : 'Vowels stand beside or sit below.';
  if (s.phase === 'transfer') els.geometry.textContent = 'One block, two pieces.';
  els.feedback.textContent = s.feedback;
  els.undo.disabled = !s.history.length || s.awaitingNext || s.phase === 'done';
  els.clear.disabled = !(s.initial || s.vowel) || s.awaitingNext || s.phase === 'done';
  els.main.innerHTML = s.phase === 'explore' ? 'Start the four builds <span aria-hidden="true">↗</span>'
    : s.phase === 'tasks' && s.awaitingNext ? 'Next build <span aria-hidden="true">→</span>'
    : s.phase === 'tasks' ? 'Check block <span aria-hidden="true">→</span>'
    : s.phase === 'transfer' ? 'Submit transfer <span aria-hidden="true">→</span>'
    : 'Explore again <span aria-hidden="true">↗</span>';
  els.count.textContent = `${s.events.length} events · ${s.runs.length} run${s.runs.length === 1 ? '' : 's'}`;
  renderInventory();
}

document.querySelectorAll('.mode-button').forEach(button => button.addEventListener('click', () => {
  setMode(s, button.dataset.mode); render();
}));
document.querySelectorAll('[data-slot]').forEach(button => button.addEventListener('click', () => {
  const result = place(s, button.dataset.slot, s.mode === 'drag' ? 'tap_alternative' : 'tap');
  if (!result.ok) s.feedback = result.reason;
  render();
}));
els.undo.addEventListener('click', () => { undo(s); render(); });
els.clear.addEventListener('click', () => { clearBlock(s); s.feedback = 'Block cleared. Choose another piece.'; render(); });
els.main.addEventListener('click', () => {
  if (s.phase === 'explore') beginTasks(s);
  else if (s.phase === 'tasks' && s.awaitingNext) next(s);
  else if (s.phase === 'tasks' || s.phase === 'transfer') check(s);
  else { s.phase = 'explore'; clearBlock(s, false); s.feedback = 'Explore freely, or try another interaction.'; record(s, 'explore_again'); }
  render();
});
els.note.addEventListener('input', () => { s.note = els.note.value; });
els.download.addEventListener('click', () => {
  s.note = els.note.value;
  const blob = new Blob([JSON.stringify(exportSession(s), null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a'); anchor.href = url;
  anchor.download = `jamo-interaction-session-${new Date(s.startedAt).toISOString().replace(/[:.]/g, '-')}.json`;
  anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
render();
