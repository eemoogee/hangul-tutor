"use strict";

// Python owns the lesson. This file keeps only presentation, time, and local playtest data.
const PARAMS = new URLSearchParams(location.search);
const COURSE = PARAMS.get("course") === "curriculum" ? "curriculum" : "sejong";
const STORAGE_KEY = COURSE === "curriculum" ? "hangul.curriculum.v1" : "sejong.slice.v1";
const CURRICULUM_SAVE_KIND = "curriculum-controller";
const CURRICULUM_SAVE_VERSION = 1;
const TEST = PARAMS.get("test") === "1";
const TEST_SEED = TEST ? Number(PARAMS.get("seed") || 1) : null;
const $ = id => document.getElementById(id);
const screen = $("screen"), controls = $("controls"), status = $("status");
const dialogLayer = $("dialog-layer");
if (COURSE === "curriculum") {
  document.title = "Hangul Tutor · Lessons";
  document.querySelector(".brand").textContent = "HANGUL TUTOR";
  $("batch-name").textContent = "Your lessons";
}
let pyodide, appVersion, flowReady = false, pending = [], openCard = null;
let awaitInput = null, visibleEvent = null, hinted = false, cardShownAt = 0;
let startedAt = null, finishedAt = null, answerLog = [], eventHistory = [];
let submissionMs = [];
let activeBucket = 0, lastTick = performance.now(), paused = false, busy = false;
let loadingTimes = {}, storageWorked = true;
let teachingData = {mnemonics: {}, quirks: {}}, teaching = null;
let saveBlocked = false;

const node = (tag, className, value) => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (value !== undefined) element.textContent = value;
  return element;
};
const add = (parent, tag, className, value) => parent.appendChild(node(tag, className, value));
const button = (label, className, action) => {
  const element = node("button", className, label);
  element.type = "button";
  element.addEventListener("click", action);
  return element;
};
function clear(kind) {
  screen.replaceChildren();
  screen.dataset.kind = kind;
  document.querySelector(".shell").classList.toggle("lesson-one-active", kind === "lesson1_teaching");
  controls.replaceChildren();
  status.textContent = "";
}
function line(parent, event) {
  const row = add(parent, "div", "character-line");
  character(row, event.speaker);
  const words = add(row, "div", "character-words");
  const tag = add(words, "span", "name-tag", event.speaker === "sejong" ? "King Sejong" : "Jeong");
  if (String(event.source || "").startsWith("real")) add(tag, "span", "historical", "historical");
  add(words, "p", "line-text", event.text);
}
const CHARACTER_ASSETS = {
  jeong: {
    hello: "./assets/jeong_hello.png",
    curious: "./assets/jeong_curious.png",
    delighted: "./assets/jeong_delighted.png",
  },
  sejong: {
    hello: "./assets/sejong_hello.png",
    curious: "./assets/sejong_curious.png",
    delighted: "./assets/sejong_delighted.png",
  },
};
function character(parent, speaker, pose = "hello") {
  const mascot = speaker === "sejong" ? "sejong" : "jeong";
  const selectedPose = CHARACTER_ASSETS[mascot][pose] ? pose : "hello";
  const image = add(parent, "img", "character-portrait");
  image.src = CHARACTER_ASSETS[mascot][selectedPose];
  image.dataset.pose = selectedPose;
  image.alt = `${mascot === "sejong" ? "King Sejong" : "Jeong"} mascot, ${selectedPose} pose`;
  image.width = 72; image.height = 72;
  return image;
}
function continueButton(label = "Continue") {
  controls.appendChild(button(label, "primary", async () => {
    if (await resumeIfPaused()) return;
    await showNext();
  }));
}
function stage(event) {
  $("batch-name").textContent = event.batch_name;
  const chips = $("letters");
  chips.replaceChildren();
  for (const letter of event.letters_known) add(chips, "span", "letter-chip", letter);
}
function takeAwait() {
  if (pending[0]?.kind === "await") return pending.shift();
  return null;
}
function setCard(event, isNew = true) {
  openCard = event;
  if (isNew) { hinted = false; cardShownAt = performance.now(); }
  awaitInput = takeAwait();
  renderCard(event);
}
function renderCard(event, overlay = null) {
  clear(event.kind);
  if (event.kind === "predict") {
    add(screen, "span", "eyebrow", "Put them together");
    add(screen, "div", "big-hangul word", `${event.consonant} + ${event.vowel} = ?`);
  } else {
    add(screen, "p", "prompt", event.prompt);
    if (event.parts) add(screen, "div", "big-hangul word", event.parts.join(" + "));
    else if (event.display) add(screen, "div", "big-hangul" + (event.display.length > 1 ? " word" : ""), event.display);
    if (event.round) {
      const bar = add(screen, "div", "round");
      const track = add(bar, "span", "round-track");
      const fill = add(track, "span", "round-fill");
      fill.style.width = `${Math.min(100, 100 * event.round.index / event.round.size)}%`;
      add(bar, "span", "round-label", `${event.round.index} of ${event.round.size}`);
    }
  }
  if (overlay) add(screen, "p", overlay.kind === "hint" ? "hint-text" : "notice", overlay.text);
  const input = awaitInput;
  if (!input) return;
  if (input.input === "choice") {
    const choices = add(controls, "div", "choices");
    for (const choice of input.choices) choices.appendChild(button(choice, "choice", () => submitAnswer(choice)));
  } else if (input.input === "text") {
    const form = add(controls, "form", "text-form");
    const field = add(form, "input");
    field.type = "text";
    field.placeholder = input.placeholder || "";
    field.autocapitalize = "none";
    field.autocomplete = "off";
    field.setAttribute("autocorrect", "off");
    field.spellcheck = false;
    field.setAttribute("enterkeyhint", "go");
    const go = add(form, "button", "primary", "Go");
    go.type = "submit";
    form.addEventListener("submit", event => { event.preventDefault(); submitAnswer(field.value); });
  }
  if (event.hint_available) controls.appendChild(button("Need a hint?", "hint-button", async () => {
    if (await resumeIfPaused()) return;
    hinted = true;
    await callFlow("submit", "/hint", 0);
  }));
}
function renderEvent(event) {
  clear(event.kind);
  if (event.kind === "narrator") line(screen, event);
  else if (event.kind === "before_word") add(screen, "div", "big-hangul word", event.ko);
  else if (event.kind === "letter_intro") {
    add(screen, "span", "eyebrow", "A new letter");
    const pair = add(screen, "div", "letter-pair");
    if (event.related) add(pair, "span", "related-letter", event.related);
    add(pair, "span", "big-hangul", event.jamo);
    add(screen, "p", "fact", `${event.roman} · ${event.sound}`);
    add(screen, "p", "support", event.shape);
    if (event.notice_line) line(screen, event.notice_line);
  } else if (event.kind === "reveal") {
    add(screen, "span", "eyebrow", "The letters become a block");
    const view = add(screen, "div", `assembly ${event.layout}`);
    add(view, "span", "part c", event.parts[0]);
    add(view, "span", "part v", event.parts[1]);
    add(view, "span", "whole", event.block);
    add(view, "span", "part-labels", `${event.parts[0]} + ${event.parts[1]}`);
    add(screen, "p", "fact", `${event.roman}${event.meaning ? ` · ${event.meaning}` : ""}`);
  } else if (event.kind === "result") {
    const context = openCard?.context;
    add(screen, "span", `eyebrow ${event.correct ? "correct" : "incorrect"}`, event.correct ? "Correct" : "Not yet");
    if (!event.correct) {
      const label = context === "check" || context === "after" ? "It reads" : "The answer is";
      add(screen, "p", "fact", `${label} ${event.correct_answer}.`);
    } else add(screen, "p", "fact correct", event.correct_answer);
    if (event.chosen_is) add(screen, "p", "support", `You chose ${event.chosen_is}.`);
    if (event.tell && !event.line?.text?.includes(event.tell)) add(screen, "p", "support", event.tell);
    if (event.line) line(screen, event.line);
  } else if (event.kind === "word_read") {
    add(screen, "div", "big-hangul word", event.ko);
    add(screen, "p", "fact", `${event.roman} · ${event.en}`);
    if (event.line) line(screen, event.line);
  } else if (event.kind === "score") {
    add(screen, "span", `eyebrow ${event.passed ? "correct" : "incorrect"}`, event.passed ? "Reading check passed" : "Keep practicing");
    add(screen, "p", "score-number", `${event.correct} of ${event.size}`);
    add(screen, "p", "support", "Reading check");
  } else if (event.kind === "milestone") {
    add(screen, "div", `seal ${event.seal}`, event.seal === "full" ? "승리" : "첫걸음");
    add(screen, "p", "fact", event.time_text);
    const lines = add(screen, "div", "milestone-lines");
    for (const item of event.lines) line(lines, item);
  } else if (event.kind === "finished") {
    finishedAt ||= new Date().toISOString();
    saveState();
    add(screen, "span", "eyebrow", event.outcome.replaceAll("_", " "));
    add(screen, "div", "seal", "승리");
    controls.appendChild(button("Copy results", "primary", showResults));
    controls.appendChild(button("Start over", "secondary", confirmReset));
    return;
  }
  continueButton();
}

