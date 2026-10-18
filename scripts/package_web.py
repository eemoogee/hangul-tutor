"""Build the complete static web folder as a Netlify Drop ZIP."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from build_web import ROOT, build


WEB = ROOT / "web"
PACKAGE = ROOT / "dist" / "hangul-tutor-web.zip"
REQUIRED = (
    "index.html", "app.js", "style.css", "teaching.json",
    "engine/manifest.json", "pyodide/pyodide.js", "pyodide/pyodide.asm.wasm",
)


def package():
    build()
    missing = [name for name in REQUIRED if not (WEB / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Incomplete web package: {', '.join(missing)}")
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(PACKAGE, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(WEB.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(WEB).as_posix())
    with ZipFile(PACKAGE) as archive:
        if "teaching.json" not in archive.namelist():
            raise ValueError("The teaching guide is missing from the deployment package.")
    print(f"Packaged {PACKAGE}")


if __name__ == "__main__":
    package()
