// Run the prototype's own script against a small DOM to check its input states.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const page = fs.readFileSync(path.join(__dirname, '..', 'archive', 'Hangul Key Pad.html'), 'utf8');
const source = page.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(source, 'prototype script exists');
assert.match(page, /<meta charset=utf8>/i);

function boot() {
  const elements = new Map();
  const timers = [];
  class Element {
    constructor(id = '') {
      this.id = id;
      this.children = [];
      this.className = '';
      this.textContent = '';
      this.attributes = {};
      this.style = {};
      this.classList = {
        add: name => { this.className = [...new Set([...this.className.split(/\s+/).filter(Boolean), name])].join(' '); },
        remove: name => { this.className = this.className.split(/\s+/).filter(x => x && x !== name).join(' '); },
        contains: name => this.className.split(/\s+/).includes(name),
        toggle: (name, enabled) => enabled ? this.classList.add(name) : this.classList.remove(name)
      };
    }
    set innerHTML(value) { this._html = value; this.children = []; }
    get innerHTML() { return this._html || ''; }
    setAttribute(name, value) { this.attributes[name] = value; }
    appendChild(child) { child.parent = this; this.children.push(child); }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(x => x !== this); }
    addEventListener() {}
    querySelectorAll(selector) {
      if (selector === '.key') return this.children.filter(x => x.classList.contains('key'));
      if (selector === '.pieces span') return [{ style: {} }, { style: {} }];
      throw new Error(`Unexpected selector: ${selector}`);
    }
    get offsetWidth() { return 1; }
  }
  const document = {
    getElementById(id) { if (!elements.has(id)) elements.set(id, new Element(id)); return elements.get(id); },
    createElement() { return new Element(); },
    addEventListener() {}
  };
  const context = vm.createContext({
    document,
    matchMedia: () => ({ matches: false }),
    requestAnimationFrame: callback => callback(),
    setTimeout: callback => { timers.push(callback); }
  });
  vm.runInContext(source, context);
  const el = id => document.getElementById(id);
  const act = expression => vm.runInContext(expression, context);
  const flush = () => { while (timers.length) timers.shift()(); };
  const labels = () => el('answer').children.map(x => x.attributes['aria-label']);
  return { el, act, flush, labels };
}

function keys(app, sequence) {
  for (const key of sequence) { app.act(`press(${JSON.stringify(key)})`); app.flush(); }
}

{
  const app = boot();
  keys(app, ['ㄴ']);
  assert.deepEqual(app.labels(), ['ㄴ, waiting for a vowel']);
  assert.match(app.el('answer').children[0].innerHTML, /class="slot"/);
}
{
  const app = boot();
  keys(app, ['ㄴ', 'ㅏ']);
  assert.deepEqual(app.labels(), ['나']);
  assert.match(app.el('answer').children[0].innerHTML, />나</);
}
{
  const app = boot();
  keys(app, ['ㄴ', 'ㅏ', 'ㄷ', 'ㅗ']);
  assert.deepEqual(app.labels(), ['나', '도']);
}
{
  const app = boot();
  keys(app, ['ㄴ', 'ㄷ']);
  assert.deepEqual(app.labels(), ['ㄴ, waiting for a vowel', 'ㄷ, waiting for a vowel']);
  assert.ok(app.el('answer').children[0].classList.contains('warn'));
}
{
  const app = boot();
  keys(app, ['ㅏ']);
  assert.deepEqual(app.labels(), ['ㅏ without a consonant']);
  assert.ok(app.el('answer').children[0].classList.contains('lone'));
  assert.match(app.el('note').innerHTML, /can't start with a vowel/);
}
{
  const app = boot();
  keys(app, ['ㄴ', 'ㅗ']);
  app.act('press("ㅏ")');
  assert.deepEqual(app.labels(), ['노']);
  assert.ok(app.el('answer').children[0].classList.contains('shake'));
  assert.match(app.el('note').innerHTML, /already has a vowel/);
  assert.equal(app.el('taps').textContent, 'Taps: ㄴ ㅗ ㅏ');
}
{
  const app = boot();
  keys(app, ['ㄴ', 'ㅏ', 'ㄷ', 'ㅗ']);
  const expected = [
    ['나', 'ㄷ, waiting for a vowel'],
    ['나'],
    ['ㄴ, waiting for a vowel'],
    []
  ];
  for (const state of expected) {
    app.act('backspace()'); app.flush();
    assert.deepEqual(app.labels(), state);
  }
}
{
  const app = boot();
  app.act('ti = 1; setTarget()');
  assert.equal(app.el('tGloss').textContent, 'do · as in do-re-mi');
  app.act('level = 1; ti = 0; buildKeys(); setTarget()');
  assert.equal(app.el('consKeys').querySelectorAll('.key').length, 4);
  assert.equal(app.el('vowKeys').querySelectorAll('.key').length, 4);
  keys(app, ['ㅁ', 'ㅜ']);
  assert.deepEqual(app.labels(), ['무']);
}
{
  const app = boot();
  keys(app, ['ㄴ']);
  app.act('check()');
  assert.match(app.el('note').innerHTML, /needs a vowel/);
  keys(app, ['ㅏ']);
  app.act('check()');
  assert.equal(app.el('note').className, 'note jeong');
  app.flush();
  assert.equal(app.el('tWord').textContent, '도');
  assert.deepEqual(app.labels(), []);
}

console.log('PASS: all seven table sequences, Check behavior, 도 caption, and Batch 1 key expansion');
