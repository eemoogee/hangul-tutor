Fine-tuning decisions and lessons log
Running record of key decisions, failed experiments, and lessons learned during the hangul-expert QLoRA fine-tuning project. Updated as decisions are made or reversed. Not a roadmap (see docs/skills/hangul-finetune-roadmap.md) — this captures why, not what next.
2026-Q2 — Base model selection: Qwen3-8B
Decision: Use Qwen/Qwen3-8B as the teacher/fine-tune target, not qwen2.5:7b or bllossom:8b.
Why: Qwen3-8B was the only model tested that correctly answered both the romanized trigger ("batchim") and the native-script trigger ("받침") raw, without fine-tuning. The other candidates failed one or both.
Still open: No separate -Instruct variant exists for Qwen3-8B — the base model is used directly with a custom Modelfile serving template.
2026-Q2 — Thinking mode suppression: empty pre-closed think block
Decision: Suppress Qwen3-8B's chain-of-thought thinking mode via an empty pre-closed think block in the Modelfile serving template: <think>\n\n</think> immediately after <|im_start|>assistant.
Why: Three approaches were tested:
Plain ChatML (no think tokens): produces a bare assistant prompt identical to thinking mode, letting the CoT prior fire regardless — doesn't suppress.
Prepend <think>\n\n</think> before generation: caused infinite think loops (~23% hang rate across a 13-question sweep).
Empty pre-closed block in the serving template: zero bleed across the same 13-question sweep. This is the correct fix.
Alternatives rejected: Plain ChatML (doesn't work), prepend (hang rate unacceptable for interactive use).
Note: Training template uses plain ChatML (no think tokens) — acceptable because the suppression fix lives at the serving layer, not the training layer.
2026-Q2 — Model card template: do NOT use unsloth 4-bit variant
Decision: Use Qwen/Qwen3-8B with load_in_4bit=True and dtype=float16 on Kaggle T4 x2. Do NOT use unsloth/Qwen3-8B-unsloth-bnb-4bit.
Why: The unsloth variant bakes in bf16 compute dtype, which is wrong for T4 GPUs (T4 supports fp16, not bf16). Using it causes silent dtype mismatches.
2026-Q2 — GGUF export: must happen in the same Python process as training
Decision: Call push_to_hub_gguf on the live model object in the same Python process as training. Do not reload from checkpoint for export.
Why: Reloading via from_pretrained or load_adapter after training does not correctly merge LoRA weights for GGUF export. The merged export only works reliably when called on the in-memory trained model object before the process exits.
2026-Q2 — Epochs: 1 epoch overfits at small dataset size
Decision: Use 2 epochs, not 3, for datasets in the 250–300 pair range.
Evidence: v1 dataset (small) overfit at 3 epochs. Moved to 1 epoch for v2, then 2 epochs from v3 onward as dataset grew. WARMUP_STEPS scaled with dataset size (8 at v10/380 pairs → 11 at v11/425 pairs).
Still open: Whether 2 epochs remains correct at current dataset size (425 pairs) is the first question to answer in B5 — the epoch experiment is planned as the cheapest controlled test before any new data work.
2026-Q2 — 받침 trigger: native script reliable, romanization is not
Decision: Native-script trigger (받침) is the reliable form for batchim queries. Romanized trigger ("batchim") is unreliable and accepted as a known limitation. RAG handles the romanized trigger at inference for the production app (Goal A).
Evidence: Romanized "batchim" failed even at 7B scale across multiple training runs. 받침 variants alone (added in v7, ablated against WeightedRandomSampler) were sufficient to fix the native-script trigger. The sampler was the wrong lever — reverting to plain SFTTrainer with 받침 variants only was the correct fix.
Alternatives rejected:
WeightedRandomSampler 2.0× (v6): batchim no-RAG passed but letter facts degraded (hallucination, batchim contamination in concepts). Not stable. This result does NOT generalize — it establishes only that oversampling didn't work for this specific target, not that oversampling can't work for correction behavior or other targets.
2026-Q2 — RAG: production path for Goal A, off-limits for Goal B
Decision: RAG-at-inference is the correct architecture for the production hangul-tutor app (Goal A). It is explicitly off-limits for the fine-tuning capability experiment (Goal B).
Why (Goal A): The app already knows decompositions deterministically (COMPOUND_COMPONENTS map, JAMO dict). Injecting ground truth into the grading context and asking the model to explain the result is good system design — the model supplies tutoring, the deterministic system supplies ground truth. No virtue in making the LLM independently reconstruct something the app already knows.
Why (Goal B): The experiment's question is specifically "can an 8B model internalize correction behavior sufficiently to independently reject a wrong learner attempt?" RAG removes the challenge that makes the experiment interesting. If the answer turns out to be "not reliably at this scale," that is a valid and useful result — it identifies a boundary between knowledge the model can retrieve and behavioral judgment it can reliably internalize through fine-tuning.
2026-Q2 — Sycophancy: knowledge-gated, not generic (v10 finding)
Finding: After B3 (correction pairs), sycophancy shifted from blanket agreement (v8: agreed with everything wrong) to knowledge-gated agreement (v10: correctly rejects 허→하 and 무→모, but rubber-stamps 카≠가, 따≠다, 곧's batchim). This is qualitatively different from v8's behavior and is a positive result, not merely a non-result: the aggregate sycophancy metric (10/6) didn't improve, but the model's pattern of failure changed in a meaningful way. This suggests at least two separable components:
Factual representation → correction behavior (trainable: v10 showed this can fire when the underlying knowledge is solid)
Confident learner framing → willingness to contradict (may be the harder, possibly scale-limited component)
Don't let the flat aggregate metric erase this qualitative finding. B5 experiments should try to determine whether the second component can be moved independently of the first.
Implication: Correction behavior is trained but can only fire when underlying factual knowledge is solid. B4 was designed to ground the missing facts (aspirated/tense consonant distinctions) before adding more correction pairs.
B4 result: Factual grounding improved terminology slightly but did not move the sycophancy rate (v11: 10/6 wrong-attempts rubber-stamped, identical to v10). Across successive training datasets incorporating additional correction examples and targeted factual grounding (B3 → B4 → v11), the measured sycophantic-accept behavior remained unchanged. Note: the datasets did not change only in correction-pair volume — B4 also changed the model's factual representation of consonant distinctions. The flat result cannot cleanly isolate correction-pair count as the sole variable.
Current hypothesis: Sycophancy-under-correction may require the model to hold a fact firmly enough to contradict a confident-sounding user claim under social pressure — a harder bar than holding the fact well enough to state it when asked directly. These may be different skills that don't transfer via more correction pairs.
Primary evaluation metric: The four-way capability vector is the primary outcome, not sycophancy rate alone. Each component is a distinct diagnostic:
accept-correct: does it recognize valid learner production?
reject-wrong: does correction behavior fire at all?
named-wrong-component: does it know why something is wrong?
sycophantic-accept: does it override its knowledge under confident learner framing?
This allows distinguishing "correction behavior isn't learned" from "correction behavior is learned but factual diagnosis isn't reliable" from "both are learned but confident user framing suppresses contradiction" — three different failure modes that a single sycophancy rate would collapse together.
Regression suite (required on every B5 run): Every training run must be evaluated against a control suite covering basic Hangul facts, existing batchim knowledge, B4 consonant distinctions, compound-vowel knowledge, and correct production attempts — in addition to the production probe. Without this, an improvement in sycophancy rejection could be masking degradation elsewhere. Precedent: v6 WeightedRandomSampler improved batchim while degrading letter facts and contaminating concept answers. That failure mode must be detectable.
Planned experiment sequence (B5):
Diagnostic question: is the model undertrained? — Epoch experiment (same dataset, same hyperparameters, vary epochs only). Check both capability vector and regression suite. If flat → proceed to step 2.
Diagnostic question: does correction behavior scale with training representation? — Scaling curve analysis (B3→B4→v11) using the 4-way capability vector. Treat as observational, not perfectly controlled: B4 changed factual representation as well as correction-pair volume, so the finding should be stated as "across successive datasets incorporating additional correction examples and targeted factual grounding, sycophantic- accept behavior remained unchanged" — not as a clean isolation of correction-pair count as the sole variable. If curve shows learnable-but-weak → proceed to step 3.
Diagnostic question: does representation concentration help? — Ratio/oversampling experiment targeting correction behavior specifically. v6 batchim result does not generalize as prior evidence against this. Monitor regression suite.
If all flat: evidence increasingly supports a capability boundary under the tested 8B/QLoRA regime — document as a capability-boundary hypothesis, not a definitive architectural limit. This establishes that the tested training recipe failed robustly, not that no possible QLoRA/SFT configuration on Qwen3-8B could learn the behavior.
2026-Q2 — Kaggle: CLI push triggers run immediately, no save-without-run
Finding: kaggle kernels push pushes AND runs immediately (verified CLI v2.2.4). There is no save-without-run option in the CLI. GPU allocation via CLI push is unreliable — use web UI "Save and Run All" for reliable GPU runs.
2026-Q2 — Kaggle dataset mount path: short form only
Finding: Dataset path on Kaggle is /kaggle/input/<slug>/<filename> — NOT the longer /kaggle/input/datasets/eemoogee/<slug>/<filename> form. The longer path caused FileNotFoundError on the v11 run. Corrected in all references.
2026-Q2 — Eval classifier: DISAGREE list needs curation, not growth
Finding: The production_probe.py classifier's DISAGREE trigger list had "almost" as a marker, but the model uses "Almost!" as praise/encouragement ("Almost! You wrote 뵈 — that's correct..."), not as a hedge or rejection. This caused stance=reject and verdict=WRONG on a correct confirmation — a false-positive inverse-rule regression.
Fix: Removed "almost" from DISAGREE (commit 6d43120). Validated: the c-compound-ood row's verdict changed WRONG→EXACT; no other rows affected; genuine rejections still score as rejections.
Implication for historical data: v10 and v11 recorded inverse-rule counts should be treated as upper bounds — the same brittle matching was active then, and no raw transcripts exist to recheck. v11's inverse=2 is now confirmed classifier noise (both were this false positive), not real model regressions. Annotated in evals/README.md (commit d164912).
General lesson: When adding trigger words to DISAGREE/AGREE lists, check whether the model uses the same word in a confirming context. Trigger-word lists need periodic review as model phrasing patterns become known, not just accumulation of more markers.
2026-Q2 — Eval instrumentation: raw responses must be persisted
Finding: v10 and v11 eval runs captured only EXACT/PARTIAL/WRONG verdicts in evals/README.md. When the B5 capability-split analysis needed to retroactively re-score v10/v11 at finer granularity (4-way split: accept-correct / reject-wrong / named-wrong-component / sycophantic-accept), the raw model response text was not available — those probes printed to stdout only and the output was never saved.
Fix: production_probe.py now writes per-run JSONL (production_probe_raw.jsonl) with full raw response text and all derived classifier fields per item per run (commit 5a67835). File is gitignored (regenerated per run). The README summary is still written — both records serve different purposes.
Lesson: Any metric you might want to analyze retroactively needs to be persisted at capture time, not reconstructed from coarse labels later. "We can always re-run" is only true if the model version hasn't changed.
Stale file to clean up
hangul_finetune_gaps.md (repo root) reflects v2 dataset coverage (145 pairs) and has never been updated. The canonical version is generated fresh by the dataset generator — the committed copy is misleading. Should be deleted or regenerated and recommitted when the dataset generator is next run.
