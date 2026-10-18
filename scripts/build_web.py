"""Copy both Python lesson flows into a static, hash-listed web bundle."""

import ast
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "engine"
SEJONG_SOURCES = (
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
SOURCES = SEJONG_SOURCES + ("lesson_flow.py", "curriculum_flow.py")


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
    def version(entries):
        return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()[:16]

    manifest = {"app_version": version(files),
                "sejong_version": version(files[:len(SEJONG_SOURCES)]),
                "files": files}
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Reuse the terminal's authored teaching text without importing its CLI.
    tree = ast.parse((ROOT / "hangul_cli.py").read_text(encoding="utf-8"))
    names = {"ALPHABET_MNEMONICS": "mnemonics", "POSITIONAL_QUIRKS": "quirks"}
    teaching = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    teaching[names[target.id]] = ast.literal_eval(node.value)
    if set(teaching) != set(names.values()):
        raise ValueError("Terminal letter teaching data is missing")
    (ROOT / "web" / "teaching.json").write_text(
        json.dumps(teaching, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(files)} files; APP_VERSION={manifest['app_version']}")


if __name__ == "__main__":
    build()
