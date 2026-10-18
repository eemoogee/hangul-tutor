"""Browser regression checks for curriculum saves from the deployed code baseline.

The legacy fixture is generated with the controller and envelope code at
eee9950, the commit used for the recorded Netlify Drop package. It is not a
current-format save with only its app hash changed.
"""

import hashlib
import json
import random
import subprocess
import sys
import threading
import types
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_web import SOURCES, build  # noqa: E402
from hangul_quiz_engine import HangulQuiz  # noqa: E402

BASELINE = "eee9950"
KEY = "hangul.curriculum.v1"
BACKUP = KEY + ".backup"
SEJONG_KEY = "sejong.slice.v1"


def committed(path):
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)


def deployed_fixture(round_card=False):
    source = committed("curriculum_flow.py")
    app = committed("web/app.js").decode("utf-8")
    save_code = app[app.index("function saveState() {"):app.index("async function callFlow(")]
    assert "JSON.stringify({app_version: appVersion, state: exportState()," in save_code
    assert "teaching:" not in save_code and "save_version:" not in save_code
    assert '"hangul.curriculum.v1"' in app
    module = types.ModuleType("deployed_curriculum_flow")
    module.__file__ = f"{BASELINE}:curriculum_flow.py"
    sys.modules[module.__name__] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    random.seed(83)
    quiz = HangulQuiz(persist=False)
    flow = module.CurriculumFlow(quiz)
    flow.start()
    flow.submit("/next")
    flow.submit("/next")
    assert quiz.current_lesson["id"] == 3 and flow.phase == "practice"
    for _ in range(10 if round_card else 2):
        flow.submit("/skip" if round_card else flow.current_question.correct_answer, 500)
    state = flow.export_state()
    assert json.loads(state)["round_asked"] == (10 if round_card else 2)
    assert flow.phase == ("round" if round_card else "practice")
    files = [{"path": path, "sha256": hashlib.sha256(committed(path)).hexdigest(),
              "bytes": len(committed(path))} for path in SOURCES]
    build_hash = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:16]
    envelope = {"app_version": f"curriculum-web-1:{build_hash}", "state": state,
                "started_at": "2026-10-17T16:00:00.000Z", "finished_at": None,
                "log": [{"qid": "deployed-format", "answer": "example"}]}
    assert set(envelope) == {"app_version", "state", "started_at", "finished_at", "log"}
    return json.dumps(envelope, ensure_ascii=False, separators=(",", ":")), json.loads(state)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

    def log_message(self, *_):
        pass


