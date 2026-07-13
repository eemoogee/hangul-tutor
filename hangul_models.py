"""
hangul_models.py — Per-task local LLM model configuration.

Every creative task (mnemonics, encouragement, sentence generation,
translation) can run on its own Ollama model. The idea: start everything on
one small/fast model, then selectively upgrade just the tasks that actually
benefit from a bigger one, without touching the rest.

Resolution order for a given task, e.g. "mnemonic":
  1. HANGUL_MODEL_MNEMONIC   env var — task-specific override
  2. --model flag            runtime default, set via set_default_model()
  3. HANGUL_OLLAMA_MODEL     env var — shared fallback
  4. DEFAULT_MODEL           hardcoded small default

Tasks:
  mnemonic       Letter mnemonics (hangul_cli.py generate_mnemonic)
  encouragement  Streak/accuracy encouragement messages
  sentence       Constrained Korean sentence generation (mini-sentences, /talk)
  translate      English translation of a fixed (Tatoeba) Korean sentence

Usage:
    from hangul_models import get_model, set_default_model, summarize_models

    model = get_model("mnemonic")
    set_default_model(args.model)  # from --model, only if the user passed it
"""

import os

# Small, fast starting point — swap individual tasks up via HANGUL_MODEL_*
# env vars once you know which ones actually need more horsepower.
DEFAULT_MODEL = "qwen2.5:1.5b"

TASKS = ("mnemonic", "encouragement", "sentence", "translate")

# Set at runtime by hangul_cli.py's --model flag. Only applies to tasks that
# don't have their own HANGUL_MODEL_* override.
_runtime_default = None


def set_default_model(model: str) -> None:
    """Override the shared fallback model at runtime (used by --model)."""
    global _runtime_default
    _runtime_default = model


def get_model(task: str) -> str:
    """Resolve which model to use for a given task."""
    if task not in TASKS:
        raise ValueError(f"Unknown model task: {task!r} (expected one of {TASKS})")

    task_override = os.environ.get(f"HANGUL_MODEL_{task.upper()}")
    if task_override:
        return task_override

    if _runtime_default:
        return _runtime_default

    return os.environ.get("HANGUL_OLLAMA_MODEL", DEFAULT_MODEL)


def all_models() -> dict:
    """Resolved model for every task — handy for a status display."""
    return {task: get_model(task) for task in TASKS}


def base_model() -> str:
    """The shared fallback model, ignoring task-specific overrides."""
    return _runtime_default or os.environ.get("HANGUL_OLLAMA_MODEL", DEFAULT_MODEL)


def summarize_models() -> str:
    """Human-readable summary for a session banner: the shared base model,
    plus any tasks that have been overridden to something different."""
    base = base_model()
    overrides = {task: m for task, m in all_models().items() if m != base}
    if not overrides:
        return base
    override_str = ", ".join(f"{task}→{m}" for task, m in overrides.items())
    return f"{base} ({override_str})"
