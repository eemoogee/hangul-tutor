import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createSession, compose, VOWELS, VOWEL_SLOT, TASKS, TRANSFER, setMode,
  select, rotate, chooseRotatedVowel, place, undo, clearBlock, beginTasks, check, next,
  exportSession} from './model.mjs';

let passed = 0;
let tick = 1000;
function test(name, fn) { fn(); passed++; console.log(`PASS ${name}`); }
function put(s, type, glyph, slot) {
  if (s.mode === 'rotate' && type === 'vowel') {
    while (s.orientation !== glyph) rotate(s, 1, tick++);
    chooseRotatedVowel(s, tick++);
  } else assert.equal(select(s, type, glyph, 'test', tick++), true);
  assert.equal(place(s, slot, 'test', tick++).ok, true);
}
function complete(s, target) {
  put(s, 'initial', target.initial, 'initial');
  put(s, 'vowel', target.vowel, VOWEL_SLOT[target.vowel]);
  assert.equal(check(s, tick++).ok, true);
}

test('all eight supported CV blocks compose only with correct geometry', () => {
  const expected = {'ㄴㅏ': '나', 'ㄴㅓ': '너', 'ㄴㅗ': '노', 'ㄴㅜ': '누',
    'ㄷㅏ': '다', 'ㄷㅓ': '더', 'ㄷㅗ': '도', 'ㄷㅜ': '두'};
  for (const [pair, block] of Object.entries(expected)) {
    assert.equal(compose(pair[0], pair[1], VOWEL_SLOT[pair[1]]), block);
    assert.equal(compose(pair[0], pair[1], VOWEL_SLOT[pair[1]] === 'side' ? 'below' : 'side'), '');
  }
});
test('free exploration is unscored and wrong geometry can be corrected', () => {
  const s = createSession(0); put(s, 'initial', 'ㄴ', 'initial'); put(s, 'vowel', 'ㅗ', 'side');
  assert.equal(compose(s.initial, s.vowel, s.vowelSlot), '');
  assert.equal(s.runs.length, 0); assert.equal(s.events.some(e => e.action === 'place' && e.wrong_geometry), true);
  put(s, 'vowel', 'ㅗ', 'below'); assert.equal(compose(s.initial, s.vowel, s.vowelSlot), '노');
  assert.equal(s.runs.length, 0);
});
test('rotation follows four physical orientations and requires explicit placement', () => {
  const s = createSession(0); setMode(s, 'rotate', 1);
  for (const expected of ['ㅏ', 'ㅜ', 'ㅓ', 'ㅗ']) {
    rotate(s, 1, 2); assert.equal(s.orientation, expected); assert.equal(s.vowel, '');
  }
  chooseRotatedVowel(s, 3); place(s, 'below', 'tap', 4);
  assert.equal(s.vowel, 'ㅗ'); assert.equal(s.vowelSlot, 'below');
});
test('target mismatch and geometry errors count, corrections can undo', () => {
  const s = createSession(0); beginTasks(s, 1);
  put(s, 'initial', 'ㄷ', 'initial'); assert.equal(s.runs[0].placement_errors, 1);
  put(s, 'vowel', 'ㅗ', 'side'); assert.equal(s.runs[0].placement_errors, 2);
  assert.equal(check(s, 3).ok, false);
  assert.equal(undo(s, 4), true); assert.equal(s.runs[0].corrections, 1);
  put(s, 'initial', 'ㄴ', 'initial'); assert.equal(s.runs[0].corrections, 2);
  clearBlock(s, true, 5); assert.equal(s.runs[0].corrections, 3);
});
for (const mode of ['tap', 'drag', 'rotate']) {
  test(`${mode} uses the same four builds and untutored transfer`, () => {
    const s = createSession(0); setMode(s, mode, 1); beginTasks(s, 2);
    for (let i = 0; i < TASKS.length; i++) {
      assert.equal(s.phase, 'tasks'); assert.equal(s.taskIndex, i);
      complete(s, TASKS[i]); assert.equal(s.awaitingNext, true); next(s, tick++);
    }
    assert.equal(s.phase, 'transfer'); assert.equal(s.feedback.includes('Untutored transfer'), true);
    complete(s, TRANSFER); assert.equal(s.phase, 'done');
    assert.equal(s.runs[0].targets_completed, 4); assert.equal(s.runs[0].transfer_correct, true);
    assert.equal(s.runs[0].completed, true);
    assert.equal(s.runs[0].task_results.length, 4);
    assert.ok(s.runs[0].transfer_elapsed_ms >= 0);
    assert.equal(exportSession(s).runs[0].mode, mode);
    assert.equal(s.events.filter(e => e.action === 'submit').length, 5);
    if (mode === 'rotate') assert.ok(s.runs[0].rotations > 0);
  });
}
test('transfer captures the first answer and never tutors before submission', () => {
  const s = createSession(0); beginTasks(s, 1);
  for (const task of TASKS) { complete(s, task); next(s, tick++); }
  put(s, 'initial', 'ㄴ', 'initial'); put(s, 'vowel', 'ㅏ', 'side');
  assert.equal(s.feedback.includes('target'), false);
  assert.equal(check(s, tick++).done, true); assert.equal(s.runs[0].transfer_correct, false);
  assert.equal(s.runs[0].transfer_first_attempt, '나');
  assert.equal(check(s, tick++).ok, false);
});
test('prototype has no production storage or network writes', () => {
  const app = readFileSync(new URL('./app.mjs', import.meta.url), 'utf8');
  assert.doesNotMatch(app, /localStorage|sessionStorage|indexedDB|fetch\(|XMLHttpRequest|sendBeacon/);
});
console.log(`\n${passed} checks passed`);
