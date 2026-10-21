# Task: Preserve and back up experimental work (no new development)

**Date:** 2026-10-21 · **Repository:** `eemoogee/hangul-tutor`

**Status:** executed by Codex on 2026-10-21 and completed by Claude the same day. Branch and commit results are in `docs/prototypes/syllable-swap-study/VERSIONS.md` and the final preservation report. This copy is sanitized: machine-specific paths are replaced with branch names and repository-relative paths.

**Authorization:** inventory, commit, and push approved experimental work to feature branches.
- Do not merge, deploy, or modify production code.
- Do not open pull requests.
- **Stop after preservation. Do not start another implementation task.**

## 0. Safety rules

- **Run every `git worktree` command from the Windows host.** From the owner's Linux VM, Windows worktrees falsely show as "prunable". **Never run `git worktree prune`.**
- No `git add .`, `git clean`, hard resets, force pushes, or history rewrites of published commits.
- Before each commit, review the staged diff. Stage only intended files, by explicit path.
- **Do not commit on `codex/lesson1-teaching`.** The main working folder is checked out there and contains unrelated uncommitted work.

## 1. Check that pushing works

Before committing anything, confirm that `origin` is reachable and authenticated. If it isn't, stop and report.

## 2. Inventory (report before changing anything)

Inspect the repository, every worktree, local branches, and live remote branches. Don't assume a worktree is committed, or that a branch is pushed.

**Codex worktrees, in risk order:**
1. **Syllable Swap Input Comparison** (Codex worktree; detached HEAD before preservation). **Highest risk.**
2. Worktrees inside the git-ignored `.verify_out/` folder:
   - `exploding-syllable-prototype` (branch `codex/exploding-syllable-prototype`)
   - `jamo-interaction-experiment`
   - `transfer-lab-review`
3. The vowel prototype archive (Codex worktree, branch `docs/archive-vowel-prototypes`; unpushed before preservation).
4. Any Relief-Exploded Syllable, Living Syllable or Remove-and-Return work found in other worktrees.

**Untracked design files in the main working folder:**
- `docs/prototypes/syllable-lift-study/`
- `docs/prototypes/syllable-swap-study/`
- `docs/prototypes/hangul-rain/` (added after this brief was first sent)
- `docs/notes/2026-10-19-*.md` (competitor note, Claude review, relief-exploded review, Hyojang review, design synthesis)
- `docs/tasks/2026-10-19_relief-exploded-syllable-study.md`
- `docs/tasks/2026-10-20_living-syllable-remove-return.md`
- this file

**Owner decisions; report, don't act:**
- the uncommitted section 8 edits in `docs/hangul_game_plan.md`
- a stray root file named `tash list`
- the two `sejong-opening-update*.patch` files
- the uncommitted Lesson 1 / Sejong work

## 3. Preserve, in this order

1. **Input Comparison** → branch `prototype/syllable-swap-input-comparison`.
2. **`.verify_out` worktrees** → their existing branches. Exclude browser profiles, caches, logs, and build output.
3. **Design files** → `design/physical-hangul-studies`, created from `master` in a fresh worktree outside `.verify_out/`. Copy the files unchanged.
4. **Lesson 1 / Sejong work:** report only. Do not commit without the owner's instruction.

**Provenance:** see `docs/prototypes/syllable-swap-study/VERSIONS.md`. Keep both versions where they meaningfully differ; don't silently choose one.

## 4. Verify (narrow)

- Each committed prototype opens without console errors.
- Staged diffs contain only intended files: no production code, nothing personal or sensitive, no caches, **no machine-specific usernames or absolute paths**.
- Original baselines are unchanged.
- Every new commit is reachable from a named branch.

Do not run the full Sejong or Lesson 1 suites for this task.

## 5. Back up

Push with ordinary, non-force pushes. Verify each branch with `git ls-remote origin <branch>`.

## 6. Final report

A table with these columns:
- item
- local branch
- commit SHA
- remote branch
- verification
- remaining uncommitted work

Then list:
- pending owner decisions
- worktrees with unique uncommitted changes
- unresolved provenance questions