function plainPrompt(value) { return String(value || "").replaceAll("**", ""); }
const CONSONANTS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ";
const VOWELS = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ";
const BATCHIM_EXAMPLES = {"ㄱ":"각", "ㄴ":"간", "ㄷ":"갇", "ㄹ":"갈", "ㅁ":"감", "ㅂ":"갑", "ㅇ":"강"};
function letterExample(letter) {
  const vowel = VOWELS.indexOf(letter);
  if (vowel >= 0) return `ㅇ + ${letter} = ${String.fromCodePoint(0xac00 + (11 * 21 + vowel) * 28)}`;
  const consonant = CONSONANTS.indexOf(letter);
  return consonant >= 0 ? `${letter} + ㅏ = ${String.fromCodePoint(0xac00 + consonant * 21 * 28)}` : "";
}
function teachingCards(lesson) {
  const cards = [{kind: "overview"}];
  if (lesson.id === 1) cards.push({kind: "discovery"});
  for (const letter of lesson.letters || []) cards.push({kind: "letter", letter});
  if ((lesson.letters || []).length || (lesson.words || []).length ||
      (lesson.vocabulary || []).length || Object.keys(lesson.block_rules || {}).length)
    cards.push({kind: "reference"});
  return cards;
}
function curriculumHeader(lesson) {
  $("batch-name").textContent = `Lesson ${lesson.id}: ${lesson.title}`;
  const chips = $("letters"); chips.replaceChildren();
  for (const letter of lesson.letters || []) add(chips, "span", "letter-chip", letter);
}
function startTeaching(lesson, index = 0, message = "") {
  if (openCard) pending.unshift(openCard);
  openCard = null; awaitInput = null;
  if (lesson.id === 1) {
    const savedState = typeof index === "string" ? index : null;
    teaching = {lesson, kind: "lesson1", message};
    pyodide.globals.set("lesson_one_mnemonics", JSON.stringify(teachingData.mnemonics || {}));
    if (savedState) {
      pyodide.globals.set("lesson_one_saved", savedState);
      python("teaching_flow = LessonOneTeaching.from_state(quiz.current_lesson, json.loads(lesson_one_mnemonics), lesson_one_saved)");
    } else python("teaching_flow = LessonOneTeaching(quiz.current_lesson, json.loads(lesson_one_mnemonics))");
    renderLessonOne();
    return;
  }
  teaching = {lesson, cards: teachingCards(lesson), index, message};
  renderTeaching();
}
function finishTeaching() {
  teaching = null;
  if (COURSE === "curriculum") python("teaching_flow = None");
  saveState();
  showCurriculumNext();
}
function nextTeaching() {
  if (!teaching) return;
  if (teaching.kind === "lesson1") return;
  if (++teaching.index >= teaching.cards.length) finishTeaching();
  else renderTeaching();
}
function lessonOneAction(action) {
  if (!teaching || teaching.kind !== "lesson1") return;
  pyodide.globals.set("lesson_one_action", action);
  const event = JSON.parse(python("json.dumps(teaching_flow.submit(lesson_one_action), ensure_ascii=False)"));
  if (event.kind === "teaching_done") finishTeaching();
  else { renderLessonOne(event); saveState(); }
}
function renderLessonOne(event = null) {
  if (!teaching || teaching.kind !== "lesson1") return;
  event ||= JSON.parse(python("json.dumps(teaching_flow.current(), ensure_ascii=False)"));
  if (event.kind === "teaching_done") { finishTeaching(); return; }
  clear("lesson1_teaching");
  visibleEvent = event;
  curriculumHeader(teaching.lesson);
  const stage = add(screen, "div", "character-stage");
  character(stage, event.speaker, event.pose);
  const dialogue = add(screen, "div", "dialogue-panel");
  add(dialogue, "span", "name-tag", "Jeong · your guide");
  add(dialogue, "p", "dialogue-text", event.dialogue);
  const exercise = add(screen, "div", "teaching-exercise");
  if (event.kind === "teaching_intro") {
    add(exercise, "span", "eyebrow", "Lesson 1 · Your first vowels");
    controls.appendChild(button("Look at two blocks", "primary", () => lessonOneAction("/continue")));
    controls.appendChild(button("Go straight to practice", "secondary", () => lessonOneAction("/skip")));
  } else if (event.kind === "teaching_predict") {
    add(exercise, "span", "eyebrow", "Notice a pattern");
    add(exercise, "div", "teaching-blocks", event.blocks.join("   "));
    add(exercise, "p", "prompt", event.prompt);
    const choices = add(controls, "div", "choices");
    for (const choice of event.choices)
      choices.appendChild(button(choice.label, "choice", () => lessonOneAction(choice.value)));
    controls.appendChild(button("Go straight to practice", "secondary", () => lessonOneAction("/skip")));
  } else if (event.kind === "teaching_feedback") {
    add(exercise, "span", "eyebrow", event.correct ? "You found it" : "Look again");
    add(exercise, "div", "teaching-blocks", event.blocks.join("   "));
    add(exercise, "p", "support", event.explanation);
    controls.appendChild(button("Meet the six vowels", "primary", () => lessonOneAction("/continue")));
    controls.appendChild(button("Go straight to practice", "secondary", () => lessonOneAction("/skip")));
  } else if (event.kind === "teaching_explore") {
    add(exercise, "span", "eyebrow", "Your first vowels");
    const grid = add(exercise, "div", "vowel-grid");
    for (const item of event.letters) {
      const tile = button("",
        "vowel-tile" + (item.jamo === event.selected ? " selected" : ""),
        () => lessonOneAction(item.jamo));
      add(tile, "strong", "vowel-glyph", item.jamo);
      add(tile, "span", "vowel-roman", item.roman);
      add(tile, "span", "vowel-block", item.syllable);
      tile.setAttribute("aria-label", `${item.jamo}, ${item.roman}, ${item.syllable}`);
      tile.setAttribute("aria-pressed", item.jamo === event.selected ? "true" : "false");
      grid.appendChild(tile);
    }
    const selected = event.letters.find(item => item.jamo === event.selected);
    if (selected) {
      const detail = add(exercise, "div", "vowel-detail");
      add(detail, "strong", "", `${selected.jamo} → ${selected.syllable} · ${selected.roman}`);
      add(detail, "p", "", selected.sound);
      if (selected.memory) add(detail, "p", "", selected.memory);
    }
    controls.appendChild(button("Start practice", "primary", () => lessonOneAction("/practice")));
  }
  saveState();
}
function renderTeaching() {
  if (!teaching) return;
  const {lesson, cards, index} = teaching;
  const card = cards[index];
  clear(index === 0 ? "lesson_started" : "lesson_teaching");
  visibleEvent = {kind: "lesson_started", lesson};
  curriculumHeader(lesson);
  const guide = add(screen, "div", "teaching-head");
  character(guide, "jeong");
  add(guide, "span", "name-tag", "Jeong · your guide");
  if (card.kind === "overview") {
    add(screen, "span", "eyebrow", `Lesson ${lesson.id} of 12`);
    add(screen, "h1", "line-text", lesson.title);
    if (teaching.message) add(screen, "p", "support", teaching.message);
    if (lesson.description) add(screen, "p", "support", plainPrompt(lesson.description));
    if (lesson.introduction) add(screen, "p", "curriculum-prompt", plainPrompt(lesson.introduction));
    if (lesson.note && lesson.id !== 1) add(screen, "p", "support", plainPrompt(lesson.note));
  } else if (card.kind === "discovery") {
    add(screen, "span", "eyebrow", "Notice the pattern");
    add(screen, "div", "teaching-equation", "ㅇ + ㅏ = 아");
    add(screen, "div", "teaching-equation", "ㅇ + ㅓ = 어");
    add(screen, "div", "teaching-equation", "ㅇ + ㅗ = 오");
    add(screen, "p", "support", "Each block begins with the same silent ㅇ. The vowel supplies its sound.");
    if (lesson.note) add(screen, "p", "support", plainPrompt(lesson.note));
  } else if (card.kind === "letter") {
    const letter = card.letter;
    const finalSound = lesson.batchim_pronunciation?.[letter];
    add(screen, "span", "eyebrow", `${finalSound ? "Bottom sound" : "Letter"} ${index - (lesson.id === 1 ? 1 : 0)} of ${lesson.letters.length}`);
    add(screen, "div", "teaching-letter", letter);
    const roman = lesson.letter_romanization?.[letter];
    if (finalSound) {
      add(screen, "p", "fact", `At the bottom: ${finalSound}`);
      if (BATCHIM_EXAMPLES[letter]) add(screen, "p", "teaching-equation", `${letter} at the bottom → ${BATCHIM_EXAMPLES[letter]}`);
    } else {
      if (roman) add(screen, "p", "fact", `Written in English letters: ${roman}`);
      if (lesson.pronunciation?.[letter]) add(screen, "p", "support", `Sounds like ${lesson.pronunciation[letter]}`);
      const example = letterExample(letter);
      if (example) add(screen, "p", "teaching-equation", example);
      if (lesson.formation?.[letter]) add(screen, "p", "support", `Built from ${lesson.formation[letter]}`);
      if (teachingData.mnemonics?.[letter]) add(screen, "p", "teaching-memory", teachingData.mnemonics[letter]);
      if (teachingData.quirks?.[letter]) add(screen, "p", "notice", teachingData.quirks[letter]);
    }
  } else if (card.kind === "reference") {
    add(screen, "span", "eyebrow", "Keep this handy");
    add(screen, "h2", "teaching-title", "Lesson reference");
    if (lesson.letters?.length) {
      const list = add(screen, "div", "teaching-reference");
      for (const letter of lesson.letters) {
        const row = add(list, "div", "teaching-reference-row");
        add(row, "strong", "reference-jamo", letter);
        add(row, "span", "", lesson.batchim_pronunciation?.[letter] ||
          `${lesson.letter_romanization?.[letter] || ""} · ${lesson.pronunciation?.[letter] || ""}`);
      }
    }
    for (const [group, rule] of Object.entries(lesson.batchim_pronunciation_rules || {}))
      add(screen, "p", "support", `${group}: ${rule}`);
    for (const pair of (lesson.confusion_pairs || []).slice(0, 4))
      add(screen, "p", "support", `Look closely: ${pair.join(" vs ")}`);
    const words = (lesson.words?.length ? lesson.words : lesson.vocabulary || []).slice(0, 3);
    if (words.length) add(screen, "p", "support", `Words to look forward to: ${words.map(w => `${w.word} (${w.meaning})`).join(" · ")}`);
    const rules = lesson.block_rules || {};
    for (const key of ["vertical_layout", "horizontal_layout"])
      if (rules[key]) add(screen, "p", "support", plainPrompt(rules[key]));
  }
  const nextLabel = index + 1 >= cards.length ? "Start practice" :
    index === 0 ? lesson.batchim_pronunciation ? "Explore bottom sounds" :
      lesson.letters?.length ? "Meet the letters" : "Explore this lesson" : "Continue";
  controls.appendChild(button(nextLabel, "primary", nextTeaching));
  if (index > 0) controls.appendChild(button("Back", "secondary", () => { teaching.index--; renderTeaching(); }));
  if (index + 1 < cards.length)
    controls.appendChild(button("Go straight to practice", "secondary", finishTeaching));
  saveState();
}
function curriculumClear(kind) {
  clear(kind);
  openCard = null;
  awaitInput = null;
}
async function chooseCurriculum(answer) {
  if (busy || await resumeIfPaused()) return;
  await callFlow("submit", answer, takeActive());
}
async function submitCurriculum(answer) {
  if (busy || await resumeIfPaused()) return;
  const card = openCard, input = awaitInput;
  if (!card || !input) return;
  const msFromCard = Math.round(performance.now() - cardShownAt);
  const events = await callFlow("submit", answer, takeActive());
  if (!events) return;
  const result = events.find(event => ["result", "check_feedback", "check_practice_feedback"].includes(event.kind));
  if (result) {
    answerLog.push({lesson: Number(python("quiz.current_lesson['id']")),
      context: card.kind, mode: card.mode || "reading_check", answer,
      correct: result.correct, skipped: Boolean(result.skipped),
      hint_used: hinted, ms_from_card: msFromCard});
    saveState();
  }
}
function curriculumQuestion(card, overlay = null) {
  const isNew = openCard !== card;
  if (isNew) { hinted = false; cardShownAt = performance.now(); }
  if (overlay?.kind === "hint" || overlay?.kind === "check_hint") hinted = true;
  openCard = card;
  awaitInput = {input: card.input || "text", choices: card.choices || []};
  clear(card.kind);
  if (card.kind === "question") {
    add(screen, "span", "eyebrow", card.mode.replaceAll("_", " "));
    add(screen, "p", "prompt curriculum-prompt", plainPrompt(card.prompt));
    if (card.display) add(screen, "div", "big-hangul", card.display);
    if (card.round) add(screen, "p", "support", `${card.round.index} of ${card.round.size} in this round`);
  } else {
    add(screen, "span", "eyebrow", card.kind === "check_question"
      ? card.retry ? "Independent retry" : `${card.number} of ${card.size} · ${card.transfer ? "New combination" : "Lesson item"}`
      : "Practice this one");
    add(screen, "div", "big-hangul word", card.letter);
    add(screen, "p", "support", card.kind === "check_practice_question"
      ? card.hint : "Type its sound in English letters.");
  }
  if (overlay) add(screen, "p", overlay.kind.includes("hint") ? "hint-text" : "notice",
    overlay.text || overlay.hint || (overlay.kind === "check_script_mismatch"
      ? "Use English letters for the sound." : "Try /hint, /skip, /back, or /quit."));
  if (awaitInput.input === "choice") {
    const choices = add(controls, "div", "choices");
    for (const choice of awaitInput.choices)
      choices.appendChild(button(choice, "choice curriculum-choice", () => submitCurriculum(choice)));
  } else {
    const form = add(controls, "form", "text-form");
    const field = add(form, "input");
    field.type = "text";
    field.autocapitalize = "none";
    field.autocomplete = "off";
    field.setAttribute("autocorrect", "off");
    field.spellcheck = false;
    field.setAttribute("enterkeyhint", "go");
    field.setAttribute("aria-label", "Your answer");
    const go = add(form, "button", "primary", "Answer");
    go.type = "submit";
    form.addEventListener("submit", event => { event.preventDefault(); submitCurriculum(field.value); });
  }
  const actions = add(controls, "div", "curriculum-actions");
  if (card.kind !== "check_practice_question" && (card.kind !== "question" || card.hint_available))
    actions.appendChild(button("Hint", "secondary", () => submitCurriculum("/hint")));
  if (card.kind !== "check_practice_question")
    actions.appendChild(button("Skip", "secondary", () => submitCurriculum("/skip")));
  if (card.kind === "question") {
    actions.appendChild(button("Reading check", "secondary", () => submitCurriculum("/check")));
    actions.appendChild(button("Next lesson", "secondary", () => submitCurriculum("/next")));
  } else actions.appendChild(button("Back to practice", "secondary", () => submitCurriculum("/back")));
  actions.appendChild(button("Save and quit", "secondary", () => submitCurriculum("/quit")));
}
function curriculumEvent(event) {
  visibleEvent = event;
  if (["question", "check_question", "check_practice_question"].includes(event.kind)) {
    curriculumQuestion(event);
    return;
  }
  if (["hint", "notice", "check_hint", "check_commands", "check_script_mismatch"].includes(event.kind)
      && openCard) {
    curriculumQuestion(openCard, event);
    return;
  }
  curriculumClear(event.kind);
  if (event.kind === "lesson_started") {
    startTeaching(event.lesson, 0, event.message || "");
  } else if (event.kind === "result") {
    add(screen, "span", `eyebrow ${event.correct ? "correct" : "incorrect"}`,
      event.skipped ? "Skipped" : event.correct ? "Correct" : "Not yet");
    add(screen, "p", "fact", plainPrompt(event.feedback ||
      (event.skipped ? `${event.letter} is ${event.correct_answer}.` : event.expected)));
    if (event.assisted) add(screen, "p", "support", "With a hint — try it alone to make it solid.");
    continueButton();
  } else if (event.kind === "round_card") {
    add(screen, "span", "eyebrow", `Round ${event.round_no}`);
    add(screen, "p", "score-number", `${event.right} of ${event.asked}`);
    add(screen, "p", "support", `${event.mastery.mastered_count} of ${event.mastery.pool_size} lesson items solid`);
    if (event.ready) add(screen, "p", "fact", "Ready for the reading check.");
    else if (event.stuck) add(screen, "p", "support", "A tough round. You can move on and return later.");
    if (event.solid_now.length) add(screen, "p", "support", `Solid now: ${event.solid_now.join(" · ")}`);
    if (event.left.length) add(screen, "p", "support", `Still to go: ${event.left.slice(0, 6).join(" · ")}`);
    for (const milestone of event.milestones) add(screen, "p", "support", milestone);
    if (event.reward?.word) add(screen, "p", "fact", `${event.reward.word} · ${event.reward.meaning || ""}`);
    if (event.actions.includes("check"))
      controls.appendChild(button("Reading check", "primary", () => chooseCurriculum("/check")));
    if (event.actions.includes("next"))
      controls.appendChild(button(`Lesson ${event.next_lesson.id}`, "secondary", () => chooseCurriculum("/next")));
    controls.appendChild(button("Continue practice", "secondary", () => chooseCurriculum("")));
    controls.appendChild(button("Save and quit", "secondary", () => chooseCurriculum("/quit")));
  } else if (event.kind === "check_intro") {
    add(screen, "span", "eyebrow", "Read on your own");
    add(screen, "p", "fact", `${event.size} prompts · ${event.pass_score} to pass`);
    add(screen, "p", "support", "No choices or timer. Hints help, but those items return for an independent try.");
    continueButton("Begin check");
  } else if (event.kind === "check_input" && event.phase === "retry") {
    add(screen, "span", "eyebrow", "Try again?");
    add(screen, "p", "support", "Take another reading check or return to practice.");
    controls.appendChild(button("Retry reading check", "primary", () => chooseCurriculum("r")));
    controls.appendChild(button("Back to practice", "secondary", () => chooseCurriculum("/back")));
    controls.appendChild(button("Save and quit", "secondary", () => chooseCurriculum("/quit")));
  } else if (event.kind === "check_feedback" || event.kind === "check_practice_feedback") {
    add(screen, "span", `eyebrow ${event.correct ? "correct" : "incorrect"}`,
      event.assisted ? "With help" : event.correct ? "Read correctly" : "Not yet");
    add(screen, "div", "big-hangul word", event.letter);
    add(screen, "p", "fact", event.correct_answer);
    if (event.assisted) add(screen, "p", "support", "This one returns for an independent try.");
    continueButton();
  } else if (event.kind === "check_score") {
    add(screen, "span", `eyebrow ${event.passed ? "correct" : "incorrect"}`,
      event.passed ? "Reading check passed" : "Keep practicing");
    add(screen, "p", "score-number", `${event.correct} of ${event.size}`);
    add(screen, "p", "support", `Need ${event.pass_score} read independently.`);
    continueButton();
  } else if (event.kind === "check_practice_intro") {
    add(screen, "span", "eyebrow", "Targeted practice");
    add(screen, "p", "support", "Practice the tricky items, then try the check again.");
    continueButton();
  } else if (event.kind === "lesson_mastered") {
    const guide = add(screen, "div", "teaching-head");
    character(guide, "sejong");
    add(guide, "span", "name-tag", "King Sejong");
    add(screen, "span", "eyebrow correct", "Lesson mastered");
    add(screen, "p", "fact", `${event.mastered_count} of ${event.pool_size} items solid`);
    if (event.words.length) add(screen, "p", "support",
      `Words you can read: ${event.words.slice(0, 6).map(word => `${word.word} · ${word.meaning}`).join("  ·  ")}`);
    continueButton();
  } else if (event.kind === "advance_prompt") {
    add(screen, "span", "eyebrow", "What next?");
    add(screen, "p", "fact", `Lesson ${event.lesson_id} is ready.`);
    controls.appendChild(button(`Start Lesson ${event.lesson_id}`, "primary", () => chooseCurriculum("")));
    controls.appendChild(button("Stay here", "secondary", () => chooseCurriculum("n")));
    controls.appendChild(button("Browse lessons", "secondary", () => chooseCurriculum("/lessons")));
    controls.appendChild(button("Save and quit", "secondary", () => chooseCurriculum("/quit")));
  } else if (event.kind === "advance_lessons") {
    add(screen, "span", "eyebrow", "Lessons");
    for (const lesson of event.lessons)
      controls.appendChild(button(`${lesson.id}. ${lesson.title}${lesson.completed ? " ✓" : ""}`,
        "secondary", () => chooseCurriculum(`/lesson ${lesson.id}`)));
    controls.appendChild(button("Back", "primary", showNext));
  } else if (event.kind === "curriculum_complete") {
    add(screen, "span", "eyebrow correct", "Curriculum complete");
    add(screen, "p", "fact", "You have read your way through all 12 lessons. 축하합니다!");
    continueButton();
  } else if (event.kind === "finished") {
    finishedAt ||= new Date().toISOString();
    saveState();
    add(screen, "span", "eyebrow", event.outcome === "quit" ? "Place saved" : "Complete");
    add(screen, "p", "fact", event.outcome === "quit" ? "Come back to this lesson any time." : "Well done!");
    if (event.outcome === "quit")
      controls.appendChild(button("Resume lesson", "primary", async () => {
        await callFlow("resume", "reopen");
      }));
    controls.appendChild(button("Start over", "secondary", confirmReset));
  } else {
    const messages = {
      check_unavailable: event.reason || "Reading check unavailable. Back to practice.",
      advance_stay: "Staying in this lesson.",
      advance_help: "Choose the next lesson, stay here, or browse the lessons.",
      advance_missing_lesson: `Choose a lesson from 1 to ${event.total}.`,
      notice: event.text || "",
    };
    if (!(event.kind in messages)) { console.warn("Unknown event kind skipped", event.kind); return false; }
    add(screen, "p", "notice", messages[event.kind]);
    continueButton();
  }
  return true;
}
async function showCurriculumNext() {
  while (pending.length) {
    const event = pending.shift();
    if (event.kind === "round_prompt" || event.kind === "check_input" && event.phase !== "retry") continue;
    if (curriculumEvent(event) !== false) return;
  }
}
async function showNext() {
  if (COURSE === "curriculum") return teaching ? nextTeaching() : showCurriculumNext();
  while (pending.length) {
    const event = pending.shift();
    visibleEvent = event;
    if (event.kind === "stage") { stage(event); continue; }
    if (event.kind === "question" || event.kind === "predict") { setCard(event); return; }
    if (event.kind === "hint" || event.kind === "notice") {
      if (openCard) { awaitInput = takeAwait(); renderCard(openCard, event); return; }
      console.warn("Input message without a card", event);
      continue;
    }
    if (event.kind === "await") {
      if (event.input === "continue") { await callFlow("submit", "", takeActive()); return; }
      console.warn("Await without a card", event);
      continue;
    }
    if (["narrator", "before_word", "letter_intro", "reveal", "result", "word_read", "score", "milestone", "finished"].includes(event.kind)) {
      renderEvent(event);
      return;
    }
    console.warn("Unknown event kind skipped", event.kind);
  }
}

