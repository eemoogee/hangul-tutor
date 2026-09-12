#!/usr/bin/env python3
"""
Train a QLoRA adapter on the Hangul dataset (437 Q&A pairs) and export a GGUF
model for local inference. Kaggle/Linux adaptation of train_hangul_finetune.py
— same dataset and training recipe, re-targeted at Qwen3-8B on a
Kaggle T4 x2 (16 GB) GPU.

Loss masking: completion-only. We fine-tune only on the assistant's answer
tokens (not the user's question), via Unsloth/TRL's native
`completion_only_loss=True` with a prompt/completion dataset split.

SETUP (Kaggle GPU notebook — Linux)
-----------------------------------
Kaggle preinstalls a CUDA-enabled torch. Add Unsloth + the pinned TRL stack on
top of it. On Linux, Unsloth pulls a compatible triton/xformers/torchao
automatically — the Windows-only `triton-windows==3.2.0.post21` pin from the
local setup is NOT needed here:

    !pip install unsloth
    !pip install trl==0.24.0 peft==0.19.1 bitsandbytes==0.49.2 transformers==5.5.0

If transformers 5.5.0 misbehaves, fall back to 4.51.3 (Unsloth's floor).

Target hardware: NVIDIA T4 (16 GB VRAM, Turing). Training runs in fp16 — T4 has
no bf16 tensor cores, so dtype is pinned to float16. A single T4 fits the 7B
QLoRA (~8 GB). This script is single-GPU; to pin it to a specific GPU, set
CUDA_VISIBLE_DEVICES before running.

Usage:
    python train_hangul_kaggle.py                 # full training run
    python train_hangul_kaggle.py --dry-run       # load model + dataset, print
                                                  #   one tokenized sample, exit
    python train_hangul_kaggle.py --dataset /path/to/data.jsonl   # custom data
    python train_hangul_kaggle.py --skip-vram-check              # skip VRAM gate

NOTE (batchim): v6 achieved native (no-RAG) recall of both "batchim" and
"받침" via a WeightedRandomSampler at 2.0x plus 받침 question variants, but the
2.0x sampler also degraded non-batchim recall (letter facts became unstable,
and batchim language contaminated the ㅇ / session-summary facts). v7 drops the
sampler and keeps only the 받침 variants — the native-script trigger without
over-weighting batchim. Raw-model sweep for a 7B base: qwen2.5:7b hallucinated
"batchim" (knows 받침, not the romanization) and bllossom:8b conflated 받침 with
case endings; qwen3:8b answered both "batchim" and "받침" (plus ㅏ) correctly, so
it is the base model here. RAG injection (rag_facts.py) remains available and
correct as an independent path.
"""

from unsloth import FastLanguageModel  # MUST be imported first — patches transformers/peft at import time

import argparse
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import torch
from datasets import Dataset
from trl import SFTConfig, SFTTrainer

# ---------------------------------------------------------------------------
# Paths / model
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

# Unsloth's pre-quantized mirror is "unsloth/Qwen3-8B-unsloth-bnb-4bit" (nf4) but
# bakes bnb_4bit_compute_dtype=bfloat16 — wrong for T4 (fp16-only), so use the
# plain repo (load_in_4bit=True quantizes on load with fp16 compute).
MODEL_NAME = "Qwen/Qwen3-8B"

GGUF_QUANTIZATION_METHOD = "q4_k_m"

DEFAULT_DATASET = BASE_DIR / "hangul_finetune_v12.jsonl"
CHECKPOINT_DIR = BASE_DIR / "outputs"                 # trainer logs + adapter checkpoints
GGUF_OUTPUT_DIR = BASE_DIR / "hangul_expert_model"    # final GGUF lands here (counts toward
                                                       # Kaggle's committed-output quota, ~20GB,
                                                       # which is separate from -- and smaller
                                                       # than -- the container's real disk)
GGUF_SCRATCH_DIR = Path(tempfile.gettempdir()) / "hangul_expert_model_scratch"
    # save_pretrained_gguf's intermediates (16-bit merge + f16 GGUF + quantized GGUF, all
    # on disk at once) can need 30GB+. Building them under BASE_DIR (/kaggle/working) hits
    # Kaggle's output quota even when the container's actual disk has room. Building them
    # in the OS temp dir instead avoids that quota; only the small final .gguf gets copied
    # into GGUF_OUTPUT_DIR afterward, which is the one thing that needs to survive as output.
