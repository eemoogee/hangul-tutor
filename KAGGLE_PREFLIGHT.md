# Kaggle fine-tune pre-flight checklist

Run through every item before launching a Kaggle fine-tune session. Each check exists
because a past run burned a session (or shipped a broken model) by skipping it — the
"why" notes are there so future-you doesn't trim a check that looks pointless.

## 0. Kaggle launch (web UI — do these before "Save & Run All")

These three are *launch* gates, distinct from the in-script checks below. They live in the
Kaggle **web UI**, not the CLI, and each exists because a past run burned GPU quota by
skipping it.

- [ ] **Accelerator = GPU T4 x2** (Settings → Accelerator), not "None".
  - *Why:* `enable_gpu: true` + `machine_shape: NvidiaTeslaT4` in `kernel-metadata.json` do NOT guarantee a GPU — a CLI-triggered push can still land on a CPU instance (`torch 2.10.0+cpu`), and Unsloth dies at import with `NotImplementedError: Unsloth cannot find any torch accelerator? You need a GPU.` (v11 run, 2026-09-01). The CLI `push`/`--accelerator` flag is the unreliable path — confirm the accelerator in the UI, every time.
- [ ] **HF_TOKEN secret attached** (Settings → Secrets), or `--hf-repo` removed from the run cell.
  - *Why:* Kaggle secrets are NOT auto-injected; `UserSecretsClient().get_secret("HF_TOKEN")` falls through to `except` and the log prints `HF_TOKEN available: False`. The failure is deferred to *after* training, so you burn a successful run with no GGUF pushed. Either attach the secret, or drop `--hf-repo` and pull the GGUF via `kaggle kernels output` instead.
- [ ] **Internet enabled** (Settings → Internet).
  - *Why:* the notebook `pip install`s Unsloth/transformers, downloads the base model, and (optionally) pushes to HF — all need network. A run with internet off fails fast on the first `pip install`, not on training.

## 1. Dataset verification

- [ ] Map every eval question to a training-data question (grep the JSONL by keyword).
  - *Why:* the v7 sweep graded "basic consonants / vowels / letter count" that had zero training coverage — the model looped or fell back to base knowledge, and those failures looked like fine-tune bugs when they were really out-of-distribution.
- [ ] Flag any eval question with zero training coverage as OOD *before* running.
  - *Why:* OOD answers are base-model knowledge, not fine-tune quality — grade them separately (§5), don't chase them as bugs.
- [ ] Confirm the dataset file the script points at exists on the runner.
  - *Why:* `DEFAULT_DATASET` is a hardcoded filename; a stale path fails silently at trainer construction, not at parse time.

## 2. Template verification

- [ ] Render ONE full training example end-to-end (prompt with `add_generation_prompt=True`, then the completion) and print the exact string.
  - *Why:* the Qwen3 template's `loop.last` clause injects `<think>\n\n</think>\n\n` into completions **regardless of the enable_thinking flag** — this is the single source of the thinking-loop bug.
- [ ] Confirm ZERO think tokens in BOTH the prompt and the completion.
  - *Why:* if think tokens leak into completions, the model never unlearns CoT and hangs ~23% of queries at inference.
- [ ] Confirm the completion_only_loss boundary is plain ChatML: prompt ends at `<|im_start|>assistant\n`, completion adds only answer tokens — no `<think>` wrapper, no duplicated think block.
  - *Why:* a duplicated `<think>`/assistant-header boundary misaligns the loss mask and corrupts training.
- [ ] Confirm training format == serving format (same template in the script and the serving Modelfile).
  - *Why:* a mismatch means the model is fine-tuned on one prompt shape but served on another — recall works in training, degrades at inference.

## 3. VRAM check

- [ ] Confirm free VRAM on the target GPU meets the script's `REQUIRED_VRAM_MIB` before loading the base model.
  - *Why:* the 7B QLoRA needs ~8 GB; a T4 with a leftover process loaded will OOM mid-run, not at launch.
- [ ] Stop any process holding the GPU first (other kernels/notebooks; locally, orphaned `llama-server.exe` → `taskkill //F //PID`), then verify `nvidia-smi` shows headroom.
  - *Why:* leftover GPU holders silently starve the run; they don't fail the pre-flight, they fail the training.

## 4. Thinking mode

- [ ] Verify suppression on the PROMPT side (generation prompt has no `<think>`).
  - *Why:* the enable_thinking flag only patches the prompt; confirming it renders clean catches the flag not being applied.
- [ ] Verify suppression on the COMPLETION side (completion has no `<think>`).
  - *Why:* the prompt-side check alone is insufficient — the completion is where think tokens actually leak (§2).
- [ ] Do both checks on a `--dry-run` / one-step run BEFORE full training.
  - *Why:* a full 2-epoch run is minutes; catching a template bug on the dry-run costs seconds.

## 5. Eval scope

- [ ] Label each eval question in-distribution (has a training twin) or out-of-distribution (no training twin) before grading.
  - *Why:* only ID questions measure the fine-tune; OOD questions measure base-model knowledge, and failures there are not fine-tune regressions.
- [ ] Grade ID and OOD separately.
  - *Why:* mixing them makes a fine-tune look worse than it is (OOD loop/hallucination) or better (base model already knows the answer).

## 6. Post-run

- [ ] After GGUF export, record the new Ollama model ID and confirm it differs from the previous live ID.
  - *Why:* the stale-export bug reuses an old `model.safetensors`; an unchanged ID means you promoted the old weights.
- [ ] Run the regression sweep (13 questions) and grade against training facts before calling it stable.
  - *Why:* "loss went down" ≠ "facts are recalled" — past runs had low loss but one shipped a 23% hang rate and a wrong-domain hallucination.
- [ ] Confirm no-RAG batchim/받침 recall before declaring the no-RAG goal met.
  - *Why:* batchim romanization has been the persistent failure; a run that still needs RAG isn't the goal state.