function clockTick(now = performance.now(), leavingPage = false) {
  if (!paused && (!document.hidden || leavingPage)) {
    const elapsed = Math.max(0, now - lastTick);
    activeBucket += Math.min(elapsed, 120000);
    if (elapsed >= 120000) paused = true;
  }
  lastTick = now;
}
function takeActive() { clockTick(); const ms = Math.round(activeBucket); activeBucket = 0; return ms; }
async function resumeIfPaused() {
  clockTick();
  if (!paused) return false;
  paused = false;
  lastTick = performance.now();
  await callFlow("resume", "pause");
  return true;
}
document.addEventListener("visibilitychange", () => {
  if (document.hidden) { clockTick(performance.now(), true); paused = true; }
  else lastTick = performance.now();
});

function python(expression) { return pyodide.runPython(expression); }
function exportState() { return python("flow.export_state()"); }
function readStored() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"); }
  catch (error) { storageWorked = false; console.warn("Storage unavailable", error); return null; }
}
function backupCurriculumSave(raw) {
  const base = `${STORAGE_KEY}.backup`;
  for (let index = 0; index < 100; index++) {
    const key = index ? `${base}.${index}` : base;
    const previous = localStorage.getItem(key);
    if (previous === raw) return key;
    if (previous === null) {
      localStorage.setItem(key, raw);
      if (localStorage.getItem(key) !== raw) throw new Error("The save backup could not be verified.");
      return key;
    }
  }
  throw new Error("No free save backup slot is available.");
}
function curriculumEnvelope(saved) {
  if (!saved || typeof saved !== "object" || Array.isArray(saved))
    throw new Error("The saved lesson is not a save envelope.");
  const current = saved.save_kind === CURRICULUM_SAVE_KIND &&
    saved.save_version === CURRICULUM_SAVE_VERSION;
  const legacy = saved.save_kind === undefined && saved.save_version === undefined &&
    /^curriculum-web-1:[0-9a-f]{16}$/.test(saved.app_version);
  if (!current && !legacy) throw new Error("The saved lesson format is unsupported.");
  if (typeof saved.state !== "string" || !saved.state)
    throw new Error("The saved controller state is missing.");
  if (saved.teaching != null &&
      (typeof saved.teaching !== "object" || Array.isArray(saved.teaching)))
    throw new Error("The saved teaching state is invalid.");
  return {saved, legacy};
}
function saveState() {
  if (!flowReady || COURSE === "curriculum" && saveBlocked) return;
  try {
    const teachingState = teaching?.kind === "lesson1"
      ? {kind: "lesson1", lesson_id: 1, state: python("teaching_flow.export_state()"),
        message: teaching.message}
      : teaching ? {lesson_id: teaching.lesson.id, index: teaching.index,
        message: teaching.message} : null;
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      ...(COURSE === "curriculum" ? {save_kind: CURRICULUM_SAVE_KIND,
        save_version: CURRICULUM_SAVE_VERSION} : {}),
      app_version: appVersion, state: exportState(),
      started_at: startedAt, finished_at: finishedAt, log: answerLog,
      teaching: teachingState}));
  } catch (error) { storageWorked = false; console.warn("Storage unavailable", error); }
}
async function callFlow(method, value, ms = 0) {
  if (busy) return;
  busy = true;
  try {
    const lettersKnown = method === "submit" && COURSE === "sejong"
      ? Number(python("len(flow.letters_known)")) : 0;
    const phase = method === "submit" ? String(python("flow.phase")) : "";
    pyodide.globals.set("web_value", value);
    pyodide.globals.set("web_ms", ms);
    const expression = method === "submit"
      ? "json.dumps(flow.submit(str(web_value), int(web_ms)), ensure_ascii=False)"
      : "json.dumps(flow.resume(str(web_value)), ensure_ascii=False)";
    const events = JSON.parse(python(expression));
    if (method === "submit") submissionMs.push({ms, phase, letters_known: lettersKnown});
    eventHistory.push(structuredClone(events));
    if (method === "resume" && COURSE === "curriculum" &&
        !events.some(event => event.kind === "finished")) finishedAt = null;
    if (method === "submit" || method === "resume" && COURSE === "curriculum") saveState();
    pending = events.slice();
    await showNext();
    return events;
  } catch (error) { showFailure(error); }
  finally { busy = false; }
}
async function submitAnswer(answer) {
  if (busy || await resumeIfPaused()) return;
  const card = openCard, input = awaitInput;
  if (!card || !input) return;
  const msFromCard = Math.round(performance.now() - cardShownAt);
  const active = takeActive();
  const events = await callFlow("submit", answer, active);
  if (!events) return;
  const result = events.find(event => event.kind === "result");
  const reveal = events.find(event => event.kind === "reveal");
  if (result || reveal) {
    answerLog.push({qid: card.qid || null, context: card.context || "predict",
      mode: card.mode || "predict", input_type: input.input, answer,
      correct: result ? result.correct : reveal.guessed_right,
      hint_used: hinted, ms_from_card: msFromCard});
    saveState();
  }
}

