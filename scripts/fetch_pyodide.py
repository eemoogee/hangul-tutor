"""Fetch the pinned, local Pyodide 0.26.4 runtime for static hosting."""

from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "pyodide"
BASE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"
FILES = ("pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm",
         "python_stdlib.zip", "pyodide-lock.json")


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        destination = OUT / name
        if destination.exists() and destination.stat().st_size:
            print(f"Present {name}: {destination.stat().st_size:,} bytes")
            continue
        temporary = OUT / (name + ".part")
        print(f"Downloading {name}...", flush=True)
        with urlopen(BASE + name, timeout=120) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if not temporary.stat().st_size:
            raise RuntimeError(f"Empty download: {name}")
        temporary.replace(destination)
        print(f"Saved {name}: {destination.stat().st_size:,} bytes")


if __name__ == "__main__":
    fetch()
