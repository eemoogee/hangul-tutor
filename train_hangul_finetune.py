#!/usr/bin/env python3
"""
Train a QLoRA adapter on the Hangul v3 dataset (276 Q&A pairs) and export
a GGUF model for local inference (e.g. loading into Ollama).

Loss masking: completion-only. We fine-tune only on the assistant's answer
tokens (not the user's question), via Unsloth/TRL's native
`completion_only_loss=True` with a prompt/completion dataset split.

SETUP (see requirements-finetune.txt for the full pinned version list)
-----------------------------------------------------------------------
This must run inside a dedicated venv, and `pip install -r requirements-finetune.txt`
ALONE WILL NOT WORK — torch has to come from the PyTorch CUDA 12.4 index and
torchao must be pinned before unsloth. Follow these three steps in order:

    1) pip install torch==2.6.0 torchvision==0.21.0 \
           --index-url https://download.pytorch.org/whl/cu124
    2) pip install torchao==0.16.0 xformers==0.0.29.post3 triton-windows==3.2.0.post21  # must precede unsloth
    3) pip install -r requirements-finetune.txt

Target hardware: NVIDIA RTX 4050 Laptop GPU (6 GB VRAM). Training runs in fp16
(the card has no reliable bf16 support), so dtype is pinned to float16.

Usage:
    python train_hangul_finetune.py            # full training run
    python train_hangul_finetune.py --dry-run  # load model + dataset, show one
                                               # tokenized sample, then exit
"""

from unsloth import FastLanguageModel  # MUST be imported first — patches transformers/peft at import time

import argparse
import json
import shutil
import sys
from pathlib import Path

import torch
from datasets import Dataset
from trl import SFTConfig, SFTTrainer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent            # .../hangul-tutor
MODEL_NAME = "unsloth/Qwen2.5-1.5B-Instruct-bnb-4bit"
DATASET_PATH = BASE_DIR / "hangul_finetune_v3.jsonl"
CHECKPOINT_DIR = BASE_DIR / "outputs"                 # trainer logs + adapter checkpoints
GGUF_OUTPUT_DIR = BASE_DIR / "hangul_expert_model"    # final merged model + GGUF

# ---------------------------------------------------------------------------
# LoRA config
# ---------------------------------------------------------------------------
LORA_R = 16
LORA_ALPHA = 32
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
NUM_EPOCHS = 1
LEARNING_RATE = 1e-4
WARMUP_STEPS = 3  # 0.1 * ceil(276/8) * 1 epoch = 0.1 * 35 = 3.5 → 3
LR_SCHEDULER_TYPE = "cosine"
SEED = 42


# 1. Environment check -------------------------------------------------------
def check_environment() -> None:
    """Verify CUDA before doing anything else; exit clearly if missing."""
    if not torch.cuda.is_available():
        print(
            "ERROR: CUDA is not available. This script needs an NVIDIA GPU.\n"
            "  - Confirm the cu124 build of torch is installed (see the header).\n"
            '  - Diagnose with:  python -c "import torch; print(torch.cuda.is_available())"',
            file=sys.stderr,
        )
        sys.exit(1)

    gpu_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    print(f"[env] GPU: {gpu_name} ({vram_gb:.1f} GB VRAM)")
    print(f"[env] torch {torch.__version__}  CUDA {torch.version.cuda}")


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

    `prompt` holds the system + user turns (everything before the answer);
    `completion` holds the assistant turns. The trainer masks every prompt
    token, so we train only on the assistant's answer — the same outcome the
    old `assistant_only_loss` approach aimed for, on a supported code path.
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
        "--dry-run",
        action="store_true",
        help="Load the model and dataset, print one tokenized sample, then exit without training.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    check_environment()

    # 2. Load the 4-bit base model + tokenizer via Unsloth -------------------
    #    load_in_4bit=True keeps the base weights in 4-bit NF4 (QLoRA). dtype
    #    controls the LoRA/compute precision -> float16 (no bf16 on RTX 4050).
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=torch.float16,
        load_in_4bit=True,
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
    dataset = load_dataset(DATASET_PATH)
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
        fp16=True,                    # NOT bf16 — RTX 4050 has no bf16 support
        seed=SEED,
        max_length=MAX_SEQ_LENGTH,
        completion_only_loss=True,    # mask the prompt; train only on the completion
        logging_steps=10,             # print loss every 10 steps (no tensorboard)
        optim="adamw_8bit",           # 8-bit Adam — lower VRAM (needs bitsandbytes)
        save_strategy="epoch",        # keep an adapter checkpoint per epoch
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

    # 7. Merge LoRA into 16-bit + attempt GGUF export --------------------------
    #    save_pretrained_gguf merges the adapter into the base weights and writes
    #    model.safetensors correctly (save_pretrained_merged does NOT write the
    #    merged weights in this Unsloth version). Its GGUF conversion step then
    #    breaks on the master convert-script, so we convert to GGUF manually.

    #    IMPORTANT: Unsloth silently REUSES an existing model.safetensors and
    #    .cache/ in the output dir — it does NOT overwrite them. On a re-run this
    #    would leave stale merged weights on disk, and the manual GGUF conversion
    #    would quantize the OLD model while Ollama reports the same layer hash
    #    (silent stale-export bug). Delete them first so the merge writes fresh.
    for stale in (
        GGUF_OUTPUT_DIR / "model.safetensors",
        GGUF_OUTPUT_DIR / ".cache",
    ):
        if stale.is_dir():
            shutil.rmtree(stale)
            print(f"[cleanup] removed stale dir {stale}")
        elif stale.is_file():
            stale.unlink()
            print(f"[cleanup] removed stale file {stale}")

    model.save_pretrained_gguf(
        str(GGUF_OUTPUT_DIR),
        tokenizer,
        quantization_method="q4_k_m",
    )


if __name__ == "__main__":
    main()