function showLoading(step = 0, error = null) {
  clear("loading");
  add(screen, "span", "eyebrow", COURSE === "curriculum" ? "HANGUL TUTOR" : "THE SEJONG TEST");
  add(screen, "h1", "line-text", error ? "The lesson could not load."
    : COURSE === "curriculum" ? "Learn Hangul, one lesson at a time." : "First words, one letter at a time.");
  const steps = add(screen, "div", "loading-steps");
  ["Download Python · about 14 MB", "Load the lessons", "Start"].forEach((label, index) => {
    const row = add(steps, "div", "loading-step");
    add(row, "span", "", label);
    add(row, "span", "", loadingTimes[index] != null ? `${loadingTimes[index].toFixed(1)} s` :
      index < step ? "ready" : index === step ? "working…" : "waiting");
  });
  if (error) {
    add(screen, "p", "notice", String(error));
    controls.appendChild(button("Retry", "primary", bootstrap));
  }
}
function showFailure(error) { console.error(error); showLoading(0, error?.message || error); }
async function fetchEngineFiles() {
  if (COURSE === "curriculum") {
    const teachingReply = await fetch("./teaching.json");
    if (!teachingReply.ok) throw new Error(`Letter guide: HTTP ${teachingReply.status}`);
    teachingData = await teachingReply.json();
  }
  const response = await fetch("./engine/manifest.json");
  if (!response.ok) throw new Error(`Lesson manifest: HTTP ${response.status}`);
  const manifest = await response.json();
  appVersion = COURSE === "curriculum"
    ? `curriculum-web-1:${manifest.app_version}`
    : `sejong-web-1:${manifest.sejong_version || manifest.app_version}`;
  const files = await Promise.all(manifest.files.map(async entry => {
    const reply = await fetch(`./engine/${entry.path}`);
    if (!reply.ok) throw new Error(`${entry.path}: HTTP ${reply.status}`);
    const bytes = new Uint8Array(await reply.arrayBuffer());
    if (bytes.length !== entry.bytes) throw new Error(`${entry.path}: incomplete download`);
    return {path: entry.path, bytes};
  }));
  pyodide.FS.mkdirTree("/app/data");
  for (const file of files) pyodide.FS.writeFile(`/app/${file.path}`, file.bytes);
  python("import os, sys, json; os.chdir('/app'); sys.path.insert(0, '/app'); from hangul_quiz_engine import HangulQuiz; from sejong_flow import SejongFlow; from curriculum_flow import CurriculumFlow, LessonOneTeaching; content = json.load(open('/app/data/sejong.json', encoding='utf-8'))");
}
async function startFresh(message = "") {
  teaching = null;
  pyodide.globals.set("web_seed", TEST_SEED);
  if (COURSE === "curriculum") {
    python("import random; random.seed(web_seed) if web_seed is not None else None; quiz = HangulQuiz(persist=False); flow = CurriculumFlow(quiz)");
  } else {
    python("quiz = HangulQuiz(persist=False); flow = SejongFlow(quiz, content, seed=web_seed)");
  }
  startedAt = new Date().toISOString(); finishedAt = null; answerLog = []; eventHistory = []; submissionMs = [];
  activeBucket = 0; lastTick = performance.now(); paused = false;
  const events = JSON.parse(python("json.dumps(flow.start(), ensure_ascii=False)"));
  eventHistory.push(structuredClone(events)); pending = events.slice(); flowReady = true;
  $("menu-button").hidden = false;
  await showNext();
  if (message) status.textContent = message;
}
function showSaveRecovery(raw, error) {
  saveBlocked = true; flowReady = false; teaching = null; pending = [];
  $("menu-button").hidden = true;
  let backupKey = null;
  if (raw !== null) {
    try { backupKey = backupCurriculumSave(raw); }
    catch (backupError) { console.warn("Save backup unavailable", backupError); }
  }
  clear("save_recovery");
  add(screen, "span", "eyebrow", "SAVED LESSON");
  add(screen, "h1", "line-text", raw === null ? "The lesson could not load." : "Your saved place is still here.");
  add(screen, "p", "support", raw === null
    ? "Storage could not be read. Try loading again before starting fresh."
    : "This version could not open it. Your original save has not been replaced.");
  add(screen, "p", "notice", String(error?.message || error));
  if (backupKey) add(screen, "p", "support", "A separate copy is kept on this device.");
  if (raw !== null) {
    const area = add(screen, "textarea", "recovery-data");
    area.readOnly = true; area.value = raw;
    controls.appendChild(button("Copy original save", "primary", async () => {
      try { await navigator.clipboard.writeText(raw); }
      catch (_) { area.focus(); area.select(); }
    }));
    controls.appendChild(button("Download original save", "secondary", () => {
      const url = URL.createObjectURL(new Blob([raw], {type: "application/json"}));
      const link = document.createElement("a");
      link.href = url; link.download = "hangul-curriculum-recovery.json";
      link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    }));
  }
  controls.appendChild(button("Try loading again", "secondary", bootstrap));
  controls.appendChild(button("Start fresh instead", "secondary", () => {
    const box = dialog("Start a fresh curriculum?");
    add(box, "p", "support", "Your saved place will be kept as a separate backup before a new lesson begins.");
    const actions = add(box, "div", "dialog-buttons");
    actions.appendChild(button("Keep my save", "secondary", closeDialog));
    actions.appendChild(button("Start fresh", "primary", async () => {
      try {
        if (raw !== null) backupCurriculumSave(raw);
        localStorage.removeItem(STORAGE_KEY);
        if (localStorage.getItem(STORAGE_KEY) !== null) throw new Error("The old save could not be cleared.");
        closeDialog(); saveBlocked = false;
        await startFresh();
      } catch (freshError) {
        if (raw !== null) {
          try { localStorage.setItem(STORAGE_KEY, raw); }
          catch (restoreError) { console.warn("Original save is in the separate backup", restoreError); }
        }
        closeDialog(); showSaveRecovery(raw, freshError);
      }
    }));
  }));
}
async function restoreCurriculum() {
  saveBlocked = true;
  let raw;
  try { raw = localStorage.getItem(STORAGE_KEY); }
  catch (error) { storageWorked = false; showSaveRecovery(null, error); return; }
  if (raw === null) { saveBlocked = false; await startFresh(); return; }
  try {
    const {saved, legacy} = curriculumEnvelope(JSON.parse(raw));
    if (legacy) backupCurriculumSave(raw);
    pyodide.globals.set("web_state", saved.state);
    python("quiz = HangulQuiz(persist=False); flow = CurriculumFlow.from_state(quiz, web_state)");
    const events = JSON.parse(python("json.dumps(flow.resume('reopen'), ensure_ascii=False)"));
    if (!Array.isArray(events) || !events.length) throw new Error("The saved screen could not be restored.");
    const validatedState = exportState();
    pyodide.globals.set("web_validated_state", validatedState);
    python("CurriculumFlow.from_state(HangulQuiz(persist=False), web_validated_state)");
    if (saved.teaching != null) {
      const lessonId = Number(python("quiz.current_lesson['id']"));
      if (String(python("flow.phase")) !== "practice" || saved.teaching.lesson_id !== lessonId)
        throw new Error("The saved teaching step does not match this lesson.");
      if (saved.teaching.kind === "lesson1") {
        if (lessonId !== 1 || typeof saved.teaching.state !== "string")
          throw new Error("The saved Lesson 1 guide is invalid.");
        pyodide.globals.set("web_teaching_state", saved.teaching.state);
        python("LessonOneTeaching.from_state(quiz.current_lesson, {}, web_teaching_state)");
      } else if (!Number.isInteger(saved.teaching.index) ||
                 saved.teaching.index < 0 ||
                 saved.teaching.index >= teachingCards(JSON.parse(python("json.dumps(quiz._lesson_info(), ensure_ascii=False)"))).length) {
        throw new Error("The saved teaching card is invalid.");
      }
    }
    startedAt = saved.started_at || new Date().toISOString();
    finishedAt = saved.finished_at || null;
    answerLog = Array.isArray(saved.log) ? saved.log : [];
    if (!events.some(event => event.kind === "finished")) finishedAt = null;
    eventHistory = [structuredClone(events)]; pending = events.slice();
    flowReady = true;
    $("menu-button").hidden = false;
    const lesson = JSON.parse(python("json.dumps(quiz._lesson_info(), ensure_ascii=False)"));
    curriculumHeader(lesson);
    if (saved.teaching != null) {
      startTeaching(lesson, saved.teaching.kind === "lesson1"
        ? saved.teaching.state : saved.teaching.index, saved.teaching.message || "");
    } else await showNext();
    if (legacy) {
      const migrated = JSON.stringify({...saved, save_kind: CURRICULUM_SAVE_KIND,
        save_version: CURRICULUM_SAVE_VERSION, app_version: appVersion,
        state: validatedState, teaching: saved.teaching ?? null});
      try {
        localStorage.setItem(STORAGE_KEY, migrated);
        if (localStorage.getItem(STORAGE_KEY) !== migrated)
          throw new Error("The migrated save could not be verified.");
      } catch (error) {
        if (localStorage.getItem(STORAGE_KEY) !== raw) localStorage.setItem(STORAGE_KEY, raw);
        throw error;
      }
    }
    saveBlocked = false;
  } catch (error) { showSaveRecovery(raw, error); }
}
async function bootstrap() {
  if (busy) return;
  busy = true; flowReady = false; loadingTimes = {};
  try {
    showLoading(0);
    let started = performance.now();
    if (!window.loadPyodide) throw new Error("Bundled Python is missing. Run scripts/fetch_pyodide.py.");
    pyodide ||= await window.loadPyodide({indexURL: new URL("./pyodide/", document.baseURI).href});
    loadingTimes[0] = (performance.now() - started) / 1000; showLoading(1);
    started = performance.now();
    await fetchEngineFiles();
    loadingTimes[1] = (performance.now() - started) / 1000; showLoading(2);
    started = performance.now();
    if (COURSE === "curriculum") await restoreCurriculum();
    else {
      const saved = readStored();
      let message = "";
      if (saved?.state && saved.app_version === appVersion) {
        try {
          pyodide.globals.set("web_state", saved.state);
          python("quiz = HangulQuiz(persist=False); flow = SejongFlow.from_state(quiz, content, web_state)");
          startedAt = saved.started_at || new Date().toISOString();
          finishedAt = saved.finished_at || null;
          answerLog = Array.isArray(saved.log) ? saved.log : [];
          flowReady = true;
          const events = JSON.parse(python("json.dumps(flow.resume('reopen'), ensure_ascii=False)"));
          eventHistory = [structuredClone(events)]; pending = events.slice();
          $("menu-button").hidden = false;
          await showNext();
        } catch (error) { message = "Saved place could not be read. Starting fresh."; await startFresh(message); }
      } else {
        if (saved?.state) message = "The lesson changed. Starting fresh.";
        await startFresh(message);
      }
    }
    loadingTimes[2] = (performance.now() - started) / 1000;
  } catch (error) {
    if (COURSE === "curriculum") {
      let raw = null;
      try { raw = localStorage.getItem(STORAGE_KEY); } catch (_) { storageWorked = false; }
      if (raw !== null) showSaveRecovery(raw, error);
      else showFailure(error);
    } else showFailure(error);
  }
  finally { busy = false; }
}