# Confirmed on the 2026-09-02 Kaggle run: save_pretrained_gguf(save_directory=X, ...) does
# NOT write GGUF files into X -- it writes the merged safetensors into X, then writes the
# actual .gguf files into a SIBLING directory named f"{X}_gguf". Undocumented, so search
# both locations for the final file rather than assuming either one alone.
GGUF_SCRATCH_GGUF_DIR = GGUF_SCRATCH_DIR.parent / f"{GGUF_SCRATCH_DIR.name}_gguf"

# ---------------------------------------------------------------------------
# LoRA config
# ---------------------------------------------------------------------------
LORA_R = 32
LORA_ALPHA = 64
LORA_DROPOUT = 0.05
TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]

# ---------------------------------------------------------------------------
# Training config
# ---------------------------------------------------------------------------
MAX_SEQ_LENGTH = 512              # our Q&A pairs are short
PER_DEVICE_BATCH_SIZE = 2
GRADIENT_ACCUMULATION_STEPS = 4   # effective batch size = 2 * 4 = 8
NUM_EPOCHS = 2  # B5 epoch experiment closed (3-epoch = 2-epoch, flat); back to 2-epoch baseline for rank experiment
LEARNING_RATE = 1e-4
WARMUP_STEPS = 11  # ceil(0.1 * ceil(437/8) * 2) = ceil(0.1 * 55 * 2) = 11
LR_SCHEDULER_TYPE = "cosine"
SEED = 42

# Free VRAM required on a single GPU for the 7B QLoRA run: 4-bit base ~4.4 GB
# + LoRA + 8-bit Adam + activations at batch 8 x seq 512 (with gradient
# checkpointing) ~= 8 GB total. Abort unless some GPU has this much free.
REQUIRED_VRAM_MIB = 8192


# 1. Environment check -------------------------------------------------------
def check_environment() -> None:
    """Verify CUDA and report every GPU before doing anything else."""
    if not torch.cuda.is_available():
        print(
            "ERROR: CUDA is not available. This script needs an NVIDIA GPU.\n"
            '  - Diagnose with:  python -c "import torch; print(torch.cuda.is_available())"',
            file=sys.stderr,
        )
        sys.exit(1)

    n = torch.cuda.device_count()
    print(f"[env] {n} CUDA device(s):")
    for i in range(n):
        props = torch.cuda.get_device_properties(i)
        vram_gb = props.total_memory / (1024 ** 3)
        print(f"  GPU {i}: {props.name} ({vram_gb:.1f} GB VRAM)")
    print(f"[env] torch {torch.__version__}  CUDA {torch.version.cuda}")


def check_vram_headroom() -> None:
    """Abort unless some single GPU has enough free VRAM for the 7B QLoRA run.

    Reads free memory across ALL GPUs (nvidia-smi emits one line per GPU) and
    requires at least REQUIRED_VRAM_MIB free on the most-free GPU — the one the
    single-GPU trainer will land on. Override with --skip-vram-check.
    """
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total,memory.used",
             "--format=csv,noheader,nounits"],
            text=True, timeout=10,
        )
    except Exception as e:
        print(f"[vram] nvidia-smi unavailable ({e}); skipping pre-flight check")
        return

    gpus = []
    for line in out.strip().splitlines():
        total, used = (int(x.strip()) for x in line.split(","))
        gpus.append((total, used))

    best_free = max((t - u) for t, u in gpus)
    print(f"[vram] {len(gpus)} GPU(s); most-free GPU has {best_free} MiB free")

    if best_free < REQUIRED_VRAM_MIB:
        print(
            f"[vram] ABORT: only {best_free} MiB free, but the 7B QLoRA needs "
            f">= {REQUIRED_VRAM_MIB} MiB on one GPU.\n"
            "  Free GPU memory (stop other kernels/notebooks) or pass "
            "--skip-vram-check to override."
        )
        sys.exit(1)

    print("[vram] OK: enough free VRAM on a single GPU")


