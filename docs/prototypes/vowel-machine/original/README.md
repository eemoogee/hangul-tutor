# Vowel Machine v0.3.1 preview

Unzip the package and open `index.html` in a modern browser. It is designed to work without a network connection; `app.js` and the three Jeong images are included. No account, backend, audio, or saved progress is used. To compare methods, use the two tabs in either order. The original v0.3 ZIP is preserved separately as the prior baseline.

`DESIGN_NOTES.md` explains the educational assumptions and historical boundary. `BEGINNER_TEST.md` gives a short observation protocol. `verify_vowel_machine.py` is the browser regression suite; it requires Python Playwright and its Chromium browser. The package keeps a copy of the v0.2 Explore baseline for reference. The reviewer can inspect `window.__vowelMachine.methodReport('stroke')` and `methodReport('keys')` in browser developer tools before closing the page; the report records which method was tested first and the four vowel recognition targets shown after it.