function closeDialog() { dialogLayer.hidden = true; dialogLayer.replaceChildren(); }
function dialog(title) {
  dialogLayer.hidden = false; dialogLayer.replaceChildren();
  const box = add(dialogLayer, "div", "dialog");
  box.setAttribute("role", "dialog"); box.setAttribute("aria-modal", "true");
  add(box, "h2", "", title);
  return box;
}
function showMenu() {
  const box = dialog("Your lesson");
  const actions = add(box, "div", "menu-actions");
  actions.appendChild(button("Copy results", "secondary", showResults));
  if (COURSE === "curriculum" && openCard?.kind === "question")
    actions.appendChild(button("Review this lesson", "secondary", () => {
      closeDialog();
      const lesson = JSON.parse(python("json.dumps(quiz._lesson_info(), ensure_ascii=False)"));
      startTeaching(lesson);
    }));
  actions.appendChild(button(COURSE === "curriculum" ? "Sejong Test" : "Full lessons", "secondary", () => {
    location.href = COURSE === "curriculum" ? "./" : "./?course=curriculum";
  }));
  actions.appendChild(button("Start over", "secondary", confirmReset));
  actions.appendChild(button("Close", "primary", closeDialog));
}
function resultsJSON() {
  const state = exportState();
  const report = {app_version: appVersion, user_agent: navigator.userAgent,
    started_at: startedAt, finished_at: finishedAt, export_state: state, log: answerLog};
  if (COURSE === "sejong") report.active_ms = JSON.parse(state).active_ms;
  else report.session_total = JSON.parse(state).session.session_total;
  return JSON.stringify(report, null, 2);
}
function showResults() {
  const value = resultsJSON();
  const box = dialog("Playtest results");
  add(box, "p", "support", "These results stay on this device until you copy them.");
  const area = add(box, "textarea");
  area.readOnly = true; area.value = value;
  const actions = add(box, "div", "dialog-buttons");
  actions.appendChild(button("Copy JSON", "primary", async () => {
    try {
      await navigator.clipboard.writeText(value);
      add(box, "p", "support", "Copied.");
    } catch (_) {
      area.focus(); area.select();
      add(box, "p", "support", "Select and copy the highlighted results.");
    }
  }));
  actions.appendChild(button("Close", "secondary", closeDialog));
}
function confirmReset() {
  const box = dialog("Start over?");
  add(box, "p", "support", COURSE === "curriculum"
    ? "This clears the active saved place and local answer log. A migration backup may remain on this device."
    : "This clears the saved place and the local answer log.");
  const actions = add(box, "div", "dialog-buttons");
  actions.appendChild(button("Keep my place", "secondary", closeDialog));
  actions.appendChild(button("Start over", "primary", async () => {
    try { localStorage.removeItem(STORAGE_KEY); } catch (error) { console.warn("Storage unavailable", error); }
    closeDialog(); await startFresh();
  }));
}
$("menu-button").addEventListener("click", showMenu);

