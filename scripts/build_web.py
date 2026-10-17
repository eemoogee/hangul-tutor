"""Copy the Python Sejong slice into a static, hash-listed web bundle."""

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "engine"
SOURCES = (
    "hangul_quiz_engine.py",
    "reading_check.py",
    "sejong_flow.py",
    "data/curriculum.json",
    "data/word_contrasts.json",
    "data/konglish_vocab.json",
    "data/reading_practice.jsonl",
    "data/tatoeba_kor_sentences.tsv",
    "data/sejong.json",
)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    files = []
    for name in SOURCES:
        source = ROOT / name
        destination = OUT / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        content = destination.read_bytes()
        files.append({"path": name, "sha256": hashlib.sha256(content).hexdigest(),
                      "bytes": len(content)})
    version = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:16]
    manifest = {"app_version": version, "files": files}
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(files)} files; APP_VERSION={version}")


if __name__ == "__main__":
    build()
