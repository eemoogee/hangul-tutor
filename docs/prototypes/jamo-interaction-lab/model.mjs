// Shared experimental model. No curriculum or production state is read or written.
export const MODES = Object.freeze(['tap', 'drag', 'rotate']);
export const VOWELS = Object.freeze(['ㅗ', 'ㅏ', 'ㅜ', 'ㅓ']);
export const CONSONANTS = Object.freeze(['ㄴ', 'ㄷ']);
export const VOWEL_SLOT = Object.freeze({'ㅏ': 'side', 'ㅓ': 'side', 'ㅗ': 'below', 'ㅜ': 'below'});
export const TASKS = Object.freeze([
  {id: 'na', cue: 'na', initial: 'ㄴ', vowel: 'ㅏ'},
  {id: 'no', cue: 'no', initial: 'ㄴ', vowel: 'ㅗ'},
  {id: 'neo', cue: 'neo', initial: 'ㄴ', vowel: 'ㅓ'},
  {id: 'nu', cue: 'nu', initial: 'ㄴ', vowel: 'ㅜ'},
]);
export const TRANSFER = Object.freeze({id: 'do-transfer', cue: 'do', initial: 'ㄷ', vowel: 'ㅗ'});
const INITIAL_INDEX = {'ㄴ': 2, 'ㄷ': 3};
const VOWEL_INDEX = {'ㅏ': 0, 'ㅓ': 4, 'ㅗ': 8, 'ㅜ': 13};

export function compose(initial, vowel, vowelSlot) {
  if (!(initial in INITIAL_INDEX) || !(vowel in VOWEL_INDEX) || VOWEL_SLOT[vowel] !== vowelSlot) return '';
  return String.fromCodePoint(0xac00 + (INITIAL_INDEX[initial] * 21 + VOWEL_INDEX[vowel]) * 28);
}

export function createSession(now = Date.now()) {
  return {
    startedAt: now, mode: 'tap', phase: 'explore', taskIndex: 0, awaitingNext: false,
    initial: '', vowel: '', vowelSlot: '', selection: null, orientation: 'ㅗ',
    history: [], runs: [], events: [], note: '', feedback: 'Choose a piece, then place it in the block.',
  };
}

export function currentTarget(s) {
  return s.phase === 'tasks' ? TASKS[s.taskIndex] : s.phase === 'transfer' ? TRANSFER : null;
}

export function record(s, action, detail = {}, now = Date.now()) {
  s.events.push({at_ms: now - s.startedAt, mode: s.mode, phase: s.phase,
    task: currentTarget(s)?.id ?? null, action, ...detail});
}

export function setMode(s, mode, now = Date.now()) {
  if (!MODES.includes(mode)) throw new Error(`Unknown mode: ${mode}`);
  if (s.mode === mode) return;
  record(s, 'mode_leave', {to: mode}, now);
  s.mode = mode;
  s.phase = 'explore'; s.taskIndex = 0; s.awaitingNext = false;
  clearBlock(s, false);
  s.orientation = 'ㅗ';
  s.feedback = 'Explore freely, or begin the same four builds in this mode.';
  record(s, 'mode_enter', {}, now);
}

export function clearBlock(s, countCorrection = true, now = Date.now()) {
  if (countCorrection && (s.initial || s.vowel) && s.phase !== 'explore') {
    activeRun(s).corrections++;
    record(s, 'correction', {kind: 'clear'}, now);
  }
  s.initial = ''; s.vowel = ''; s.vowelSlot = ''; s.selection = null; s.history = [];
}

export function beginTasks(s, now = Date.now()) {
  s.phase = 'tasks'; s.taskIndex = 0; s.awaitingNext = false;
  clearBlock(s, false);
  s.orientation = 'ㅗ';
  s.feedback = 'Build the sound shown above. Place both pieces, then check.';
  s.runs.push({mode: s.mode, started_at_ms: now - s.startedAt, completed: false,
    task_started_at_ms: now - s.startedAt, task_results: [], targets_completed: 0,
    placement_errors: 0, rotations: 0, corrections: 0,
    transfer_started_at_ms: null, transfer_correct: null, transfer_first_attempt: null,
    transfer_elapsed_ms: null});
  record(s, 'tasks_start', {}, now);
}

