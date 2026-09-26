"""
hangul_conversation.py — Conversational glue for Hangul Tutor.

Generates tiny Korean sentences constrained to ONLY the syllables the user
has mastered. Validates LLM output by decomposing every syllable and
rejecting any that fall outside the allowed set, then retrying.

Sentence sources, in priority order:
  1. Tatoeba corpus  — real, natural Korean sentences filtered down to ones
     that use only mastered syllables. Guaranteed valid, no LLM invention.
  2. LLM generation  — constrained prompt + syllable validation + retry.
  3. Templates       — instant, always valid, used when the above fail.

Three interaction modes:
  - read_translate: Show Korean sentence → user translates to English
  - fill_blank: Show sentence with one word missing → user fills it
  - reply_korean: Ask a simple question → user answers in Korean
"""

import json
import random
import re
import sys
import subprocess
import os
from pathlib import Path
from typing import Optional

from hangul_quiz_engine import HangulQuiz
from hangul_models import get_model

MAX_RETRIES = 3
TATOEBA_PATH = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "data" / "tatoeba_kor_sentences.tsv"


# ── Syllable utilities ─────────────────────────────────────────────────────

def decompose(syllable: str) -> tuple:
    """Decompose Hangul syllable → (cho, jung, jong). Returns None for non-Hangul."""
    if len(syllable) != 1:
        return None
    code = ord(syllable)
    if code < 0xAC00 or code > 0xD7A3:
        return None  # Not a Hangul syllable
    code -= 0xAC00
    jong = code % 28
    jung = ((code - jong) // 28) % 21
    cho = ((code - jong) // 28) // 21
    return (cho, jung, jong)


def extract_syllables(text: str) -> list[str]:
    """Extract all Hangul syllable blocks from a text string."""
    syllables = []
    for char in text:
        if decompose(char) is not None:
            syllables.append(char)
    return syllables


def validate_sentence(sentence: str, allowed_syllables: set[str]) -> tuple[bool, list[str]]:
    """Check if every Hangul syllable in the sentence is in the allowed set.
    Returns (is_valid, list_of_illegal_syllables)."""
    found = extract_syllables(sentence)
    illegal = [s for s in found if s not in allowed_syllables]
    return len(illegal) == 0, illegal


# ── Tatoeba corpus — real sentences filtered to mastered syllables ─────────

_tatoeba_cache: Optional[list[str]] = None


def _load_tatoeba_sentences() -> list[str]:
    """Load and cache Korean sentences from the Tatoeba corpus (tab-separated:
    id, lang, sentence). Returns an empty list if the file is missing."""
    global _tatoeba_cache
    if _tatoeba_cache is not None:
        return _tatoeba_cache

    sentences = []
    if TATOEBA_PATH.exists():
        with open(TATOEBA_PATH, encoding='utf-8') as f:
            for line in f:
                parts = line.rstrip('\n').split('\t')
                if len(parts) >= 3 and parts[2].strip():
                    sentences.append(parts[2].strip())
    _tatoeba_cache = sentences
    return sentences


def find_tatoeba_sentence(
    allowed_syllables: set[str], min_syllables: int = 2, max_syllables: int = 6
) -> Optional[str]:
    """Find a real Korean sentence from the Tatoeba corpus using ONLY the
    given syllables (punctuation/spaces/numbers are ignored automatically —
    validate_sentence only looks at actual Hangul syllable blocks).
    Returns None if nothing in the corpus matches."""
    candidates = []
    for sentence in _load_tatoeba_sentences():
        syls = extract_syllables(sentence)
        if not (min_syllables <= len(syls) <= max_syllables):
            continue
        is_valid, _ = validate_sentence(sentence, allowed_syllables)
        if is_valid:
            candidates.append(sentence)
    return random.choice(candidates) if candidates else None


def _translate_via_ollama(korean: str, model: str) -> Optional[str]:
    """Ask the LLM to translate an already-verified-safe Korean sentence.
    Unlike sentence generation, this doesn't need syllable validation —
    the Korean text is fixed and came straight from the Tatoeba corpus, so
    a rough translation is fine even if the LLM output is imperfect."""
    prompt = (
        "Translate this Korean sentence to short, natural English. "
        f"Reply with ONLY the translation, nothing else.\n\n{korean}"
    )
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8'
        )
        if result.returncode == 0:
            line = result.stdout.strip().split('\n')[0].strip()
            return line or None
    except Exception:
        pass
    return None


# ── Single-word vocab exposure (no LLM needed) ──────────────────────────────

# Guaranteed to contain at least one real vocab match (아이 = "child", using
# only 아 and 이) — used when the learner's own mastered syllables don't
# happen to spell any real word yet, so build_template_sentence still has
# something genuine to fall back to instead of giving up.
_SAFE_DEFAULT_SYLLABLES = ["가", "나", "다", "아", "이"]

READING_PRACTICE_PATH = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "data" / "reading_practice.jsonl"
_reading_practice_cache: Optional[list[dict]] = None


def _load_reading_practice() -> list[dict]:
    """Load and cache reading_practice.jsonl — richer than
    konglish_vocab.json: includes real multi-word phrases (source
    'combo', e.g. "이 방" = "this room") and real subject+verb sentences
    (source 'phrase', e.g. "나는 먹는다" = "I eat") alongside single words
    (sources 'native' and 'konglish'). One source type is excluded:
      - 'drill': raw consonant+vowel syllable rows (e.g. "아 어 오 우 으
        이"), not real content — their 'english' field is a romanization
        breakdown, not a translation.
    'phrase' entries were corrected before being wired in — the original
    data had two real bugs: English subject-verb agreement errors
    throughout (always using 3rd-person-singular form regardless of
    subject — "I/me eats" instead of "I eat"), and several Korean errors
    from a stray 다 appended to noun stems (좋은 날다 instead of 좋은 날,
    confusing 날 "day" with 날다 "to fly") or attached directly to a noun
    without the required 이/입니다 copula (이것은 책다 instead of 이것은
    책입니다). Both are now fixed in the data file itself.
    Returns an empty list if the file is missing."""
    global _reading_practice_cache
    if _reading_practice_cache is not None:
        return _reading_practice_cache

    entries = []
    if READING_PRACTICE_PATH.exists():
        with open(READING_PRACTICE_PATH, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("source") == "drill":
                    continue
                if entry.get("korean") and entry.get("english"):
                    entries.append(entry)
    _reading_practice_cache = entries
    return entries


def _find_real_word(allowed_syllables, quiz: 'HangulQuiz') -> Optional[dict]:
    """Find ONE real vocabulary word — a SINGLE token (no space in the
    Korean string) — that is spellable entirely from allowed_syllables.
    Searches reading_practice.jsonl first (richer — includes real words),
    then konglish_vocab.json. Multi-word entries (e.g. "이 방" = "this
    room", or a subject+verb phrase) are excluded, so the result is always
    honest exposure of one word, never a phrase dressed up as a word.
    Skips konglish_vocab's 'useful_phrases' category on purpose: it's
    greetings, adverbs, and question words (안녕, 빨리, 뭐, 누구, 어디...),
    none of which make sensible standalone vocabulary to drill. Returns a
    {'ko': ..., 'en': ...} dict, or None if nothing matches."""
    allowed_set = set(allowed_syllables)
    candidates = []

    for entry in _load_reading_practice():
        ko = entry.get("korean", "")
        if " " in ko:
            continue
        if ko and all(c in allowed_set for c in ko):
            candidates.append({"ko": ko, "en": entry["english"]})

    vocab = quiz.get_konglish_vocab()
    for category, words in vocab.get("categories", {}).items():
        if category == "useful_phrases":
            continue
        for entry in words:
            ko = entry.get("ko", "")
            if " " in ko:
                continue
            if ko and all(ch in allowed_set for ch in ko):
                candidates.append(entry)

    return random.choice(candidates) if candidates else None


def build_template_sentence(allowed_syllables: list[str], quiz: 'HangulQuiz') -> dict:
    """Return ONE real, spellable single word as honest vocab exposure —
    instant, no LLM, no sentence construction. There are no grammar
    templates anymore (no 이것은/저것은/입니다 wrapping) and no multi-word
    real sentences: the learner sees a real word they can actually read,
    framed as exposure ("a real Korean word you can already spell"), never
    "you can now read this sentence". A word is only a candidate if it is
    a single token (no space), enforced inside _find_real_word. Falls back
    to a small safe-default syllable set when the learner's own syllables
    don't spell any real word yet, so this always has something genuine to
    show rather than giving up.
    """
    word = _find_real_word(allowed_syllables, quiz) or _find_real_word(_SAFE_DEFAULT_SYLLABLES, quiz)

    if word is None:
        # Shouldn't happen — _SAFE_DEFAULT_SYLLABLES is chosen specifically
        # to guarantee a match — but fall back honestly rather than
        # fabricate meaning if it somehow ever does.
        return {
            "korean": "".join(allowed_syllables[:2]) or "가나",
            "english": "(no real-word match yet — just practice reading these syllables, no translation to check)",
            "answer": None,
            "mode": "syllable_practice",
            "syllables_used": list(allowed_syllables[:2]),
            "method": "template"
        }

    return {
        "korean": word["ko"],
        "english": word["en"],
        "answer": None,
        "mode": "vocab_exposure",
        "syllables_used": extract_syllables(word["ko"]),
        "method": "template"
    }

def _build_constrained_prompt(
    allowed_syllables: list[str],
    mode: str,
    previous_failure: Optional[str] = None
) -> str:
    """Build a prompt that tightly constrains the LLM to only use given syllables."""

    syl_list = ", ".join(sorted(allowed_syllables))
    syl_count = len(allowed_syllables)

    base_instruction = f"""You are a Korean language teacher. Create a TINY Korean sentence using ONLY these {syl_count} syllable blocks:

{syl_list}

RULES (follow exactly or your response is invalid):
1. Every Korean character you write MUST be from the list above — NOTHING else
2. No spaces within words, spaces only between words
3. Keep the sentence 2-4 words long
4. Include an English translation on a separate line starting with "EN:"
5. Do NOT add explanations, romanization, or anything else"""

    mode_instructions = {
        "read_translate": """
TASK: Write a very simple Korean statement using the allowed syllables.
The user will read it and translate it to English.
Make it a real, natural sentence (even if very basic).
Example format:
  저는 학생입니다
  EN: I am a student""",

        "fill_blank": """
TASK: Write a Korean sentence where ONE word is replaced with [___].
The user must fill in the blank using only the allowed syllables.
The missing word should be a single syllable block from the allowed list.
Example format:
  저는 [___]입니다
  EN: I am a ___
  ANSWER: 학생""",

        "reply_korean": """
TASK: Ask a simple question in Korean. The user must answer in Korean
using only the allowed syllables. The question itself must also only use
allowed syllables.
Example format:
  이름이 무엇입니까?
  EN: What is your name?"""
    }

    prompt = base_instruction + mode_instructions.get(mode, mode_instructions["read_translate"])

    if previous_failure:
        prompt += f"""

PREVIOUS ATTEMPT FAILED because it used syllables outside the allowed list.
Illegal syllables used: {previous_failure}
Fix this: rewrite the sentence using ONLY syllables from the allowed list above."""

    prompt += "\n\nKorean sentence:"

    return prompt


# ── Conversation turn generator ────────────────────────────────────────────

def generate_conversation_turn(
    quiz: HangulQuiz,
    mode: str = "read_translate",
    model: str = None,
    use_llm: bool = True,
    use_tatoeba: bool = True
) -> Optional[dict]:
    """Generate a conversational Korean sentence using only mastered syllables.

    Tries, in order: a real Tatoeba sentence (read_translate mode only),
    then LLM generation, then a template — always falling back rather than
    failing outright.

    Returns dict with:
      - korean: the Korean sentence
      - english: English translation
      - answer: the expected answer (for fill_blank mode)
      - mode: the interaction mode
      - syllables_used: which mastered syllables appeared
      - method: "tatoeba" | "llm" | "template"
      Or None if generation failed after retries.
    """
    # Resolve per-task models — an explicit `model` param overrides both,
    # otherwise sentence generation and translation are configured
    # independently (see hangul_models.py).
    sentence_model = model or get_model("sentence")
    translate_model = model or get_model("translate")

    # Get mastered syllables (confidence >= 3 = "known") — filtered to
    # ones with a genuine initial consonant. A vowel-only syllable
    # (아/어/오, still all you'd have early in Lesson 1) can't carry real
    # word meaning on its own; asking the LLM for a "real, natural
    # sentence" using only those is an impossible request and just
    # invites a hallucinated string with a fabricated translation.
    # hangul_cli.py's generate_mini_sentence already guards against this
    # with quiz.has_real_consonant() — applied here too so /talk gets the
    # same protection, not just the auto-triggered mini-sentence feature.
    mastered = {
        s for s, v in quiz.progress.get("mastered_letters", {}).items()
        if v >= 3 and decompose(s) is not None and quiz.has_real_consonant(s)
    }

    # Also include syllables from completed lessons' practice lists
    for lesson in quiz.curriculum["lessons"]:
        if lesson["id"] in quiz.progress.get("completed_lessons", []):
            for syl in lesson.get("practice_syllables", []):
                if decompose(syl) is not None and quiz.has_real_consonant(syl):
                    mastered.add(syl)

    if len(mastered) < 3:
        # Not enough to build anything honest yet. (This used to return
        # "아이가" as a gradeable read_translate turn with a made-up
        # "translation" the learner was then marked against.) Callers
        # already treat None as "keep practicing".
        return None

    allowed = sorted(mastered)

    # Template mode — instant, no LLM needed
    if not use_llm:
        return build_template_sentence(allowed, quiz)

    # Prefer a real sentence from the Tatoeba corpus when possible — more
    # natural than anything the LLM would invent, and guaranteed to use
    # only allowed syllables since we filtered for that.
    if use_tatoeba and mode == "read_translate":
        tatoeba_sentence = find_tatoeba_sentence(mastered)
        if tatoeba_sentence:
            translation = _translate_via_ollama(tatoeba_sentence, translate_model)
            return {
                "korean": tatoeba_sentence,
                # None (not a placeholder string) when the model couldn't
                # translate, so the caller shows a self-check instead of
                # grading the learner against the placeholder text.
                "english": translation,
                "answer": None,
                "mode": "read_translate",
                "syllables_used": extract_syllables(tatoeba_sentence),
                "method": "tatoeba"
            }

    failure_note = None

    for attempt in range(MAX_RETRIES):
        prompt = _build_constrained_prompt(allowed, mode, failure_note)

        try:
            result = subprocess.run(
                ["ollama", "run", sentence_model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=90,
                encoding='utf-8'
            )
            if result.returncode != 0:
                continue

            output = result.stdout.strip()

            # Parse the output
            lines = output.split('\n')
            korean_line = ""
            english_line = ""
            answer_line = None

            for line in lines:
                line = line.strip()
                if line.startswith("EN:") or line.startswith("English:"):
                    english_line = line.split(":", 1)[1].strip()
                elif line.startswith("ANSWER:") or line.startswith("Answer:"):
                    answer_line = line.split(":", 1)[1].strip()
                elif line and not line.startswith("#") and not line.startswith("```"):
                    # First non-empty, non-metadata line is the Korean sentence
                    if not korean_line:
                        korean_line = line

            # Clean the Korean line — keep only Hangul and spaces
            korean_clean = re.sub(r'[^\uAC00-\uD7A3\s]', '', korean_line).strip()

            if not korean_clean:
                failure_note = "no Korean text found in output"
                continue

            # Validate: every syllable must be in the allowed set
            is_valid, illegal = validate_sentence(korean_clean, set(allowed))
            if not is_valid:
                failure_note = ", ".join(illegal[:5])
                continue

            return {
                "korean": korean_clean,
                "english": english_line or None,
                "answer": answer_line,
                "mode": mode,
                "syllables_used": extract_syllables(korean_clean),
                "attempts": attempt + 1,
                "method": "llm"
            }

        except subprocess.TimeoutExpired:
            failure_note = "timeout"
            continue
        except Exception as e:
            failure_note = str(e)[:100]
            continue

    # All LLM retries exhausted — fall back to template
    return build_template_sentence(allowed, quiz)


# ── Answer checking for conversation modes ─────────────────────────────────

_FILLER_WORDS = {
    "a", "an", "the", "is", "am", "are", "was", "were", "be", "it", "its",
    "this", "that", "to", "of", "and", "i", "you", "he", "she", "we", "they",
    "my", "your", "do", "does", "did", "in", "on", "at",
}


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", text.lower()) if w not in _FILLER_WORDS}


def check_conversation_answer(
    user_input: str,
    turn: dict,
    quiz: HangulQuiz
) -> dict:
    """Check the user's answer for a conversation turn.
    Returns feedback dict with correct, feedback, and scoring info.

    Only gradeable modes (read_translate, fill_blank, reply_korean) should
    reach this function — exposure turns (vocab_exposure / syllable_practice)
    are presented by their callers without grading. An unrecognized mode is a
    caller bug, so it raises instead of silently passing."""
    mode = turn.get("mode", "read_translate")
    user_clean = user_input.strip()

    if mode == "read_translate":
        # User translates Korean → English. Fuzzy match on English.
        expected = (turn.get("english") or "").lower()
        user_lower = user_clean.lower()

        # Keyword overlap on CONTENT words only — punctuation stripped and
        # filler words ignored, so "it is a dog" no longer scores 75% against
        # "it is a cat" just by sharing 'it', 'is' and 'a'.
        expected_words = _content_words(expected) or set(re.findall(r"[a-z']+", expected))
        user_words = set(re.findall(r"[a-z']+", user_lower))
        overlap = expected_words & user_words
        score = len(overlap) / max(1, len(expected_words))

        if score >= 0.5:
            return {
                "correct": True,
                "feedback": f"✅ Good! The translation is: **{expected}**",
                "score": score
            }
        else:
            return {
                "correct": False,
                "feedback": f"Not quite. The Korean means: **{expected}**\nYou said: {user_clean}",
                "score": score
            }

    elif mode == "fill_blank":
        expected = turn.get("answer", "")
        if not expected:
            return {"correct": True, "feedback": "✅ (no answer key — self-check!)", "score": 1.0}

        if user_clean == expected:
            return {"correct": True, "feedback": f"✅ Correct! The word is **{expected}**", "score": 1.0}
        else:
            return {"correct": False, "feedback": f"❌ The missing word is **{expected}**, not '{user_clean}'", "score": 0.0}

    elif mode == "reply_korean":
        # User answers in Korean. Check if their answer uses only mastered syllables.
        mastered = {
            s for s, v in quiz.progress.get("mastered_letters", {}).items()
            if v >= 3 and decompose(s) is not None
        }
        is_valid, illegal = validate_sentence(user_clean, mastered)

        if not is_valid:
            return {
                "correct": False,
                "feedback": f"⚠️ Your answer used syllables you haven't mastered yet: {', '.join(illegal[:5])}\nTry using only these: {', '.join(sorted(mastered)[:10])}",
                "score": 0.0
            }

        if len(user_clean) < 1:
            return {"correct": False, "feedback": "Try answering in Korean!", "score": 0.0}

        return {
            "correct": True,
            "feedback": f"✅ Nice Korean answer! ({len(extract_syllables(user_clean))} syllables used correctly)",
            "score": 1.0
        }

    raise ValueError(f"no grading defined for conversation mode {mode!r}")


# ── Demo ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Hangul Conversation module...")
    quiz = HangulQuiz()

    # Simulate some progress
    quiz.progress["mastered_letters"] = {
        "아": 4, "이": 4, "가": 3, "나": 3, "다": 3, "저": 3, "는": 3
    }
    quiz.progress["completed_lessons"] = [1, 2]

    print(f"Mastered syllables: {sorted(quiz.progress['mastered_letters'].keys())}")

    turn = generate_conversation_turn(quiz, mode="read_translate",
                                       model="llama3.2:1b-instruct-q4_K_M")
    if turn:
        print(f"\nKorean: {turn['korean']}")
        print(f"English: {turn['english']}")
        print(f"Syllables used: {turn['syllables_used']}")
        print(f"Attempts: {turn.get('attempts', '?')}")
    else:
        print("\nGeneration failed after retries.")
