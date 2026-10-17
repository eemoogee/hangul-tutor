"""Minimal plain-text playtest runner for SejongFlow."""

import json
import time
from pathlib import Path

from hangul_quiz_engine import HangulQuiz
from sejong_flow import SejongFlow


ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "data" / "sejong_state.json"
CONTENT_PATH = ROOT / "data" / "sejong.json"


class ActiveClock:
    def __init__(self):
        self.last = time.monotonic()
        self.pending = 0

    def mark(self):
        now = time.monotonic()
        self.pending += min(max(0, now - self.last), 120) * 1000
        self.last = now

    def take(self):
        self.mark()
        amount = round(self.pending)
        self.pending = 0
        return amount


def save(flow):
    STATE_PATH.write_text(flow.export_state(), encoding="utf-8")


def show_line(line):
    print(f"{line['speaker'].title()}: {line['text']}")


def wait_for_enter():
    while input("[Enter] ").strip():
        print("Press Enter without typing to continue. Answers go at the choice or text prompt.")


def render(events, clock):
    for event in events:
        kind = event["kind"]
        if kind == "stage":
            print(f"\n[{event['batch_name']} — {event['phase']}]\n")
            continue
        if kind == "narrator":
            show_line(event)
        elif kind == "letter_intro":
            print(f"{event['jamo']} = {event['roman']} — {event['sound']}\n{event['shape']}")
            if "notice_line" in event:
                show_line(event["notice_line"])
        elif kind == "predict":
            print(f"{event['consonant']} + {event['vowel']} = ?")
        elif kind == "reveal":
            print(f"{event['parts'][0]} + {event['parts'][1]} = {event['block']} ({event['roman']})")
        elif kind == "question":
            print(f"\n{event['prompt']}\n{event['display']}")
            if "round" in event:
                print(f"{event['round']['index']} / {event['round']['size']}")
        elif kind == "result":
            print(("Correct" if event["correct"] else "Try again later") +
                  f" — {event['correct_answer']}")
            if "line" in event:
                show_line(event["line"])
        elif kind == "word_read":
            print(f"{event['ko']} ({event['roman']}) = {event['en']}")
            if "line" in event:
                show_line(event["line"])
        elif kind == "hint":
            print("Hint:", event["text"])
        elif kind == "score":
            print(f"{event['context']}: {event['correct']} / {event['size']}")
        elif kind == "milestone":
            print(f"\n*** {event['id'].replace('_', ' ').title()} — {event['time_text']} ***")
            for line in event["lines"]:
                show_line(line)
        elif kind == "notice":
            print(event["text"])
        elif kind == "finished":
            print("Finished:", event["outcome"])
            return None
        elif kind == "await":
            if event["input"] == "choice":
                for index, choice in enumerate(event["choices"], 1):
                    print(f"  {index}. {choice}")
                prompt = f"Choice (1-{len(event['choices'])} or exact option): "
                raw = input(prompt)
            elif event["input"] == "continue":
                wait_for_enter()
                raw = ""
            else:
                raw = input("> ")
            elapsed = clock.take()
            if event["input"] == "choice" and raw.isdigit():
                index = int(raw) - 1
                if 0 <= index < len(event["choices"]):
                    raw = event["choices"][index]
            return raw, elapsed
        if kind in ("narrator", "letter_intro", "reveal", "word_read", "milestone", "result"):
            wait_for_enter()
            clock.mark()
    return None


def main():
    content = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
    quiz = HangulQuiz(persist=False)
    if STATE_PATH.exists():
        choice = input("Resume saved Sejong Test? [Y/n] ").strip().lower()
        if choice not in ("n", "no"):
            flow = SejongFlow.from_state(quiz, content, STATE_PATH.read_text(encoding="utf-8"))
            events = flow.resume("reopen")
        else:
            flow = SejongFlow(quiz, content)
            events = flow.start()
    else:
        flow = SejongFlow(quiz, content)
        events = flow.start()
    save(flow)
    clock = ActiveClock()
    try:
        while True:
            reply = render(events, clock)
            if reply is None:
                break
            answer, active_ms = reply
            events = flow.submit(answer, active_ms)
            save(flow)
    except (KeyboardInterrupt, EOFError):
        print("\nPlace saved. Run again to resume.")
        save(flow)


if __name__ == "__main__":
    main()