export function activeRun(s) { return s.runs.at(-1); }

export function select(s, type, glyph, method = 'tap', now = Date.now()) {
  if (s.awaitingNext || s.phase === 'done') return false;
  if (type === 'initial' && !CONSONANTS.includes(glyph)) return false;
  if (type === 'vowel' && (!VOWELS.includes(glyph) || s.mode === 'rotate')) return false;
  s.selection = {type, glyph, method};
  s.feedback = `${glyph} selected. Place it in the block.`;
  record(s, 'select', {type, glyph, method}, now);
  return true;
}

export function rotate(s, direction, now = Date.now()) {
  if (s.mode !== 'rotate' || s.awaitingNext || s.phase === 'done') return false;
  const i = VOWELS.indexOf(s.orientation);
  s.orientation = VOWELS[(i + (direction > 0 ? 1 : 3)) % 4];
  s.selection = {type: 'vowel', glyph: s.orientation, method: 'rotate'};
  if (s.phase !== 'explore') activeRun(s).rotations++;
  record(s, 'rotate', {direction: direction > 0 ? 'clockwise' : 'counterclockwise', to: s.orientation}, now);
  s.feedback = `${s.orientation} is ready. Choose a vowel position explicitly.`;
  return true;
}

export function chooseRotatedVowel(s, now = Date.now()) {
  if (s.mode !== 'rotate' || s.awaitingNext || s.phase === 'done') return false;
  s.selection = {type: 'vowel', glyph: s.orientation, method: 'rotate'};
  s.feedback = `${s.orientation} is ready. Choose a vowel position explicitly.`;
  record(s, 'select', {type: 'vowel', glyph: s.orientation, method: 'rotate'}, now);
  return true;
}

export function place(s, slot, method = 'tap', now = Date.now()) {
  if (s.awaitingNext || s.phase === 'done') return {ok: false, reason: 'Wait for the next build.'};
  const piece = s.selection;
  if (!piece) return {ok: false, reason: 'Choose a piece first.'};
  if (!['initial', 'side', 'below'].includes(slot)) return {ok: false, reason: 'Choose a block position.'};
  if ((slot === 'initial') !== (piece.type === 'initial')) {
    if (s.phase === 'tasks') activeRun(s).placement_errors++;
    record(s, 'placement_error', {kind: 'piece_type', glyph: piece.glyph, slot, method}, now);
    return {ok: false, reason: s.phase === 'transfer' ? 'That piece does not fit this position.'
      : piece.type === 'initial' ? 'Consonants start the block.' : 'Vowels go beside or below the consonant.'};
  }
  const previous = {initial: s.initial, vowel: s.vowel, vowelSlot: s.vowelSlot};
  s.history.push(previous);
  if (piece.type === 'initial') s.initial = piece.glyph;
  else { s.vowel = piece.glyph; s.vowelSlot = slot; }
  s.selection = null;
  const changed = piece.type === 'initial'
    ? Boolean(previous.initial && previous.initial !== s.initial)
    : Boolean(previous.vowel && (previous.vowel !== s.vowel || previous.vowelSlot !== s.vowelSlot));
  if (changed && s.phase !== 'explore') { activeRun(s).corrections++; record(s, 'correction', {kind: 'replace'}, now); }
  const target = currentTarget(s);
  const wrongGeometry = piece.type === 'vowel' && VOWEL_SLOT[piece.glyph] !== slot;
  const wrongForTarget = target && (piece.type === 'initial' ? piece.glyph !== target.initial : piece.glyph !== target.vowel);
  if (s.phase === 'tasks' && (wrongGeometry || wrongForTarget)) activeRun(s).placement_errors++;
  record(s, 'place', {glyph: piece.glyph, slot, method, wrong_geometry: wrongGeometry,
    target_mismatch: s.phase === 'tasks' ? Boolean(wrongForTarget) : null}, now);
  const block = compose(s.initial, s.vowel, s.vowelSlot);
  s.feedback = s.phase === 'transfer' ? 'Placement recorded. Submit when ready.'
    : wrongGeometry ? `${piece.glyph} needs the ${VOWEL_SLOT[piece.glyph] === 'side' ? 'side' : 'lower'} vowel position to form a standard block.`
    : block ? `You made ${block}.` : 'Keep building. Both pieces make one block.';
  return {ok: true, block, wrongGeometry};
}

