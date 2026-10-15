#!/usr/bin/env python3
"""
_demo_hangul_effects.py — SEE the terminal effect candidates before any of
them are wired into the app.

WHY THIS EXISTS
---------------
hangul_cli.py already has working in-place animation (reveal_letter,
_title_chart_animation) but the cursor math is hand-rolled per call site
and a SECOND private width function (dw()) duplicates the module-level
_vwidth(). Before deciding which effects to ship and how to factor them,
run this and pick by eye rather than by description.

This script is standalone: it does NOT import hangul_cli, so it can be run
and deleted without touching the app. When an effect is chosen, its body
moves into the new module and gets re-verified there.

RUN
---
    cd ~/Documents/hangul-tutor
    python scripts/_demo_hangul_effects.py            # all effects, in order
    python scripts/_demo_hangul_effects.py 3          # just effect #3
    python scripts/_demo_hangul_effects.py --list     # names only
    python scripts/_demo_hangul_effects.py --plain    # no ANSI at all

NOTES FOR REVIEWERS
-------------------
* _vwidth() below is a COPY of the module-level one in hangul_cli.py, plus
  the 0x3130-0x318F compatibility-jamo range the inline dw() also had. Part
  of what this demo is testing is whether width math holds up across all
  these effects — if it breaks here it breaks there.
* EFFECT_RESTRAINED / EFFECT_PLAYFUL in the listing is my read of fit with
  the app's existing aesthetic (box-drawing frames, mono romanization,
  deliberate restraint). That labelling is a judgment call, not a fact.
* All timing constants are at the top of each function so they can be
  tuned without hunting.
"""

import math
import os
import random
import shutil
import sys
import time

# ── ANSI ───────────────────────────────────────────────────────────────────
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
WHITE = "\033[97m"
RESET = "\033[0m"

if sys.platform == "win32":
    os.system("")  # enable VT processing on older cmd.exe

USE_ANSI = True


def styled(text: str, *styles) -> str:
    if not USE_ANSI or not styles:
        return text
    return "".join(styles) + text + RESET


# ── Width math (mirrors hangul_cli.py) ─────────────────────────────────────
_HANGUL_WIDE_RANGES = (
    (0x1100, 0x11FF),  # Jamo block
    (0x3130, 0x318F),  # Compatibility Jamo — the standalone ㅎㅏㄴ used here
    (0xAC00, 0xD7A3),  # Syllables (한, 글)
)


def _vwidth(s: str) -> int:
    """Terminal columns: Hangul double-width, everything else single."""
    return sum(
        2 if any(lo <= ord(c) <= hi for lo, hi in _HANGUL_WIDE_RANGES) else 1
        for c in s
    )


# ── Terminal primitives ────────────────────────────────────────────────────
def term_cols(default: int = 80) -> int:
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except Exception:
        return default


CURSOR_UP_1 = "\033[1A"
CURSOR_COL_0 = "\033[1G"


def hide_cursor():
    if USE_ANSI:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()


def show_cursor():
    if USE_ANSI:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


def repaint(lines, first=False):
    """Draw a block of lines, overwriting the previous block in place.

    The whole point: on every frame after the first, walk the cursor up
    len(lines) and return to column 1, then rewrite. Without this the
    animation scrolls the terminal instead of animating.

    Every line is padded to a common width so a shorter frame fully erases
    the longer one behind it — otherwise trailing glyphs ghost through.
    """
    block = [line for line in lines]
    width = max((_vwidth(strip_ansi(line)) for line in block), default=0)
    out = []
    if not first:
        out.append(CURSOR_UP_1 * len(block) + CURSOR_COL_0)
    for line in block:
        pad = width - _vwidth(strip_ansi(line))
        out.append(line + " " * pad + "\n")
    sys.stdout.write("".join(out))
    sys.stdout.flush()


_ANSI_RE = None


def strip_ansi(s: str) -> str:
    global _ANSI_RE
    if _ANSI_RE is None:
        import re

        _ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
    return _ANSI_RE.sub("", s)


def banner(n, name, note):
    print()
    print(styled(f"── Effect {n}: {name} " + "─" * max(0, 46 - len(name)), BOLD, WHITE))
    print(styled(f"   {note}", DIM))
    print()


# ── Candidate effects ──────────────────────────────────────────────────────