# 2. Dataset loading ----------------------------------------------------------
def load_dataset(path: Path) -> Dataset:
    """Read the JSONL and return a Dataset with an un-tokenized `messages` column."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))  # {"messages": [...]}

    print(f"[data] loaded {len(records)} examples from {path.name}")
    return Dataset.from_list(records)


def transform_to_prompt_completion(dataset: Dataset) -> Dataset:
    """Split each `messages` record into `prompt` + `completion` columns for
    Unsloth's native `completion_only_loss` path.

    `prompt` holds the user turns (this dataset has no system message — everything
    before the answer);
    `completion` holds the assistant turns. The trainer masks every prompt
    token, so we train only on the assistant's answer.
    """
    def split(example: dict) -> dict:
        messages = example["messages"]
        return {
            "prompt": [m for m in messages if m["role"] != "assistant"],
            "completion": [m for m in messages if m["role"] == "assistant"],
        }

    dataset = dataset.map(split, remove_columns=["messages"])
    print(f"[data] split into prompt/completion columns ({len(dataset)} examples)")
    return dataset


# Dry-run helper ---------------------------------------------------------------
def print_prompt_completion_sample(tokenizer, example: dict) -> None:
    """Print one example's rendered prompt + completion (for --dry-run)."""
    prompt = example["prompt"]
    completion = example["completion"]

    rendered_prompt = tokenizer.apply_chat_template(
        prompt, tokenize=False, add_generation_prompt=True
    )
    prompt_ids = tokenizer.apply_chat_template(
        prompt, tokenize=True, return_dict=True, add_generation_prompt=True
    )["input_ids"]
    full_ids = tokenizer.apply_chat_template(
        prompt + completion, tokenize=True, return_dict=True, add_generation_prompt=False
    )["input_ids"]
    n_prompt = min(len(prompt_ids), len(full_ids))
    n_completion = len(full_ids) - n_prompt

    print("\n[dry-run] prompt messages:")
    for m in prompt:
        print(f"    {m['role']}: {m['content']!r}")
    print("\n[dry-run] completion messages:")
    for m in completion:
        print(f"    {m['role']}: {m['content']!r}")
    print("\n[dry-run] rendered prompt (add_generation_prompt=True):")
    print(rendered_prompt)
    print(f"\n[dry-run] token counts — prompt: {n_prompt}, completion: {n_completion}, "
          f"total: {len(full_ids)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune a Hangul expert model with QLoRA.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Path to the JSONL training dataset (default: {DEFAULT_DATASET.name}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load the model and dataset, print one tokenized sample, then exit without training.",
    )
    parser.add_argument(
        "--skip-vram-check",
        action="store_true",
        help="Skip the GPU VRAM headroom pre-flight check.",
    )
    parser.add_argument(
        "--hf-repo",
        type=str,
        default=None,
        dest="hf_repo",
        help=(
            "HuggingFace repo the GGUF was pushed to after this run "
            "(e.g. eemoogee/hangul-expert-qwen3-8b). Recorded in the run manifest; "
            "does NOT trigger a push — that step is still manual."
        ),
    )
    parser.add_argument(
        "--notes",
        type=str,
        default=None,
        help="Free-text annotation for this run (e.g. 'B5 epoch=3 test'). Stored in run manifest.",
    )
    return parser.parse_args()


# 8. Run manifest -------------------------------------------------------------
def log_run_manifest(
    args: argparse.Namespace,
    dataset_pairs: int,
    copied_ggufs: list,
) -> None:
    """Append one JSON record to run_manifest.jsonl in the repo root.

    Captures the full hyperparameter set, dataset version, git commit hash, and
    GGUF output details so runs are comparable without reconstructing config from
    memory or screenshots. Called only after a successful train+export.

    Args:
        args:           parsed CLI args (carries dataset path, hf_repo, notes).
        dataset_pairs:  number of training pairs actually loaded.
        copied_ggufs:   list of Path objects for the .gguf files written to
                        GGUF_OUTPUT_DIR (post-copy, pre-scratch-cleanup).
    """
    def _git_commit() -> str:
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=BASE_DIR, text=True, timeout=5, stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            return "unknown"

    record = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "git_commit": _git_commit(),
        "dataset": {
            "file": args.dataset.name,
            "pairs": dataset_pairs,
        },
        "model": MODEL_NAME,
        "lora": {
            "r": LORA_R,
            "alpha": LORA_ALPHA,
            "dropout": LORA_DROPOUT,
            "target_modules": TARGET_MODULES,
        },
        "training": {
            "epochs": NUM_EPOCHS,
            "lr": LEARNING_RATE,
            "warmup_steps": WARMUP_STEPS,
            "lr_scheduler": LR_SCHEDULER_TYPE,
            "batch_size_per_device": PER_DEVICE_BATCH_SIZE,
            "gradient_accumulation_steps": GRADIENT_ACCUMULATION_STEPS,
            "effective_batch_size": PER_DEVICE_BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS,
            "max_seq_length": MAX_SEQ_LENGTH,
            "seed": SEED,
        },
        "export": {
            "quantization": GGUF_QUANTIZATION_METHOD,
            "gguf_files": [
                {"name": f.name, "size_mb": round(f.stat().st_size / 1e6, 1)}
                for f in copied_ggufs
            ],
        },
        "hf_repo": args.hf_repo,
        "notes": args.notes,
    }

    manifest_path = GGUF_OUTPUT_DIR / "run_manifest.jsonl"
    with open(manifest_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"[manifest] appended run record to {manifest_path.name}")
    print(f"[manifest] git_commit={record['git_commit'][:12]}  "
          f"dataset={record['dataset']['file']} ({dataset_pairs} pairs)  "
          f"epochs={NUM_EPOCHS}  r={LORA_R}  lr={LEARNING_RATE}")