export function undo(s, now = Date.now()) {
  if (s.awaitingNext || s.phase === 'done' || !s.history.length) return false;
  const previous = s.history.pop();
  s.initial = previous.initial; s.vowel = previous.vowel; s.vowelSlot = previous.vowelSlot;
  s.selection = null;
  if (s.phase !== 'explore') activeRun(s).corrections++;
  record(s, 'correction', {kind: 'undo'}, now);
  s.feedback = 'Last placement undone.';
  return true;
}

export function check(s, now = Date.now()) {
  const target = currentTarget(s);
  if (!target || s.awaitingNext) return {ok: false, reason: 'No build to check.'};
  const actual = compose(s.initial, s.vowel, s.vowelSlot);
  const correct = s.initial === target.initial && s.vowel === target.vowel && s.vowelSlot === VOWEL_SLOT[target.vowel];
  record(s, 'submit', {correct, block: actual || null}, now);
  if (s.phase === 'transfer') {
    const run = activeRun(s);
    run.transfer_first_attempt = actual || null;
    run.transfer_correct = correct;
    run.transfer_elapsed_ms = now - (s.startedAt + run.transfer_started_at_ms);
    run.completed = true;
    s.phase = 'done';
    s.feedback = correct ? `Transfer complete: ${actual}. What helped you decide?`
      : `Transfer recorded. The target was ${compose(target.initial, target.vowel, VOWEL_SLOT[target.vowel])}. What did you try?`;
    record(s, 'condition_complete', {transfer_correct: correct}, now);
    return {ok: correct, done: true};
  }
  if (!correct) {
    const reason = s.initial !== target.initial ? `The first piece is ${s.initial || 'missing'}; try the consonant for “${target.cue}”.`
      : s.vowel !== target.vowel ? `The vowel ${s.vowel || 'is missing'} changes the sound. Try the one for “${target.cue}”.`
      : `${s.vowel} belongs ${VOWEL_SLOT[s.vowel] === 'side' ? 'beside' : 'below'} the consonant.`;
    s.feedback = reason;
    return {ok: false, reason};
  }
  const run = activeRun(s);
  run.targets_completed++;
  run.task_results.push({task: target.id, completed_at_ms: now - s.startedAt,
    elapsed_ms: now - (s.startedAt + run.task_started_at_ms),
    submissions: s.events.filter(e => e.action === 'submit' && e.task === target.id &&
      e.mode === s.mode && e.at_ms >= run.started_at_ms).length});
  s.awaitingNext = true;
  s.feedback = `${actual} matches “${target.cue}”. Continue when ready.`;
  return {ok: true, done: false};
}

export function next(s, now = Date.now()) {
  if (!s.awaitingNext) return false;
  s.awaitingNext = false;
  if (s.taskIndex < TASKS.length - 1) s.taskIndex++;
  else s.phase = 'transfer';
  if (s.phase === 'transfer') activeRun(s).transfer_started_at_ms = now - s.startedAt;
  else activeRun(s).task_started_at_ms = now - s.startedAt;
  clearBlock(s, false);
  s.orientation = 'ㅗ';
  s.feedback = s.phase === 'transfer'
    ? 'Untutored transfer: make one new block. There are no hints or corrections before submission.'
    : 'Make the next sound with the same letters.';
  record(s, s.phase === 'transfer' ? 'transfer_start' : 'task_start', {}, now);
  return true;
}

export function exportSession(s) {
  return {
    schema: 1, experiment: 'jamo-interaction-lab', started_at: new Date(s.startedAt).toISOString(),
    note: s.note, runs: s.runs, events: s.events,
    interpretation_note: 'Prototype interaction log only; no mastery or educational superiority inference.',
  };
}