def run():
    build()
    assert (ROOT / "web" / "teaching.json").is_file()
    legacy_raw, legacy_state = deployed_fixture()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}/"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context()
            page = context.new_page()

            def load(raw):
                page.goto(base + "teaching.json")
                page.evaluate("localStorage.clear()")
                page.evaluate("([key, value]) => {localStorage.setItem(key, value); localStorage.setItem('sejong.slice.v1', 'sejong-sentinel')}", [KEY, raw])
                page.goto(base + "?course=curriculum&test=1&seed=83", wait_until="domcontentloaded")
                page.wait_for_function("document.querySelector('#screen')?.dataset.kind !== 'loading'", timeout=120000)

            def stored(key=KEY):
                return page.evaluate("key => localStorage.getItem(key)", key)

            load(legacy_raw)
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            migrated = json.loads(stored())
            resumed = page.evaluate("__curriculumTest.state()")
            assert migrated["save_kind"] == "curriculum-controller"
            assert migrated["save_version"] == 1
            assert migrated["app_version"] != json.loads(legacy_raw)["app_version"]
            assert migrated["teaching"] is None
            assert stored(BACKUP) == legacy_raw
            assert stored(SEJONG_KEY) == "sejong-sentinel"
            assert resumed["lesson_id"] == legacy_state["lesson_id"] == 3
            assert resumed["current_question"] == legacy_state["current_question"]
            assert resumed["round_asked"] == legacy_state["round_asked"] == 2
            assert resumed["round_no"] == legacy_state["round_no"]
            original_progress = json.loads(legacy_state["quiz"])
            resumed_progress = json.loads(resumed["quiz"])
            # start_lesson stamps a new visit time when the controller is restored.
            original_progress.pop("last_session", None)
            resumed_progress.pop("last_session", None)
            assert resumed_progress == original_progress, {
                key: (original_progress.get(key), resumed_progress.get(key))
                for key in original_progress if original_progress.get(key) != resumed_progress.get(key)
            }
            assert page.locator("#screen").get_attribute("data-kind") == "question"
            print("PASS deployed-format Lesson 3 save, progress, held question, round, and separate Sejong key")

            page.reload()
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            repeated = page.evaluate("__curriculumTest.state()")
            assert repeated["lesson_id"] == resumed["lesson_id"]
            assert repeated["current_question"] == resumed["current_question"]
            assert repeated["round_asked"] == resumed["round_asked"]
            assert repeated["round_no"] == resumed["round_no"]
            assert stored(BACKUP) == legacy_raw
            assert page.locator("#screen").get_attribute("data-kind") == "question"
            print("PASS repeat loading migrated save without teaching")

            round_raw, round_state = deployed_fixture(round_card=True)
            load(round_raw)
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            restored_round = page.evaluate("__curriculumTest.state()")
            assert restored_round["phase"] == "round"
            assert restored_round["round_asked"] == round_state["round_asked"] == 10
            assert restored_round["card"] == round_state["card"]
            assert page.locator("#screen").get_attribute("data-kind") == "round_card"
            page.reload()
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            assert page.locator("#screen").get_attribute("data-kind") == "round_card"
            assert page.evaluate("__curriculumTest.state().round_asked") == 10
            print("PASS deployed-format round card and counters survive migration and reload")

            current_without_teaching = {k: v for k, v in migrated.items() if k != "teaching"}
            current_without_teaching["app_version"] = "curriculum-web-1:0000000000000000"
            load(json.dumps(current_without_teaching, ensure_ascii=False))
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            loaded_without_teaching = page.evaluate("__curriculumTest.state()")
            assert loaded_without_teaching["lesson_id"] == resumed["lesson_id"]
            assert loaded_without_teaching["current_question"] == resumed["current_question"]
            assert loaded_without_teaching["round_asked"] == resumed["round_asked"]
            assert page.locator("#screen").get_attribute("data-kind") == "question"
            print("PASS explicit save version ignores build hash and accepts missing teaching key")

            page.goto(base + "teaching.json")
            page.evaluate("localStorage.clear()")
            page.evaluate("([key, value]) => localStorage.setItem(key, value)", [KEY, legacy_raw])
            page.route("**/teaching.json", lambda route: route.fulfill(status=503, body="unavailable"))
            page.goto(base + "?course=curriculum&test=1&seed=83", wait_until="domcontentloaded")
            page.wait_for_function("document.querySelector('#screen')?.dataset.kind === 'save_recovery'", timeout=120000)
            assert stored() == legacy_raw and stored(BACKUP) == legacy_raw
            page.evaluate("flowReady = true; saveState(); flowReady = false")
            assert stored() == legacy_raw
            page.unroute("**/teaching.json")
            page.reload()
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            assert page.evaluate("__curriculumTest.state().lesson_id") == 3
            print("PASS dependency-load failure preserves save; retry after recovery resumes Lesson 3")

            def recovery(raw):
                load(raw)
                assert page.locator("#screen").get_attribute("data-kind") == "save_recovery"
                assert stored() == raw and stored(BACKUP) == raw
                assert page.get_by_role("button", name="Download original save").count() == 1
                assert page.locator(".recovery-data").input_value() == raw
                page.evaluate("flowReady = true; saveState(); flowReady = false")
                assert stored() == raw
                page.reload()
                page.wait_for_function("document.querySelector('#screen')?.dataset.kind === 'save_recovery'", timeout=120000)
                assert page.locator("#screen").get_attribute("data-kind") == "save_recovery"
                assert stored() == raw
                assert stored(SEJONG_KEY) == "sejong-sentinel"

            recovery('{"app_version":')
            print("PASS malformed JSON survives reload and attempted autosave")

            future = dict(migrated, save_version=99)
            recovery(json.dumps(future, ensure_ascii=False))
            print("PASS unsupported future save remains recoverable")

            broken = json.loads(legacy_raw)
            broken_state = json.loads(broken["state"])
            broken_state["current_question"] = None
            broken["state"] = json.dumps(broken_state, ensure_ascii=False)
            recovery(json.dumps(broken, ensure_ascii=False))
            print("PASS failed legacy migration preserves the original during autosave")

            denied = browser.new_context()
            denied.add_init_script("""(() => {
                const original = Storage.prototype.setItem;
                Storage.prototype.setItem = function(key, value) {
                    if (key === 'hangul.curriculum.v1' &&
                        String(value).includes('"save_kind":"curriculum-controller"'))
                        throw new Error('simulated migration write failure');
                    return original.call(this, key, value);
                };
            })()""")
            denied_page = denied.new_page()
            denied_page.goto(base + "teaching.json")
            denied_page.evaluate("([key, value]) => localStorage.setItem(key, value)", [KEY, legacy_raw])
            denied_page.goto(base + "?course=curriculum&test=1&seed=83", wait_until="domcontentloaded")
            denied_page.wait_for_function("document.querySelector('#screen')?.dataset.kind === 'save_recovery'", timeout=120000)
            assert denied_page.evaluate("key => localStorage.getItem(key)", KEY) == legacy_raw
            assert denied_page.evaluate("key => localStorage.getItem(key)", BACKUP) == legacy_raw
            denied.close()
            print("PASS failed migration write keeps primary and backup byte-identical")

            page.get_by_role("button", name="Start fresh instead").click()
            assert stored() == json.dumps(broken, ensure_ascii=False)
            page.get_by_role("button", name="Keep my save").click()
            assert stored() == json.dumps(broken, ensure_ascii=False)
            page.get_by_role("button", name="Start fresh instead").click()
            page.get_by_role("button", name="Start fresh", exact=True).click()
            page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
            assert page.locator("#screen").get_attribute("data-kind") == "lesson1_teaching"
            assert stored(BACKUP) == json.dumps(broken, ensure_ascii=False)
            assert stored(SEJONG_KEY) == "sejong-sentinel"
            print("PASS fresh start requires explicit choice and retains the original backup")

            first_lesson_save = json.loads(stored())
            first_lesson_state = json.loads(first_lesson_save["state"])
            for phase, expected in (("intro", "teaching_intro"),
                                    ("predict", "teaching_pair_predict"),
                                    ("feedback", "teaching_pair_predict"),
                                    ("explore", "teaching_explore")):
                old_guide = {"phase": phase,
                             "choice": "ㅇ" if phase in ("feedback", "explore") else None,
                             "selected": "ㅜ" if phase == "explore" else None}
                candidate = dict(first_lesson_save,
                                 teaching={"kind": "lesson1", "lesson_id": 1,
                                           "state": json.dumps(old_guide, ensure_ascii=False),
                                           "message": ""})
                raw_candidate = json.dumps(candidate, ensure_ascii=False)
                load(raw_candidate)
                page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
                assert page.locator("#screen").get_attribute("data-step") == expected
                assert stored(BACKUP) == raw_candidate
                normalized = json.loads(stored())
                assert json.loads(normalized["teaching"]["state"])["version"] == 2
                state = page.evaluate("__curriculumTest.state()")
                assert state["current_question"] == first_lesson_state["current_question"]
                assert state["round_asked"] == first_lesson_state["round_asked"]
                page.reload()
                page.wait_for_function("window.__curriculumTest?.ready()", timeout=120000)
                assert page.locator("#screen").get_attribute("data-step") == expected
            assert stored(SEJONG_KEY) == "sejong-sentinel"
            print("PASS actual old Lesson 1 teaching states normalize with backup and held question")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    run()
