"""
term_wrap.py — word-wrap everything the tutor prints to the terminal's width.

The app's text was written for a wide desktop terminal. On a phone (Termux is
~45-50 columns) long lines were hard-wrapped by the terminal mid-word ("one
com / pact square") and the continuation started at column 0, losing its
indent. WrappingStdout sits in front of sys.stdout and breaks lines at spaces
instead, continuing them under their own indent — or, for a line that starts
with a bullet emoji like 💡 or ✅, under the text after it.

Lines that already fit are passed through untouched, and any write that moves
the cursor (the title-screen and letter-reveal animations) goes straight
through, so the animations keep working.

Usage (hangul_cli.main does this):
    import term_wrap
    term_wrap.install()          # only wraps when stdout is a real terminal

Set HANGUL_WRAP=<columns> to force a width (handy for testing what the app
looks like on a phone from a wide terminal), or HANGUL_WRAP=0 to turn it off.
"""

import os
import re
import shutil
import sys
import unicodedata

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
# Escape sequences that move the cursor or clear the screen — anything other
# than a colour/style change (which ends in 'm').
_CURSOR_MOVE = re.compile(r"\x1b\[[0-9;?]*[A-HJKSTfsu]")
_TOKEN = re.compile(r"\n|\r| +|[^ \n\r]+")


def display_width(s: str) -> int:
    """Terminal columns `s` occupies: colour codes take none, Hangul and
    emoji take two, combining marks and emoji modifiers take none."""
    s = _ANSI.sub("", s)
    w = 0
    for ch in s:
        if ch in "‍️︎" or unicodedata.combining(ch):
            continue
        w += 2 if unicodedata.east_asian_width(ch) in "WF" else 1
    return w


def _is_bullet(word: str) -> bool:
    """A leading 💡 / ✅ / ❌ / 🎯 / • style marker: a short run of
    non-letter, non-Hangul symbols."""
    plain = _ANSI.sub("", word)
    return (0 < len(plain) <= 3 and display_width(plain) <= 3
            and not any(c.isalnum() for c in plain))


class WrappingStdout:
    def __init__(self, stream, width=None):
        self._stream = stream
        self._fixed_width = width
        self._col = 0
        self._line_start = True
        self._indent = ""
        self._hang = ""
        self._pending_space = ""
        self._first_word = True

    # -- plumbing ----------------------------------------------------------
    def __getattr__(self, name):           # encoding, fileno, isatty, buffer...
        return getattr(self._stream, name)

    def flush(self):
        if self._pending_space:
            self._stream.write(self._pending_space)
            self._col += len(self._pending_space)
            self._pending_space = ""
        self._stream.flush()

    def _width(self) -> int:
        if self._fixed_width:
            return self._fixed_width
        return shutil.get_terminal_size((80, 24)).columns

    def _newline_state(self):
        self._col = 0
        self._line_start = True
        self._indent = ""
        self._hang = ""
        self._pending_space = ""
        self._first_word = True

    # -- the wrapping ------------------------------------------------------
    def write(self, s: str):
        if not s:
            return 0
        if _CURSOR_MOVE.search(s):
            # Animation frame: never touch it. Assume it leaves the cursor at
            # the start of a line (every animation in the app does).
            if self._pending_space:
                self._stream.write(self._pending_space)
            self._stream.write(s)
            self._newline_state()
            return len(s)
        limit = max(20, self._width() - 1)
        out = []
        for tok in _TOKEN.findall(s):
            if tok in ("\n", "\r"):
                out.append(tok)
                self._newline_state()
            elif tok[0] == " ":
                if self._line_start:
                    self._indent += tok
                    out.append(tok)
                    self._col += len(tok)
                else:
                    self._pending_space += tok
            else:
                w = display_width(tok)
                if self._line_start:
                    self._line_start = False
                    self._hang = self._indent or "  "
                    if _is_bullet(tok):
                        self._hang = self._indent + " " * (w + 1)
                    out.append(tok)
                    self._col += w
                    continue
                gap = len(self._pending_space)
                if w and self._col + gap + w > limit and self._col > len(self._hang):
                    out.append("\n" + self._hang)
                    self._col = display_width(self._hang)
                else:
                    out.append(self._pending_space)
                    self._col += gap
                self._pending_space = ""
                out.append(tok)
                self._col += w
        self._stream.write("".join(out))
        return len(s)


def install():
    """Wrap sys.stdout if it's a real terminal (or HANGUL_WRAP forces a
    width). Safe to call more than once."""
    if isinstance(sys.stdout, WrappingStdout):
        return
    forced = os.environ.get("HANGUL_WRAP", "").strip()
    if forced == "0":
        return
    if forced.isdigit():
        sys.stdout = WrappingStdout(sys.stdout, width=int(forced))
    elif sys.stdout.isatty():
        sys.stdout = WrappingStdout(sys.stdout)
