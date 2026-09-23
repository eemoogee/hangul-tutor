"""
sim_lesson.py — Simulate a lesson session without human input.

Usage:
    python sim_lesson.py                    # Lesson 1, 30 questions, all correct
    python sim_lesson.py --lesson 2         # Lesson 2
    python sim_lesson.py --questions 50     # 50 questions
    python sim_lesson.py --errors 0.15      # ~15% wrong answers
    python sim_lesson.py --mode read_aloud  # lock to one mode
    python sim_lesson.py --show-questions   # print each Q&A as it happens

Prints the full session summary and lesson complete screen at the end,
exactly as the real app would show them.
"""

import sys
import os
import argparse
import random

# Add the hangul-tutor directory to path so we can import the engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hangul_quiz_engine import HangulQuiz

# ── Minimal styled() shim so hangul_cli output functions work ─────────
BOLD="\033[1m"; GREEN="\033[92m"; RED="\033[91m"; YELLOW="\033[93m"
CYAN="\033[96m"; RESET="\033[0m"

def styled(t, *codes): return "".join(codes) + t + RESET

# ── Inline the output functions we need from hangul_cli ──────────────
# (avoids importing the full CLI which has other module dependencies)

def print_lesson_intro(introduction="", note=""):
    if introduction:
        print(f"\n{styled('📖 Introduction', BOLD, CYAN)}")
        print(f"   {introduction}")
    if note:
        print(f"\n{styled('📝 Note:', BOLD)} {note}")

def print_reference_table(quiz, lesson):
    """Simplified reference table — letters and pronunciations."""
    letters = lesson.get("letters", [])
    pron    = lesson.get("pronunciation", {})
    if not letters:
        return
    roman = quiz.get_romanization_table()
    print(f"\n{styled('📋 Reference Table', BOLD, CYAN)}")
    composed = [quiz._letter_to_syllable(l) if l in "ㅏㅓㅗㅜㅡㅣㅑㅕㅛㅠㅐㅔㅒㅖㅘㅙㅚㅝㅞㅟㅢ" else l for l in letters]
    print("   " + "   ".join(composed))
    print("   " + "   ".join(f"{roman.get(l,'?'):<4}" for l in letters))
    print()
    for l in letters:
        p = pron.get(l, "")
        r = roman.get(l, "?")
        if p:
            print(f"   {l} ({r})  —  {p}")

def print_lesson_complete(quiz):
    """Print the lesson complete summary box."""
    W = 32
    lesson = quiz.current_lesson
    if not lesson:
        return
    summary = quiz.get_progress_summary()
    m = quiz.lesson_mastery(lesson["id"])
    acc = summary.get("session_pct", 0)
    qs  = summary.get("session_score", "0/0")
    stk = summary.get("streak_best", 0)

    # Weakest item — use LearnerItem.confidence, not flat mastered_letters.
    # Word-based lessons track the same mastery_words pool lesson_mastery
    # measures, so the weakest item is reported from that pool to match.
    pool = lesson.get("mastery_words") or quiz._get_lesson_syllable_pool(lesson)
    weakest = min(pool, key=lambda s: quiz._get_item(s).confidence) if pool else ""

    # Next lesson
    all_lessons = quiz.list_lessons()
    current_id  = lesson["id"]
    next_lesson = next((l for l in all_lessons if l["id"] == current_id + 1), None)

    # Next lesson preview — use letters, practice_syllables, or example_syllables
    # depending on what the next lesson has
    next_preview = ""
    if next_lesson:
        nl = next_lesson
        if "letters" in nl:
            next_preview = " ".join(nl["letters"][:5])
        elif "practice_syllables" in nl:
            next_preview = " ".join(nl["practice_syllables"][:5])
        elif "example_syllables" in nl:
            next_preview = " ".join(nl["example_syllables"][:5])

    lines = [
        styled(f"║{'LESSON COMPLETE':^{W}}║", BOLD, CYAN),
        styled(f"╠{'═'*W}╣", CYAN),
        f"║  {'Accuracy':<14}{str(acc)+'%':>{W-16}}  ║",
        f"║  {'Questions':<14}{str(qs):>{W-16}}  ║",
        f"║  {'Best Streak':<14}{str(stk)+' ✦':>{W-16}}  ║",
        f"║  {'Weakest':<14}{weakest:>{W-16}}  ║",
        f"║{' '*W}║",
    ]
    if next_lesson:
        lines += [
            f"║  {'Next':<14}{('Lesson '+str(next_lesson['id'])):>{W-16}}  ║",
            f"║{next_preview:^{W}}║",
        ]
    lines.append(styled(f"╚{'═'*W}╝", CYAN))

    print(f"\n{styled(f'╔{chr(9552)*W}╗', CYAN)}")
    for line in lines:
        print(line)

