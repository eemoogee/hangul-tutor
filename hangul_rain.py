"""
hangul_rain.py — Hangul "rain" typing game for the Hangul Tutor CLI.

Invader / Level classes adapted from kgutwin/typing (MIT licensed):
    https://github.com/kgutwin/typing
The original drops English words from the top of the screen and you type them
to shoot them down. Here each falling invader is a Hangul syllable block that
you "shoot" by typing its romanization letter-by-letter.

This module is self-contained: it does NOT import hangul_quiz_engine, so it
can be imported and unit-tested without loading the quiz engine's heavy
startup (progress files, corpus exclusion sets, etc.). The romanization logic
below is a standalone copy of the engine's own — keep the two in sync if the
app's spelling system ever changes.

Public entry points:
    syllable_to_roman(hangul) -> str
    launch_rain_mode(quiz)
"""

import json
import os
import random
import re
import time
from pathlib import Path

# `curses` is a Unix stdlib module. It is NOT importable from stock Windows
# Python (the `windows-curses` package provides it). The rest of this module —
# in particular syllable_to_roman — must stay importable without it, so the
# import is deferred to the point the game actually launches. `_load_curses`
# returns the module or raises a clear error at launch time.
try:
    import curses  # noqa: F401
except ImportError:
    curses = None


def _require_curses():
    if curses is None:
        raise RuntimeError(
            "The Hangul Rain game mode needs the `curses` module, which is "
            "not available on this Python (Windows). Install it with "
            "`pip install windows-curses` to play."
        )
    return curses


# ── Romanization (standalone copy of hangul_quiz_engine's logic) ─────────────

# The exact spelling system read_aloud grades typed answers against — copied
# verbatim from hangul_quiz_engine.ROMANIZATION. Pulled here so this module
# stands alone.
ROMANIZATION = {
    'ㄱ': 'g', 'ㄴ': 'n', 'ㄷ': 'd', 'ㄹ': 'r/l', 'ㅁ': 'm',
    'ㅂ': 'b', 'ㅅ': 's', 'ㅇ': 'ng', 'ㅈ': 'j', 'ㅊ': 'ch',
    'ㅋ': 'k', 'ㅌ': 't', 'ㅍ': 'p', 'ㅎ': 'h',
    'ㄲ': 'kk', 'ㄸ': 'tt', 'ㅃ': 'pp', 'ㅆ': 'ss', 'ㅉ': 'jj',
    'ㅏ': 'a', 'ㅓ': 'eo', 'ㅗ': 'o', 'ㅜ': 'u', 'ㅡ': 'eu', 'ㅣ': 'i',
    'ㅑ': 'ya', 'ㅕ': 'yeo', 'ㅛ': 'yo', 'ㅠ': 'yu',
    'ㅐ': 'ae', 'ㅔ': 'e', 'ㅒ': 'yae', 'ㅖ': 'ye',
    'ㅘ': 'wa', 'ㅙ': 'wae', 'ㅚ': 'oe', 'ㅝ': 'wo', 'ㅞ': 'we',
    'ㅟ': 'wi', 'ㅢ': 'ui'
}


def _initial_roman(jamo: str) -> str:
    """Romanization of a jamo in INITIAL position. ㅇ is SILENT here (the
    placeholder, contributes no sound), and ㄹ is 'r' — the 'r/l' in
    ROMANIZATION is a display convention for the bare letter, not a real
    initial-consonant spelling."""
    if jamo == "ㅇ":
        return ""
    if jamo == "ㄹ":
        return "r"
    return ROMANIZATION.get(jamo, "?")


# Curriculum is loaded once at import, purely to read batchim_pronunciation_rules
# (the same authoritative source hangul_quiz_engine._batchim_sound derives from).
_CURRICULUM_PATH = Path(__file__).parent / "data" / "curriculum.json"
try:
    with open(_CURRICULUM_PATH, encoding="utf-8") as _f:
        _CURRICULUM = json.load(_f)
