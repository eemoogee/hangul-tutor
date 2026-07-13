# run_tutor.ps1 — Launch Hangul Tutor with a curated multi-model setup.
#
# Rationale (see `ollama list` for what's available locally):
#   - Base default: qwen2.5:1.5b — fast and reliable, used for anything not
#     explicitly overridden below (e.g. encouragement messages, which are
#     low-stakes and don't need a bigger model).
#   - Mnemonic + sentence generation: bllossom:8b — a Korean/English-tuned
#     model, a better fit than a general-purpose model for tasks that need
#     real Korean fluency (shape-based mnemonics, constrained sentences).
#   - Translation: translategemma:latest — purpose-built for translation
#     rather than general chat, used only for the /talk translation step.
#
# Avoided: qwen3:8b / qwen3.5:9b (non-nothink variants). These default to an
# internal "thinking" mode that generates hidden reasoning tokens before the
# actual answer, which was blowing past the 60s Ollama timeout even for a
# one-line mnemonic. If you want to experiment with Qwen3-level quality
# without that slowdown, try qwen3.5:9b-nothink instead.
#
# Usage: .\run_tutor.ps1 [any extra args, e.g. --lesson 3]

$env:HANGUL_MODEL_MNEMONIC = "bllossom:8b"
$env:HANGUL_MODEL_SENTENCE = "bllossom:8b"
$env:HANGUL_MODEL_TRANSLATE = "translategemma:latest"

python hangul_cli.py --model qwen2.5:1.5b @args