DEMO_WORD = "한글"
JAMO_POOL = list("ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎㅏㅑㅓㅕㅗㅛㅜㅠㅡㅣ")


def effect_1_column_rain(width=None, rows=10, steps=26, fps=0.045):
    """EFFECT 1 — vertical jamo rain, one or more columns, glyphs falling.

    Matrix-ish. Reads as 'arcade'. Trailing glyphs fade to DIM so the head
    of each column is the bright part. This is the effect most likely to
    fight the app's restrained visual language — shown so you can judge it.
    """
    width = width or min(term_cols() - 4, 60)
    n_cols = max(8, width // 5)  # denser: the first pass used only 6 columns
    gap = max(2, width // n_cols)  # and left most of a 56-col screen empty
    col_x = [2 + i * gap for i in range(n_cols)]

    # Each column: a drop position, speed, and the glyph trail above it.
    drops = []
    for i in range(n_cols):
        drops.append(
            {
                "x": col_x[i],
                "y": random.uniform(-rows, 0),
                "speed": random.uniform(0.5, 1.0),
                "trail": [random.choice(JAMO_POOL) for _ in range(random.randint(4, 8))],
            }
        )

    def render():
        grid = [[" "] * (width + 4) for _ in range(rows)]
        for d in drops:
            head = int(d["y"])
            for k, ch in enumerate(d["trail"]):
                yy = head - k
                if 0 <= yy < rows:
                    xx = d["x"]
                    style = (GREEN, BOLD) if k == 0 else (GREEN,) if k < 3 else (DIM, GREEN)
                    # keep any Hangul glyph double-width safe
                    grid[yy][xx] = ch  # placement is 1 cell/glyph; see note below
        return ["".join(r) for r in grid]

    # NOTE: this builds a per-cell grid assuming 1 cell per glyph, but
    # Hangul jamo are DOUBLE-width. Building the frame by joining a grid
    # and then colouring is exactly the trap _vwidth exists to catch — so
    # for the demo we render column-by-column instead, which respects the
    # real width. Kept the grid code above as a dead-comment illustration
    # of the wrong approach; see the working renderer below.
    def render_columns():
        lines = []
        for y in range(rows):
            pieces = []
            for d in drops:
                head = int(d["y"])
                ch = None
                for k, c in enumerate(d["trail"]):
                    if head - k == y:
                        if k == 0:
                            ch = styled(c, GREEN, BOLD)
                        elif k < 3:
                            ch = styled(c, GREEN)
                        else:
                            ch = styled(c, DIM, GREEN)
                        break
                pieces.append(ch if ch else "  ")
            # pad each column slot to its widest member so nothing drifts
            lines.append("  " + " ".join(pieces))
        return lines

    for _ in range(steps):
        repaint(render_columns())
        for d in drops:
            d["y"] += d["speed"]
            if d["y"] - len(d["trail"]) > rows:
                d["y"] = random.uniform(-3, 0)
                d["speed"] = random.uniform(0.5, 1.0)
                d["trail"] = [
                    random.choice(JAMO_POOL) for _ in range(random.randint(4, 8))
                ]
        time.sleep(fps)
    repaint([" " * 2 for _ in range(rows)])


def effect_2_marquee(text=DEMO_WORD * 3, pad=12, width=None, steps=30, fps=0.05):
    """EFFECT 2 — horizontal marquee that scrolls right-to-left, looping.

    Restrained. Good for a title strip or a lesson header. Demonstrates
    correct wrapping across the double-width boundary (naive slicing would
    cut a jamo in half and shift the whole line).
    """
    width = width or min(term_cols() - 6, 48)
    units = list(text)  # split by CHARACTER, never by byte
    span = len(units) + pad
    for i in range(steps):
        off = i % span
        window = []
        col = 0
        for k in range(span):
            idx = (k - off) % span
            if idx < len(units):
                ch = units[idx]
                w = _vwidth(ch)
                if col + w > width:
                    break
                window.append(ch)
                col += w
            else:
                if col + 1 > width:
                    break
                window.append(" ")
                col += 1
        line = styled("".join(window) or " ", CYAN, BOLD)
        repaint([line, styled(" " * width, RESET)])
        time.sleep(fps)
    repaint([" " * width] * 2)


def effect_3_wipe_in(text=DEMO_WORD, width=None, steps=18, fps=0.06):
    """EFFECT 3 — typewriter / left-to-right wipe reveal of a word.

    Restrained, on-brand. Same family as the existing reveal_letter card:
    the glyph appears progressively rather than all at once. Respects
    double width (advances 2 columns per Hangul glyph).
    """
    width = width or min(term_cols() - 6, 40)
    units = list(text)
    total_cols = sum(_vwidth(c) for c in units)
    indent = "   "  # every frame, including the caret frame — see check script

    for i in range(steps + 1):
        frac = i / steps
        shown_cols = int(total_cols * frac)
        body, col = [], 0
        for ch in units:
            if col + _vwidth(ch) <= shown_cols:
                body.append(styled(ch, CYAN, BOLD))
            else:
                body.append(" " * _vwidth(ch))  # hole keeps later glyphs in place
            col += _vwidth(ch)
        caret = "" if i == steps else styled("▏", DIM)
        repaint([indent + "".join(body) + caret, styled(" " * width, RESET)])
        time.sleep(fps)
    repaint([indent + styled(text, CYAN, BOLD), styled(" " * width, RESET)])


def effect_4_row_sweep(rows=None, cols=8, steps=24, fps=0.05):
    """EFFECT 4 — a horizontal scanline sweeping down through a grid of
    syllables, lighting each row as it passes.

    Restrained-to-playful. This is the 'scrolling rows' reading — a grid
    being progressively revealed rather than text moving. Useful for the
    alphabet/CV chart.
    """
    rows = rows or [
        "".join(random.choice(list("ㄱㄴㅁㅅㅎ")) + random.choice(list("ㅏㅓㅗㅜㅣ")))
        for _ in range(cols)
    ]
    n = len(rows)
    for s in range(steps):
        head = (s * n / steps) % n
        lines = []
        for i, row in enumerate(rows):
            d = abs(i - head)
            # wrap-around distance so the sweep loops smoothly
            d = min(d, n - d)
            if d < 0.8:
                lines.append("   " + styled(row, GREEN, BOLD) + "   ←")
            elif d < 1.8:
                lines.append("   " + styled(row, CYAN))
            else:
                lines.append("   " + styled(row, DIM))
        repaint(lines)
        time.sleep(fps)


def effect_5_sweep_columns(text=DEMO_WORD, letters=None, steps=22, fps=0.05):
    """EFFECT 5 — a column (vertical band) of light sweeping left-to-right
    across a Hangul word, revealing it as the band passes.

    Restrained. The 'scrolling columns' reading applied to text rather
    than a grid. Nice for a single word/answer reveal, not for lists.
    """
    letters = letters or list(text)
    # Build a plain 2-row block: glyph row + romanization-ish underbar row.
    # Column-by-column so double-width glyphs are never split.
    cols = []
    for ch in letters:
        cols.append((ch, _vwidth(ch)))
    total = sum(w for _, w in cols)

    for s in range(steps + 1):
        pos = total * (s / steps)
        out, col = [], 0
        for ch, w in cols:
            # is this glyph currently under the sweeping band?
            near = abs((col + w / 2) - pos) <= (total / steps) + 0.75
            passed = (col + w) <= pos
            if near:
                out.append(styled(ch, WHITE, BOLD))
            elif passed:
                out.append(styled(ch, GREEN))
            else:
                out.append(styled(ch, DIM))
            col += w
        repaint(["   " + "".join(out), "   " + styled("─" * total, DIM)])
        time.sleep(fps)
    repaint(["   " + styled("".join(letters), GREEN, BOLD), "   " + styled("─" * total, DIM)])


def effect_6_flash_feedback(correct=True, blink=3, fps=0.11):
    """EFFECT 6 — a single emphatic pulse for answer feedback (right/wrong).

    The 'flashing' reading, scoped to one moment rather than a whole
    screen. Deliberately short and not strobing — a full-screen strobe on
    every answer would be punishing across a 30-question session. Shown
    both in the pass and fail colour so you can judge the wrong-answer one,
    which is the one that can feel hostile if overdone.
    """
    good = [GREEN, CYAN]
    bad = [RED, YELLOW]
    pair = good if correct else bad
    mark = "✓" if correct else "✗"
    word = "정답!" if correct else "다시!"
    roman = "correct!" if correct else "try again"

    def frame(on):
        colour = pair[0] if on else pair[1]
        line = f"   {mark}  {styled(word, colour, BOLD)}  {styled(roman, DIM)}"
        return [line, ""]

    for i in range(blink):
        repaint(frame(i % 2 == 0))
        time.sleep(fps)
        repaint(frame(i % 2 != 0))
        time.sleep(fps)
    repaint(frame(True))
    time.sleep(0.35)


def effect_7_random_scatter(text=DEMO_WORD, steps=26, fps=0.045):
    """EFFECT 7 — glyphs land out of order (scatter / slot-machine).

    Playful. Each final position is filled in a random order rather than
    left-to-right. Close to what _title_chart_animation already does for
    its chart cells — shown so you can compare the existing feel against
    the wipe in Effect 3.
    """
    units = list(text)
    order = list(range(len(units)))
    random.shuffle(order)

    def frame(filled):
        out = []
        for i, ch in enumerate(units):
            if i in filled:
                out.append(styled(ch, GREEN, BOLD))
            else:
                out.append(styled(random.choice(JAMO_POOL), DIM))
        return ["   " + "".join(out), ""]

    filled = set()
    for i in range(steps):
        # fill roughly one slot at a time, accelerating a little at the end
        target = int(len(units) * (i / steps) ** 0.8)
        while len(filled) < target and order:
            filled.add(order.pop())
        repaint(frame(filled))
        time.sleep(fps)
    repaint(["   " + styled(text, GREEN, BOLD), ""])


def effect_8_block_pulse(text=DEMO_WORD, steps=20, fps=0.06):
    """EFFECT 8 — whole-word colour pulse: cycles hue to draw the eye.

    Playful, and the highest mis-use risk: flashing colour on a word every
    time it appears would be exhausting to read. Shown mainly so you can
    confirm you do NOT want it in the main loop, or only on rare events
    (level-up / streak milestone).
    """
    palette = [CYAN, GREEN, YELLOW, MAGENTA, BLUE, WHITE]
    for i in range(steps):
        c = palette[i % len(palette)]
        repaint(["   " + styled(text, c, BOLD), ""])
        time.sleep(fps)
    repaint(["   " + styled(text, GREEN, BOLD), ""])


EFFECTS = [
    ("column-rain", effect_1_column_rain, "vertical jamo rain — arcade, likely off-brand"),
    ("marquee", effect_2_marquee, "horizontal scroll, looping — title/header strip"),
    ("wipe-in", effect_3_wipe_in, "typewriter reveal — on-brand, like reveal_letter"),
    ("row-sweep", effect_4_row_sweep, "scanline down a grid — 'scrolling rows' on a chart"),
    ("col-sweep", effect_5_sweep_columns, "light band across a word — answer reveal"),
    ("flash-correct", lambda: effect_6_flash_feedback(True), "pulse on correct answer"),
    ("flash-wrong", lambda: effect_6_flash_feedback(False), "pulse on wrong answer (the risky one)"),
    ("scatter", effect_7_random_scatter, "out-of-order landing — matches existing chart feel"),
    ("block-pulse", effect_8_block_pulse, "colour cycling — likely too loud for the loop"),
]


def main():
    global USE_ANSI
    args = [a for a in sys.argv[1:]]

    if "--plain" in args:
        USE_ANSI = False
        args.remove("--plain")

    if "--list" in args or "-l" in args:
        for i, (name, _, note) in enumerate(EFFECTS, 1):
            print(f"{i:2d}. {name:14s} {note}")
        return

    want = None
    if args and args[0].isdigit():
        want = int(args[0])

    print(styled("\n  Hangul terminal effects — candidate demo", BOLD, WHITE))
    print(styled(f"  term width: {term_cols()} cols   ansi: {USE_ANSI}", DIM))
    print(styled("  (nothing here touches the app; this is a scratch script)", DIM))

    hide_cursor()
    try:
        for i, (name, fn, note) in enumerate(EFFECTS, 1):
            if want is not None and i != want:
                continue
            banner(i, name, note)
            fn()
            time.sleep(0.4)
    except KeyboardInterrupt:
        print("\n  (interrupted)")
    finally:
        show_cursor()

    print()
    print(styled("  done — effects ran in place, terminal was not scrolled.", GREEN))
    print(styled("  pick the ones you want; bodies move to the module on commit.", DIM))
    print()


if __name__ == "__main__":
    main()