except (OSError, ValueError):
    _CURRICULUM = {"lessons": []}


def _decompose_syllable(syllable: str) -> tuple:
    """Decompose a Hangul syllable into (choseong, jungseong, jongseong).
    Standalone copy of HangulQuiz._decompose_syllable."""
    if len(syllable) == 1 and ord(syllable) < 0xAC00:
        # Single jamo, not a syllable
        return ('', '', '')

    code = ord(syllable) - 0xAC00
    jong = code % 28
    jung = ((code - jong) // 28) % 21
    cho = ((code - jong) // 28) // 21

    CHOSEONG = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ',
                'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    JUNGSEONG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ',
                 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
    JONGSEONG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ',
                 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ',
                 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

    return (CHOSEONG[cho], JUNGSEONG[jung], JONGSEONG[jong] if jong > 0 else '')


def _batchim_sound(jong: str) -> str:
    """Real pronounced sound for a batchim letter, derived from curriculum
    data (batchim_pronunciation_rules). Standalone copy of
    HangulQuiz._batchim_sound — same authoritative source, same fallback."""
    for lesson in _CURRICULUM.get("lessons", []):
        rules = lesson.get("batchim_pronunciation_rules")
        if not rules:
            continue
        for letters_str, desc in rules.items():
            if jong in letters_str:
                match = re.search(r'\[(\w+)\]', desc)
                if match:
                    return match.group(1)
    # Simplified early-lesson letters taught before batchim rules exist.
    simple = {'ㄱ': 'k', 'ㄴ': 'n', 'ㄷ': 't', 'ㄹ': 'l',
              'ㅁ': 'm', 'ㅂ': 'p', 'ㅇ': 'ng'}
    return simple.get(jong, '?')


def syllable_to_roman(hangul: str) -> str:
    """Romanize a composed Hangul syllable (or a single bare jamo).

    Standalone equivalent of HangulQuiz._hangul_to_roman_hint — no `self`,
    no ENGINE instance required. Returns the romanization string ('가'->'ga',
    '한'->'han'), or the input unchanged if decomposition fails.
    """
    # Single jamo (letter or vowel) — direct lookup.
    if hangul in ROMANIZATION:
        return ROMANIZATION[hangul]

    try:
        cho, jung, jong = _decompose_syllable(hangul)
        roman_cho = _initial_roman(cho)
        roman_jung = ROMANIZATION.get(jung, '?')

        # Silent ㅇ initial with no batchim: just the vowel sound.
        if cho == 'ㅇ' and not jong:
            return roman_jung

        roman_jong = _batchim_sound(jong) if jong else ""
        return f"{roman_cho}{roman_jung}{roman_jong}"
    except Exception:
        return hangul


# ── Game tuning ──────────────────────────────────────────────────────────────
TICK = 0.1
STARTING_LIVES = 3
INVADERS_PER_LEVEL = 20
START_SPEED = 10          # ticks per one-row fall at level 1 (lower = faster)
KEY_ESC = "\x1b"


class _PlayfieldClip:
    """Wraps a curses window so addstr() silently skips any row past
    height-3 (the HUD rows) or above the top edge."""

    def __init__(self, scr):
        self._scr = scr
        self._last_row = scr.getmaxyx()[0] - 3

    def addstr(self, y, x, *args):
        if 0 <= y <= self._last_row:
            self._scr.addstr(y, x, *args)


# ── Invader (adapted from kgutwin/typing, MIT) ───────────────────────────────

class Invader:
    """A falling Hangul syllable. `c` is the display string (always shown
    as-is); `romanization` is what the player must type. `damage` tracks
    position WITHIN the romanization (0..len(romanization)), not in `c`."""

    def __init__(self, hangul: str, romanization: str, init_x: int = 0):
        self.c = hangul
        self.romanization = romanization
        self.x = init_x
        self.y = 0
        self.damage = 0
        self.fall_ticks_left = 0
        self.exploded = False
        self.scored = False

    @classmethod
    def new(cls, hangul: str, romanization: str, max_x: int):
        # Hangul blocks are 2 columns wide in a terminal, and the typing
        # hint underneath ("[ga]") is len(romanization) + 2 wide — keep
        # whichever is wider fully on screen.
        width = max(2 * len(hangul), len(romanization) + 2)
        x = random.randint(1, max(1, max_x - width))
        return cls(hangul, romanization, x)

    def __len__(self):
        # Length is measured in romanization units, not display glyphs.
        return len(self.romanization)

    @property
    def disabled(self):
        if self.exploded:
            return False
        return self.damage >= len(self)

    @property
    def destroyed(self):
        return self.damage >= len(self) + 3

    @property
    def targetable(self):
        return not (self.disabled or self.exploded)

    def hit_by(self, c: str) -> bool:
        """Advance `damage` if `c` matches the next expected romanization
        character. Returns True on a match."""
        if c is None or not self.targetable:
            return False

        if c == self.romanization[self.damage]:
            self.damage += 1
            return True

        return False

    def explode(self):
        if not self.exploded:
            self.exploded = True
            self.damage = len(self)

    def fall(self, speed: int):
        if self.destroyed or self.exploded:
            return

        if self.fall_ticks_left == 0:
            self.y += 1
            self.fall_ticks_left = speed
        else:
            self.fall_ticks_left -= 1

    def draw_to(self, scr):
        # The bottom two rows (height-2 divider, height-1 status line) are
        # reserved for the HUD — never draw an invader, its typing hint or
        # its explosion there. Matters mostly when the window shrinks
        # mid-game and a block ends up below the new playfield.
        scr = _PlayfieldClip(scr)
        if len(self) <= self.damage <= len(self) + 3:
            # Explosion animation — kept verbatim from the original; `len(self)`
            # resolves to the romanization length.
            self.damage += 1
            frame = self.damage - (1 + len(self))
            x = '@' if self.exploded else '*'
            if frame == 0:
                scr.addstr(self.y, self.x, x * len(self))
            elif frame == 1:
                if len(self) == 1:
                    scr.addstr(self.y, self.x - 1, x * 3)
                else:
                    scr.addstr(self.y, self.x - 1,
                               x * 2 + (' ' * (len(self) - 2)) + x * 2)
            elif frame >= 2:
                scr.addstr(self.y - 1, self.x - 2,
                           x + (' ' * (len(self) + 2)) + x)
                scr.addstr(self.y, self.x - 1, x + (' ' * len(self)) + x)
                scr.addstr(self.y + 1, self.x - 2,
                           x + (' ' * (len(self) + 2)) + x)

        elif self.damage > 0:
            # Partially typed (this is the invader being aimed at): show the
            # block highlighted, plus a progress hint below, e.g. [g_] for 가.
            scr.addstr(self.y, self.x, self.c, curses.A_BOLD | curses.A_REVERSE)
            typed = self.romanization[:self.damage]
            remaining = "_" * (len(self) - self.damage)
            hint = "[{}{}]".format(typed, remaining)
            try:
                scr.addstr(self.y + 1, self.x, hint, curses.A_DIM)
            except curses.error:
                pass
        else:
            scr.addstr(self.y, self.x, self.c, curses.A_BOLD)


# ── RainLevel (adapted from kgutwin/typing Level, MIT) ───────────────────────

class RainLevel:
    """A round of Hangul Rain.

    Adapted from the original Level: the city / building destruction mechanic
    is removed entirely. Instead, if any invader reaches the bottom row the
    player loses one life (start with STARTING_LIVES). Game over at 0 lives.
    Kept from the original: falling speed escalation, a score, an
    invaders_left counter, and the HUD line at the bottom. Lives and score
    carry over from one level to the next.
    """

    def __init__(self, n: int, pool: list, previous_points: int = 0,
                 lives: int = STARTING_LIVES):
        self.n = n
        self.pool = pool                      # list of (hangul, romanization)
        self.points = previous_points
        self.invaders = []
        self.invaders_left = INVADERS_PER_LEVEL
        self.lives = lives
        # Each level starts a notch faster than the last.
        self.speed = max(2, START_SPEED - (n - 1))
        self.create_new_in = 10
        self.max_x = 10
        self.bottom_row = 99
        self.misses = 0
        self.last_miss = ""                   # shown briefly in the HUD
        self.miss_flash = 0

    def _target_for(self, c: str):
        """Which invader a keystroke goes to. An invader you've already
        started typing keeps focus (so a shared first letter can't jump to
        a different block halfway through); otherwise the LOWEST matching
        invader — the most urgent one — takes the hit."""
        live = [i for i in self.invaders if i.targetable]
        started = [i for i in live if i.damage > 0]
        if started:
            locked = max(started, key=lambda i: i.y)
            if locked.romanization[locked.damage] == c:
                return locked
            # Wrong letter for the word you're on — allow switching only to
            # a fresh invader that this key starts.
        fresh = [i for i in live if i.damage == 0 and i.romanization[0] == c]
        return max(fresh, key=lambda i: i.y) if fresh else None

    def move(self, c=None):
        """Advance one tick. `c` is the just-typed character (or None)."""
        if c is not None:
            target = self._target_for(c)
            if target is not None:
                # Switching to a new invader abandons any half-typed one.
                for i in self.invaders:
                    if i is not target and i.targetable and i.damage > 0:
                        i.damage = 0
                target.hit_by(c)
            else:
                self.misses += 1
                self.last_miss = c
                self.miss_flash = 8

        for i in self.invaders:
            if i.disabled and not i.scored:
                self.points += self.n * len(i)
                i.scored = True
            elif not i.disabled:
                i.fall(self.speed)

        # Life loss: any live invader that has reached the bottom row.
        for i in self.invaders:
            if not i.destroyed and not i.exploded and i.y >= self.bottom_row:
                i.explode()
                self.lives -= 1

        self.invaders = [i for i in self.invaders if not i.destroyed]
        if self.miss_flash:
            self.miss_flash -= 1

        # Spawn. Speed escalates once per spawn at the level's midpoint —
        # the old check ran every tick while invaders_left sat on a multiple
        # of 12, so the speed dropped to its minimum within a second or two.
        if self.create_new_in > 0:
            self.create_new_in -= 1
        elif self.invaders_left > 0:
            hangul, roman = random.choice(self.pool)
            self.invaders.append(Invader.new(hangul, roman, self.max_x))
            self.invaders_left -= 1
            if self.invaders_left == INVADERS_PER_LEVEL // 2 and self.speed > 2:
                self.speed -= 1
            e = max(11 - self.n, 1)
            self.create_new_in = random.randint(e, 20)

    def draw(self, scr):
        height, width = scr.getmaxyx()
        self.max_x = width - 2
        self.bottom_row = height - 3

        for i in self.invaders:
            try:
                i.draw_to(scr)
            except curses.error:
                pass

        scr.hline(height - 2, 0, '-', width)
        hud = 'Level %d   Score: %d   Left: %d   Lives: %s   (Esc = quit)' % (
            self.n, self.points, self.invaders_left + len(self.invaders),
            '<3 ' * self.lives)
        if self.miss_flash:
            hud += '   miss: %r' % self.last_miss
        try:
            scr.addstr(height - 1, 0, hud[:width - 1])
        except curses.error:
            pass

    @property
    def complete(self):
        return self.invaders_left == 0 and not self.invaders

    @property
    def game_over(self):
        return self.lives <= 0


# ── Game loop / launcher ─────────────────────────────────────────────────────

def _build_pool(quiz) -> list:
    """(hangul, romanization) pairs from the current lesson's quiz pool —
    the same pool the quiz itself draws from, so every lesson is playable
    (the old version read only practice_syllables, leaving Lessons 1, 10
    and 11 with "nothing to play"). Falls back to the current lesson's
    letters' basic vowels if the pool is somehow empty."""
    lesson = getattr(quiz, "current_lesson", None) or {}
    try:
        syllables = quiz._get_lesson_syllable_pool(lesson) if lesson else []
    except Exception:
        syllables = lesson.get("practice_syllables") or []
    if not syllables:
        syllables = ["아", "어", "오", "우", "으", "이"]

    pool = []
    for s in syllables:
        roman = syllable_to_roman(s)
        if "/" in roman:                    # bare ㄹ -> 'r/l': type the first
            roman = roman.split("/")[0]
        if not roman or roman == '?' or roman == s:   # lookup failed
            continue
        pool.append((s, roman))
    return pool


def _center(scr, y: int, text: str, attr=0):
    height, width = scr.getmaxyx()
    try:
        scr.addstr(y, max(0, (width - len(text)) // 2), text[:width - 1], attr)
    except curses.error:
        pass


def _banner(scr, lines: list, wait: float):
    """Show a centered message for `wait` seconds (any key skips ahead)."""
    scr.erase()
    height, _ = scr.getmaxyx()
    top = height // 2 - len(lines) // 2
    for k, line in enumerate(lines):
        _center(scr, top + k, line, curses.A_BOLD if k == 0 else 0)
    scr.refresh()
    end = time.time() + wait
    while time.time() < end:
        try:
            scr.getkey()
            break
        except curses.error:
            time.sleep(0.05)


def rain_main(stdscr, pool: list):
    """Curses main loop: nodelay tick loop, one key read per tick. Returns
    (score, level reached)."""
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.leaveok(1)

    _banner(stdscr, ["H A N G U L   R A I N",
                     "",
                     "Type each falling block's sound (가 = ga) before it lands.",
                     "You have %d lives. Esc quits." % STARTING_LIVES], 3.0)

    level = RainLevel(1, pool)
    while True:
        stdscr.erase()
        level.draw(stdscr)
        stdscr.refresh()

        try:
            c = stdscr.getkey()
        except curses.error:
            c = ''

        if c == KEY_ESC:
            break
        # Only single printable letters count as typing; arrow keys and the
        # like arrive as multi-character names and are ignored.
        key = c.lower() if len(c) == 1 and c.isalpha() else None
        level.move(key)

        if level.game_over:
            _banner(stdscr, ["G A M E   O V E R",
                             "",
                             "Score: %d    Level: %d" % (level.points, level.n)], 3.0)
            break
        if level.complete:
            _banner(stdscr, ["Level %d cleared!" % level.n,
                             "",
                             "Score: %d  —  get ready, it speeds up..." % level.points], 2.0)
            level = RainLevel(level.n + 1, pool, level.points, level.lives)
        time.sleep(TICK)

    return level.points, level.n


def launch_rain_mode(quiz):
    """Build the pool from the quiz's current lesson and run Hangul Rain.

    Prints a short summary afterwards, and records a new high score in
    quiz.progress['rain_best'] (the caller saves progress). Returns
    (score, level_reached)."""
    pool = _build_pool(quiz)
    if not pool:
        print("Hangul Rain: no syllables to play for this lesson.")
        return (0, 0)

    curses = _require_curses()
    # curses waits ~1s after Esc to see if it starts an escape sequence;
    # shorten that so Esc quits promptly (must be set before curses starts).
    os.environ.setdefault("ESCDELAY", "25")
    score, level_reached = curses.wrapper(rain_main, pool)
    print("Hangul Rain — final score: {} (reached level {})".format(score, level_reached))
    progress = getattr(quiz, "progress", None)
    if isinstance(progress, dict):
        best = progress.get("rain_best", 0)
        if score > best:
            progress["rain_best"] = score
            if best:
                print("🏆 New high score! (previous best: {})".format(best))
        elif best:
            print("High score: {}".format(best))
    return (score, level_reached)