def main() -> None:
    args = parse_args()
    check_environment()
    if not args.skip_vram_check:
        check_vram_headroom()

    # 2. Load the 4-bit base model + tokenizer via Unsloth -------------------
    #    load_in_4bit=True keeps the base weights in 4-bit NF4 (QLoRA). dtype
    #    controls the LoRA/compute precision -> float16 (T4 has no bf16).
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=torch.float16,
        load_in_4bit=True,
    )

    # Qwen3 defaults to chain-of-thought ("thinking") output. Setting
    # enable_thinking=false only changes the GENERATION PROMPT; the assistant-turn
    # branch still renders <think>\n\n</think>\n\n before the answer (its
    # `loop.last` clause is unconditional), so training completions still carry
    # think tokens and the model never unlearns CoT — producing an infinite
    # <think> loop at inference (~23% hang rate observed). Fix: replace the
    # template with a PLAIN ChatML template that renders ZERO think tokens in both
    # prompt and completion, so the model learns to answer directly and the
    # completion_only_loss boundary is clean. This must match the serving
    # Modelfile (plain, no think block).
    tokenizer.chat_template = (
        "{%- for message in messages %}"
        "{{- '<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>\n' }}"
        "{%- endfor %}"
        "{%- if add_generation_prompt %}{{- '<|im_start|>assistant\n' }}{%- endif %}"
    )

    # 3. Attach LoRA adapters ------------------------------------------------
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=TARGET_MODULES,
        bias="none",
        use_gradient_checkpointing="unsloth",  # trades compute for VRAM
        random_state=SEED,
    )

    # 4. Load the dataset and split into prompt/completion columns ------------
    dataset = load_dataset(args.dataset)
    dataset_pairs = len(dataset)  # capture before transform (row count is unchanged by it)
    dataset = transform_to_prompt_completion(dataset)

    if args.dry_run:
        print_prompt_completion_sample(tokenizer, dataset[0])

    # 5. Trainer -------------------------------------------------------------
    training_args = SFTConfig(
        output_dir=str(CHECKPOINT_DIR),
        per_device_train_batch_size=PER_DEVICE_BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        num_train_epochs=NUM_EPOCHS,
        learning_rate=LEARNING_RATE,
        warmup_steps=WARMUP_STEPS,
        lr_scheduler_type=LR_SCHEDULER_TYPE,
        fp16=True,                    # NOT bf16 — T4 (Turing) has no bf16 support
        seed=SEED,
        max_length=MAX_SEQ_LENGTH,
        completion_only_loss=True,    # mask the prompt; train only on the completion
        logging_steps=10,             # print loss every 10 steps (no tensorboard)
        optim="adamw_8bit",           # 8-bit Adam — lower VRAM (needs bitsandbytes)
        save_strategy="epoch",        # keep an adapter checkpoint per epoch
        save_total_limit=1,           # ...but only the latest -- export uses the live
                                       # in-memory model, not a reloaded checkpoint, so
                                       # older ones are pure disk cost with no purpose
        report_to="none",             # no tensorboard / wandb
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,   # trl >=0.24 renamed this from `tokenizer=`
        train_dataset=dataset,        # prompt/completion columns; trainer tokenizes + masks
        args=training_args,
    )

    # --dry-run: the trainer was constructed above (validating the full
    #    completion_only_loss setup); exit before any training happens ---------
    if args.dry_run:
        print("\n[dry-run] SFTTrainer constructed OK — completion_only_loss path validated")
        print("[dry-run] exiting before training (--dry-run)")
        return

    # 6. Train ----------------------------------------------------------------
    trainer.train()

    # 7. Merge LoRA into 16-bit + export GGUF ----------------------------------
    #    save_pretrained_gguf merges the adapter into the base weights, writes
    #    model.safetensors, and converts to q4_k_m GGUF. On Linux (Kaggle) this
    #    runs natively — Unsloth builds llama.cpp via cmake/apt; no manual step
    #    (the Windows winget/cmake workaround does not apply).
    #
    #    IMPORTANT: Unsloth silently REUSES an existing model.safetensors and
    #    .cache/ in the output dir — it does NOT overwrite them. On a re-run
    #    this leaves stale merged weights on disk (silent stale-export bug).
    #    Wipe the scratch dir first so the merge always writes fresh.
    for stale_dir in (GGUF_SCRATCH_DIR, GGUF_SCRATCH_GGUF_DIR):
        if stale_dir.exists():
            shutil.rmtree(stale_dir)
            print(f"[cleanup] removed stale scratch dir {stale_dir}")
    GGUF_SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    model.save_pretrained_gguf(
        str(GGUF_SCRATCH_DIR),
        tokenizer,
        quantization_method=GGUF_QUANTIZATION_METHOD,
    )

    # Only the final quantized .gguf needs to survive as notebook output -- the
    # merged 16-bit safetensors and any intermediate (unquantized) f16 GGUF stay
    # in scratch and get discarded, since GGUF_OUTPUT_DIR (under /kaggle/working)
    # is quota-limited. Filter by the quant method's name in case Unsloth leaves
    # the f16 intermediate on disk too -- copying THAT defeats the whole point.
    GGUF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_gguf_files = sorted(
        f for search_dir in (GGUF_SCRATCH_DIR, GGUF_SCRATCH_GGUF_DIR) if search_dir.exists()
        for f in search_dir.rglob("*.gguf")
    )
    if not all_gguf_files:
        raise RuntimeError(
            f"save_pretrained_gguf reported success but no .gguf file was found under "
            f"{GGUF_SCRATCH_DIR} or {GGUF_SCRATCH_GGUF_DIR} -- inspect both directories "
            f"before re-running."
        )
    gguf_files = [f for f in all_gguf_files if GGUF_QUANTIZATION_METHOD.lower() in f.name.lower()]
    if not gguf_files:
        print(
            f"[WARN] no .gguf filename matched quantization method "
            f"{GGUF_QUANTIZATION_METHOD!r} -- falling back to copying ALL "
            f"{len(all_gguf_files)} .gguf file(s) found. Check their size below; if one "
            f"is far larger than expected for a quantized model, it's likely the "
            f"unquantized intermediate and should be deleted from GGUF_OUTPUT_DIR."
        )
        gguf_files = all_gguf_files
    elif len(gguf_files) < len(all_gguf_files):
        skipped = [f.name for f in all_gguf_files if f not in gguf_files]
        print(f"[info] not copying non-{GGUF_QUANTIZATION_METHOD} file(s) to output: {skipped}")

    copied_ggufs = []
    for gguf_file in gguf_files:
        dest = GGUF_OUTPUT_DIR / gguf_file.name
        shutil.copy2(gguf_file, dest)
        copied_ggufs.append(dest)
        print(f"[done] copied {gguf_file.name} ({dest.stat().st_size / 1e9:.2f} GB) -> {dest}")

    for scratch_dir in (GGUF_SCRATCH_DIR, GGUF_SCRATCH_GGUF_DIR):
        shutil.rmtree(scratch_dir, ignore_errors=True)
        print(f"[cleanup] removed scratch dir {scratch_dir}")
    print(f"[done] GGUF export complete: {GGUF_OUTPUT_DIR}")

    # 8. Log run manifest -------------------------------------------------------
    log_run_manifest(args, dataset_pairs, copied_ggufs)


if __name__ == "__main__":
    main()