# ── Argument parsing ──────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Simulate a Hangul Tutor lesson session.")
parser.add_argument("--lesson",         type=int,   default=1,     help="Lesson number (default: 1)")
parser.add_argument("--questions",      type=int,   default=30,    help="Number of questions to simulate (default: 30)")
parser.add_argument("--errors",         type=float, default=0.0,   help="Fraction of wrong answers, 0.0–1.0 (default: 0.0)")
parser.add_argument("--mode",           type=str,   default=None,  help="Lock to a specific quiz mode")
parser.add_argument("--show-questions", action="store_true",       help="Print each question and answer as it runs")
parser.add_argument("--progress",       type=str,   default=None,  help="Path to user_progress.json (default: fresh/temp)")
parser.add_argument("--seed",           type=int,   default=None,  help="Random seed for reproducible runs")
args = parser.parse_args()

if args.seed is not None:
    random.seed(args.seed)
    print(f"{styled(f'  [seed: {args.seed}]', YELLOW)}")

# ── Set up quiz ───────────────────────────────────────────────────────
# Change to the script's own directory so relative paths resolve
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Start with a clean quiz instance — reset progress in-memory so the
# sim doesn't inherit real user data. Most reliable across platforms.
quiz = HangulQuiz()
quiz.progress = {
    "current_lesson":         1,
    "completed_lessons":      [],
    "mastered_letters":       {},
    "confusion_counts":       {},
    "learner_items":          {},
    "total_questions_answered": 0,
    "total_correct":          0,
    "streak_best":            0,
    "last_session":           None,
}
quiz.session_correct = 0
quiz.session_total   = 0
quiz.session_streak  = 0

lesson = quiz.start_lesson(args.lesson)
print(f"\n{styled('━'*50, CYAN)}")
lesson_title = f"Lesson {lesson['id']}: {lesson['title']}"
print(f"{styled(f'  Simulating {lesson_title}', BOLD, CYAN)}")
print(f"{styled(f'  {args.questions} questions | {int(args.errors*100)}% error rate', CYAN)}")
if args.mode:
    print(f"{styled(f'  Mode locked: {args.mode}', CYAN)}")
if args.seed is not None:
    print(f"{styled(f'  Seed: {args.seed}', CYAN)}")
print(f"{styled('━'*50, CYAN)}\n")

# Print the lesson intro exactly as the real app does
print_lesson_intro(lesson.get("introduction",""), lesson.get("note",""))
print_reference_table(quiz, lesson)

# ── Simulation loop ───────────────────────────────────────────────────
correct_count = 0
wrong_count   = 0
mastery_hit   = False

for i in range(args.questions):
    q = quiz.next_question(mode=args.mode)

    # Decide: correct or deliberate wrong?
    if random.random() < args.errors:
        # Submit a plausible wrong answer
        if q.choices:
            wrong_choices = [c for c in q.choices if c != q.correct_answer]
            user_input = random.choice(wrong_choices) if wrong_choices else "???"
        else:
            user_input = "???"
    elif q.mode == "read_word":
        # read_word grades against its accepted_romanizations list; the
        # primary one is correct_answer, but use accepted[0] explicitly so
        # the sim never accidentally simulates a "correct" answer that the
        # grader would reject.
        user_input = q.accepted[0] if q.accepted else q.correct_answer
    else:
        user_input = q.correct_answer

    result = quiz.answer(user_input, q)

    if result.correct:
        correct_count += 1
    else:
        wrong_count += 1

    if args.show_questions:
        status = styled("✅", GREEN) if result.correct else styled("❌", RED)
        print(f"  Q{i+1:03d} [{q.mode:20s}] {q.prompt[:40]:<40}  →  {user_input:<8}  {status}")

    # Check mastery after each correct answer
    if result.correct and not mastery_hit:
        m = quiz.lesson_mastery(lesson["id"])
        if m["is_mastered"]:
            mastery_hit = True
            mastery_msg = f"  🎓 Mastery reached at question {i+1} ({m['mastered_count']}/{m['pool_size']} items)"
            print(f"\n{styled(mastery_msg, BOLD, GREEN)}\n")

# ── Final state ───────────────────────────────────────────────────────
print(f"\n{styled('━'*50, CYAN)}")
total = correct_count + wrong_count
pct   = int(correct_count / total * 100) if total else 0
m     = quiz.lesson_mastery(lesson["id"])

mc = m['mastered_count']; ps = m['pool_size']; nd = m['needed']
print(f"{styled(f'  Results: {correct_count}/{total} correct ({pct}%)', BOLD)}")
print(f"{styled(f'  Mastery: {mc}/{ps} items at confidence >= 3 (need {nd})', BOLD)}")
is_done = m['is_mastered']
done_color = GREEN if is_done else YELLOW
print(f"{styled(f'  Lesson complete: {is_done}', BOLD, done_color)}")
print(f"{styled('━'*50, CYAN)}\n")

# Print session summary and lesson complete screen exactly as the real app does
summary = quiz.get_progress_summary()
print(f"{styled('📊 Session Summary:', BOLD)}")
print(f"   Correct: {summary['session_score']} ({summary['session_pct']}%)")
print(f"   Best Streak: {summary['streak_best']}")
if summary.get('top_confusions'):
    print(f"   Practice these: {', '.join(c['pair'] for c in summary['top_confusions'])}")

if (quiz.current_lesson is not None
        and quiz.lesson_mastery(quiz.current_lesson["id"])["is_mastered"]):
    print_lesson_complete(quiz)
