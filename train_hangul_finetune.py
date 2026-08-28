#!/usr/bin/env python3
"""
Train a QLoRA adapter on the Hangul factual dataset (145 Q&A pairs) and export
a GGUF model for local inference (e.g. loading into Ollama).

Loss masking: assistant-only. We fine-tune only on the assistant's answer tokens
(not the user's question), via TRL's `assistant_only_loss=True`.

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
DATASET_PATH = BASE_DIR / "hangul_finetune_factual.jsonl"
CHECKPOINT_DIR = BASE_DIR / "outputs"                 # trainer logs + adapter checkpoints
GGUF_OUTPUT_DIR = BASE_DIR / "hangul_expert_model"    # final merged model + GGUF

# ---------------------------------------------------------------------------
# LoRA config
# ---------------------------------------------------------------------------
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.0
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
NUM_EPOCHS = 3
LEARNING_RATE = 2e-4
WARMUP_RATIO = 0.1
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


# Chat-template patch --------------------------------------------------------
def enable_assistant_mask(tokenizer) -> None:
    """
    Add `{% generation %}` markers to the chat template so TRL's
    `assistant_only_loss=True` can tell which tokens belong to the assistant.

    Why this is needed: TRL computes the assistant mask with
    `apply_chat_template(..., return_assistant_tokens_mask=True)`, which relies on
    the `{% generation %}` Jinja block. Qwen2.5's shipped template does NOT have
    that block, so the mask would come back all-zero and TRL would raise
    "at least one example has no assistant tokens".

    The markers are *pure tracking* — they emit no text, so the rendered prompt
    and tokenization are byte-for-byte identical before and after this patch.
    """
    template = tokenizer.chat_template.replace("\r\n", "\n")

    old = (
        '    {%- if (message.role == "user") or (message.role == "system" and not loop.first) or (message.role == "assistant" and not message.tool_calls) %}\n'
        "        {{- '<|im_start|>' + message.role + '\\n' + message.content + '<|im_end|>' + '\\n' }}\n"
    )
    new = (
        '    {%- if (message.role == "user") or (message.role == "system" and not loop.first) %}\n'
        "        {{- '<|im_start|>' + message.role + '\\n' + message.content + '<|im_end|>' + '\\n' }}\n"
        '    {%- elif (message.role == "assistant" and not message.tool_calls) %}\n'
        "        {{- '<|im_start|>' + message.role + '\\n' }}\n"
        '        {%- generation %}\n'
        "        {{- message.content + '<|im_end|>' + '\\n' }}\n"
        '        {%- endgeneration %}\n'
    )

    if old not in template:
        raise RuntimeError(
            "Could not patch the Qwen2.5 chat template for assistant masking — "
            "the template structure did not match expectations. (Check the model's "
            "tokenizer_config.json chat_template.)"
        )

    tokenizer.chat_template = template.replace(old, new)


# 4. Dataset loading ----------------------------------------------------------
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


# Dry-run helper ---------------------------------------------------------------
def print_tokenized_sample(tokenizer, example: dict) -> None:
    """Print one example's rendered prompt + tokenization (for --dry-run)."""
    messages = example["messages"]

    rendered = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=False
    )
    out = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        return_dict=True,
        add_generation_prompt=False,
        return_assistant_tokens_mask=True,
    )
    input_ids = out["input_ids"]
    mask = out.get("assistant_masks") or []
    n_assistant = int(sum(mask))

    print("\n[dry-run] sample messages:")
    for m in messages:
        print(f"    {m['role']}: {m['content']!r}")
    print("\n[dry-run] rendered prompt (tokenize=False):")
    print(rendered)
    print(f"\n[dry-run] token count: {len(input_ids)}")
    print(f"[dry-run] trainable (assistant) tokens: {n_assistant} / {len(input_ids)}")
    if n_assistant:
        assistant_ids = [tid for tid, m in zip(input_ids, mask) if m == 1]
        print(f"[dry-run] decoded assistant tokens: {tokenizer.decode(assistant_ids)!r}")


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

    # Enables TRL's assistant-only loss (see function docstring).
    enable_assistant_mask(tokenizer)

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

    # 4. Load the (un-tokenized) dataset -------------------------------------
    dataset = load_dataset(DATASET_PATH)

    # --dry-run: show one tokenized sample, then exit before training ---------
    if args.dry_run:
        print_tokenized_sample(tokenizer, dataset[0])
        print("\n[dry-run] exiting before training (--dry-run)")
        return

    # 5. Trainer -------------------------------------------------------------
    training_args = SFTConfig(
        output_dir=str(CHECKPOINT_DIR),
        per_device_train_batch_size=PER_DEVICE_BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        num_train_epochs=NUM_EPOCHS,
        learning_rate=LEARNING_RATE,
        warmup_ratio=WARMUP_RATIO,
        lr_scheduler_type=LR_SCHEDULER_TYPE,
        fp16=True,                    # NOT bf16 — RTX 4050 has no bf16 support
        seed=SEED,
        max_length=MAX_SEQ_LENGTH,
        assistant_only_loss=True,     # mask the user turn; train only on the answer
        logging_steps=10,             # 8. print loss every 10 steps (no tensorboard)
        optim="adamw_8bit",           # 8-bit Adam — lower VRAM (needs bitsandbytes)
        save_strategy="epoch",        # keep an adapter checkpoint per epoch
        report_to="none",             # no tensorboard / wandb
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,   # trl >=0.24 renamed this from `tokenizer=`
        train_dataset=dataset,        # un-tokenized messages; trainer tokenizes + masks
        args=training_args,
    )

    # 6. Train ----------------------------------------------------------------
    trainer.train()

    # 7. Save merged model + export GGUF (Q4_K_M) -----------------------------
    #    save_pretrained_gguf merges the LoRA adapter back into the base weights,
    #    writes a merged 16-bit copy, then converts to llama.cpp GGUF.
    model.save_pretrained_gguf(
        str(GGUF_OUTPUT_DIR),
        tokenizer,
        quantization_method="q4_k_m",
    )
    print(f"[done] merged model + GGUF saved to {GGUF_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