if (TEST && COURSE === "sejong") window.__sejongTest = {
  answer: () => flowReady ? python("flow.current['target'] if flow.phase == 'predict_reveal' else flow.current['answer'] if flow.current else ''") : null,
  current: () => ({card: openCard, await: awaitInput, visible: visibleEvent}),
  state: () => flowReady ? JSON.parse(exportState()) : null,
  history: () => eventHistory,
  log: () => answerLog,
  submissions: () => submissionMs,
  clock: () => ({activeBucket, paused}),
  inject: event => { pending.unshift(event); showNext(); },
  idle: ms => { lastTick -= ms; clockTick(); },
  hidden: () => { clockTick(); paused = true; },
  timings: () => loadingTimes,
  ready: () => flowReady && !busy,
  next: showNext,
};
if (TEST && COURSE === "curriculum") window.__curriculumTest = {
  answer: () => flowReady ? python("flow.current_question.correct_answer if flow.phase == 'practice' else flow.check.check.current.correct_answer if flow.phase == 'check' and flow.check.phase == 'question' else ''") : null,
  current: () => ({card: openCard, input: awaitInput, visible: visibleEvent}),
  state: () => flowReady ? JSON.parse(exportState()) : null,
  history: () => eventHistory,
  ready: () => flowReady && !busy,
  submit: answer => chooseCurriculum(answer),
  next: showNext,
  solidify: () => python("for target in quiz._mastery_set(quiz.current_lesson):\n item = quiz._get_item(quiz._compose_bare_vowel(target))\n item.history = '111'\n quiz._save_item(item)"),
};
bootstrap();
