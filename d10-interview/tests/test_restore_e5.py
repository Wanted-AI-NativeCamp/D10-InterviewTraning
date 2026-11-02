# 리포트 저장 · 복원 안정성 테스트 (E-5). coach 의 저장 · 읽기 함수 + Streamlit AppTest. 외부 API 호출 없음.
# 기존 v1 기준 샘플(tests/fixtures/v1)은 읽기만 하고 바꾸지 않는다. 변형은 메모리 안에서만 만든다.
# 실행: d10-interview 폴더에서  python -m unittest discover tests
import ast
import copy
import json
import os
import unittest
from pathlib import Path
from unittest import mock

import coach
from make_v1_samples import DAY, UPDATED_AT, data_of, with_data
from test_app_errors import ROOT, AppErrorCase
from fake_llm import response

FIXTURES = Path(__file__).parent / "fixtures" / "v1"


def fixture(name="v1_with_retry") -> str:
    return (FIXTURES / "supported" / f"{name}.md").read_text(encoding="utf-8")


def load(text: str):
    parsed = coach.parse_report(text)
    questions = coach.match_questions(coach.load_questions(), parsed["profile"]["job"], parsed["questions"])
    return parsed, questions, coach.rebuild_session(parsed["session"], questions)


def save(parsed, questions, s, latest=None) -> str:
    """앱의 build_current_report 와 같은 인자로 다시 저장한다."""
    return coach.build_report(
        parsed["profile"], questions, s["evaluation"], s["retries"], s["messages"],
        s["last_suggest"], s["last_question"], None, parsed["round"],
        coach.load_precheck(), parsed["precheck"], UPDATED_AT, DAY,
        retry_counts=s["retry_counts"], understanding=s["understanding"], retry_history=s["retry_history"],
        clue_set=s["clue_set"], clue_round=s["clue_round"], memo=None, verdict_open=False,
        practice=parsed["session"].get("practice") or [], past_hidden=parsed["session"].get("past_hidden") or [],
        latest_unscored=s["latest_unscored"] if latest is None else latest,
        retry_unreadable=s["retry_unreadable"], evaluation_unreadable=s["evaluation_unreadable"],
    )


def round_trip(text: str, latest=None):
    parsed, questions, s = load(text)
    again = save(parsed, questions, s, latest)
    return again, load(again)


def add_attempt(s, no, score_each, answer):
    """앱의 record_retry 와 같은 규칙으로 기록을 더한다 (ID · 최고 점수 · 횟수)."""
    history = s["retry_history"].setdefault(no, [])
    attempt = {"answer": answer, **coach.checked_retry({k: score_each for k in coach.CRITERIA} | {"weak": "약한 점"})}
    attempt["attempt_id"] = coach.next_attempt_id(no, history, s["retry_unreadable"].get(no, []))
    history.append(attempt)
    s["retries"] = coach.reflected_retries(s["evaluation"], s["retry_history"])
    s["retry_counts"] = {n: len(h) for n, h in s["retry_history"].items()}
    return attempt


def edit_session(text: str, change) -> str:
    data = data_of(text)
    change(data["session"])
    return with_data(text, data)


class AnswerVersionsTest(unittest.TestCase):
    """최초 · 최고 · 최신 답의 저장 · 복원."""

    def test_first_answer_and_evaluation_kept(self):
        parsed, questions, s = load(fixture())
        first = copy.deepcopy((s["messages"], s["evaluation"]))
        for i in range(5):
            add_attempt(s, 1, 5, f"1번 재도전 {i}")
        _, (_, _, again) = round_trip(save(parsed, questions, s))
        self.assertEqual((again["messages"], again["evaluation"]), first)

    def test_best_and_tie_after_round_trip(self):
        parsed, questions, s = load(fixture())
        no = 3  # 샘플: 처음 11점, 기존 재도전 8점 (반영 없음)
        a = add_attempt(s, no, 4, "16점 먼저")
        add_attempt(s, no, 4, "16점 나중")              # 동점 → 먼저 받은 답
        add_attempt(s, no, 1, "낮은 점수")
        _, (_, _, again) = round_trip(save(parsed, questions, s))
        self.assertEqual(again["retries"][no]["attempt_id"], a["attempt_id"])
        best = add_attempt(again, no, 5, "20점")
        self.assertEqual(again["retries"][no]["attempt_id"], best["attempt_id"])

    def test_latest_unscored_saved_and_restored(self):
        parsed, questions, s = load(fixture())
        totals = coach.total_scores(s["evaluation"], s["retries"])
        text = save(parsed, questions, s, latest={2: "채점받지 못한 최신 답"})
        self.assertEqual(data_of(text)["session"]["latest_unscored"], {"2": {"answer": "채점받지 못한 최신 답"}})
        _, _, again = load(text)
        self.assertEqual(again["latest_unscored"], {2: "채점받지 못한 최신 답"})
        self.assertEqual(again["retry_history"], s["retry_history"])                   # 기록 · 횟수 · 점수는 그대로
        self.assertEqual(coach.total_scores(again["evaluation"], again["retries"]), totals)

    def test_latest_same_as_scored_not_duplicated(self):
        parsed, questions, s = load(fixture())
        scored = s["retry_history"][2][0]["answer"]
        first = coach.answer_text(s["messages"], 2)
        text = save(parsed, questions, s, latest={2: f"  {scored} ", 3: first})
        self.assertNotIn("latest_unscored", data_of(text)["session"])

    def test_best_not_stored_separately(self):
        """최고 점수 답은 기록에서 계산한다: 파일의 retries 값이 틀려도 기록으로 다시 고른다."""
        parsed, questions, s = load(fixture())
        add_attempt(s, 2, 5, "20점")
        text = edit_session(save(parsed, questions, s), lambda ses: ses["retries"].clear())
        _, _, again = load(text)
        self.assertEqual(again["retries"][2]["answer"], "20점")


class ManyAttemptsTest(unittest.TestCase):

    def test_45_attempts_round_trip(self):
        parsed, questions, s = load(fixture())
        for i in range(45):
            add_attempt(s, 3, 5 if i == 43 else 1, f"3번 재도전 {i + 1}")  # 최고 점수는 44번째
        _, (_, _, again) = round_trip(save(parsed, questions, s))
        history = again["retry_history"][3]
        self.assertEqual(len(history), 46)                                   # 기존 1 + 45
        self.assertEqual([a["attempt_id"] for a in history], [f"q3-a{n}" for n in range(1, 47)])
        self.assertEqual(again["retries"][3]["answer"], "3번 재도전 44")
        self.assertEqual(again["retry_counts"][3], 46)

    def test_over_limit_rejected_not_trimmed(self):
        parsed, questions, s = load(fixture())
        items = [{"answer": f"a{i}", "specific": 1, "relevance": 1, "structure": 1, "evidence": 1, "weak": ""}
                 for i in range(coach.MAX_ATTEMPTS_PER_QUESTION + 1)]
        text = edit_session(save(parsed, questions, s), lambda ses: ses["retry_history"].update({"4": items}))
        with self.assertRaises(ValueError) as caught:
            coach.parse_report(text)
        self.assertIn("500개 초과", str(caught.exception))
        at_limit = edit_session(save(parsed, questions, s),
                                lambda ses: ses["retry_history"].update({"4": items[:coach.MAX_ATTEMPTS_PER_QUESTION]}))
        self.assertEqual(len(load(at_limit)[2]["retry_history"][4]), coach.MAX_ATTEMPTS_PER_QUESTION)

    def test_file_size_limit(self):
        text = fixture() + "\n" + "가" * (coach.MAX_REPORT_BYTES // 3 + 10)
        with self.assertRaises(ValueError) as caught:
            coach.parse_report(text)
        self.assertIn("5MB 초과", str(caught.exception))


class DamagedEvaluationTest(unittest.TestCase):

    def damaged(self):
        return edit_session(fixture(), lambda ses: ses["evaluation"]["panel"].pop())

    def test_partial_restore(self):
        _, _, ok = load(fixture())
        parsed, questions, s = load(self.damaged())
        self.assertIsNone(s["evaluation"])                                   # 0점으로 채우지 않음
        self.assertEqual(s["messages"], ok["messages"])                      # 질문 · 답은 그대로
        self.assertEqual(s["retries"], {})
        self.assertEqual(s["retry_history"], ok["retry_history"])            # 재도전 기록도 보존
        self.assertIn("panel_role_missing:recruiter", s["problems"]["evaluation"])
        self.assertEqual(len(s["evaluation_unreadable"]), 1)
        self.assertEqual((s["clue_round"], s["clue_set"]), (1, None))

    def test_other_damages(self):
        for name, change in [
            ("번호 오류", lambda ses: ses["evaluation"]["answers"][0].update(no=0)),
            ("타입 오류", lambda ses: ses["evaluation"]["answers"][1].update(specific="3")),
            ("항목 누락", lambda ses: ses["evaluation"]["answers"][2].pop("evidence")),
        ]:
            with self.subTest(name=name):
                self.assertIsNone(load(edit_session(fixture(), change))[2]["evaluation"])

    def test_out_of_range_clamped(self):
        def change(ses):
            ses["evaluation"]["panel"][0]["score"] = 12
            ses["evaluation"]["answers"][0]["specific"] = 9
            ses["retry_history"]["2"][0]["relevance"] = -3
        _, _, s = load(edit_session(fixture(), change))
        self.assertEqual(s["evaluation"]["panel"][0]["score"], 10)
        self.assertEqual(s["evaluation"]["answers"][0]["scores"]["specific"], 5)
        self.assertEqual(s["retry_history"][2][0]["scores"]["relevance"], 0)
        self.assertEqual(s["problems"], {"evaluation": [], "retry_codes": [], "retry_unreadable": 0})

    def test_damaged_original_kept_after_re_evaluation(self):
        """다시 평가받은 뒤 저장해도 읽지 못한 최초 평가 원본이 남는다."""
        damaged = self.damaged()
        raw = data_of(damaged)["session"]["evaluation"]
        parsed, questions, s = load(damaged)
        s["evaluation"] = coach.checked_evaluation(data_of(fixture())["session"]["evaluation"], questions)  # 다시 평가받음
        s["retries"] = coach.reflected_retries(s["evaluation"], s["retry_history"])
        _, (_, _, again) = round_trip(save(parsed, questions, s))
        self.assertIsNotNone(again["evaluation"])
        self.assertEqual(again["evaluation_unreadable"], [raw])


class DamagedRetryTest(unittest.TestCase):

    def damaged(self):
        def change(ses):
            ses["retry_history"]["2"][1]["specific"] = "4"          # 타입 오류
            ses["retry_history"]["3"].append({"answer": "점수 없는 기록"})
        return edit_session(fixture(), change)

    def test_preserved_and_excluded(self):
        _, _, ok = load(fixture())
        _, _, s = load(self.damaged())
        self.assertEqual([a["attempt_id"] for a in s["retry_history"][2]], ["q2-a1"])
        self.assertEqual([(u["attempt_id"], u["raw"]["answer"]) for u in s["retry_unreadable"][2]],
                         [("q2-a2", ok["retry_history"][2][1]["answer"])])
        self.assertEqual(s["retry_unreadable"][3][0]["attempt_id"], "q3-a2")
        self.assertEqual(s["problems"]["retry_unreadable"], 2)
        self.assertIn("score_type:specific", s["problems"]["retry_codes"])
        self.assertEqual(s["retry_counts"], {2: 1, 3: 1})                   # 읽지 못한 기록은 세지 않음

    def test_resave_keeps_unreadable_and_ids(self):
        parsed, questions, s = load(self.damaged())
        new = add_attempt(s, 2, 5, "새 재도전")
        self.assertEqual(new["attempt_id"], "q2-a3")                        # 읽지 못한 q2-a2 와 겹치지 않음
        again_text, (_, _, again) = round_trip(save(parsed, questions, s))
        self.assertEqual(again["retry_unreadable"], s["retry_unreadable"])
        self.assertEqual([a["attempt_id"] for a in again["retry_history"][2]], ["q2-a1", "q2-a3"])
        self.assertEqual(again["problems"]["retry_codes"], [])              # 지난번에 남긴 것은 새 문제로 세지 않음
        self.assertEqual(again["problems"]["retry_unreadable"], 2)
        _, (_, _, third) = round_trip(again_text)
        self.assertEqual(third["retry_unreadable"], s["retry_unreadable"])  # 몇 번 다시 저장해도 그대로


class AttemptIdTest(unittest.TestCase):

    def test_stable_for_v1(self):
        first, second = load(fixture())[2], load(fixture())[2]
        ids = {no: [a["attempt_id"] for a in h] for no, h in first["retry_history"].items()}
        self.assertEqual(ids, {2: ["q2-a1", "q2-a2"], 3: ["q3-a1"]})
        self.assertEqual(ids, {no: [a["attempt_id"] for a in h] for no, h in second["retry_history"].items()})

    def test_given_ids_kept_and_duplicates_fixed(self):
        def change(ses):
            ses["retry_history"]["2"][0]["attempt_id"] = "q2-a7"
            ses["retry_history"]["2"][1]["attempt_id"] = "q2-a7"            # 겹침 → 새 번호
            ses["retry_history"]["3"][0]["attempt_id"] = "q9-a1"            # 다른 질문 ID → 순서 ID
        _, _, s = load(edit_session(fixture(), change))
        self.assertEqual([a["attempt_id"] for a in s["retry_history"][2]], ["q2-a7", "q2-a2"])
        self.assertEqual([a["attempt_id"] for a in s["retry_history"][3]], ["q3-a1"])
        self.assertEqual(coach.next_attempt_id(2, s["retry_history"][2]), "q2-a8")


class CompatibilityTest(unittest.TestCase):

    def test_new_file_keeps_v1_fields(self):
        """새 파일도 version 1 · 기존 칸을 그대로 가진다 (옛 앱은 모르는 칸을 무시하고 읽는다)."""
        parsed, questions, s = load(fixture())
        add_attempt(s, 2, 5, "20점")
        data = data_of(save(parsed, questions, s, latest={4: "최신"}))
        self.assertEqual((data["version"], data["revision"]), (1, 2))
        session = data["session"]
        for key in ("messages", "evaluation", "retries", "retry_history", "retry_counts", "clues"):
            self.assertIn(key, session)
        self.assertEqual(session["retry_counts"], {"2": 3, "3": 1})
        old_view = coach.summarize_retry(session["retry_history"]["2"][-1])  # 옛 앱의 읽기 방식
        self.assertEqual(old_view["score"], 20)

    def test_no_session_reports_unchanged(self):
        parsed = coach.parse_report((FIXTURES / "partial" / "v1_legacy_no_session.md").read_text(encoding="utf-8"))
        self.assertIsNone(parsed["session"])


class StaticTest(unittest.TestCase):

    def test_memo_review_linked_by_id(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('state.memo_reviews[result_key] = attempt["attempt_id"]', source)
        tree = ast.parse(source)
        show = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "show_review_result")
        self.assertIn("a.get('attempt_id') == review_id", ast.unparse(show))
        self.assertNotIn("summarize_evaluation", source)
        self.assertNotIn("summarize_retry", source)


class AppRestoreTest(AppErrorCase):
    """화면: 손상된 평가가 든 기록을 열면 질문 · 답만 불러오고 다시 평가받을 수 있다 (개발용 모의 데이터 길로 연다)."""

    def setUp(self):
        super().setUp()
        self.env = mock.patch.dict(os.environ, {"DEV_MOCK": "1"})
        self.env.start()
        self.real_load_mock = coach.load_mock

    def tearDown(self):
        coach.load_mock = self.real_load_mock
        self.env.stop()
        super().tearDown()

    def open_mock(self, change, script):
        data = self.real_load_mock()
        change(data["session"])
        coach.load_mock = lambda: copy.deepcopy(data)
        self.open_app(script)
        self.at.button(key="title_new").click().run()
        self.click("모의 데이터로 열기")
        self.assertEqual(self.at.session_state["stage"], "done")

    def test_damaged_evaluation_then_re_evaluate(self):
        self.open_mock(lambda ses: ses["evaluation"]["panel"].pop(), {"evaluation": [response("evaluation", "perfect")]})
        self.assertIsNone(self.at.session_state["evaluation"])
        self.assertIn("평가 데이터를 읽지 못해 질문과 답변만 불러왔어요. 다시 평가받을 수 있어요.",
                      " ".join(w.value for w in self.at.warning))
        [event] = self.events()
        self.assertEqual((event["error_type"], event["source"], event["status"]), ("restore_validation", "restore", "failed"))
        self.assertIn("panel_role_missing:recruiter", event["codes"])
        self.assertEqual(len(self.at.session_state["evaluation_unreadable"]), 1)
        self.click("위원 4명에게 평가받기")
        self.assertIsNotNone(self.at.session_state["evaluation"])
        self.assertEqual(len(self.at.session_state["evaluation_unreadable"]), 1)  # 원본은 다음 저장까지 남는다

    def test_damaged_retry_warning(self):
        def change(ses):
            ses["retry_history"] = {"2": [{"answer": "점수 없는 기록"}]}
        self.open_mock(change, {})
        self.assertIsNotNone(self.at.session_state["evaluation"])
        self.assertIn("일부 재도전 평가를 읽지 못했어요. 답변은 보존했지만 해당 점수는 반영하지 않았어요.",
                      " ".join(w.value for w in self.at.warning))
        self.assertEqual(self.at.session_state["retry_unreadable"][2][0]["raw"], {"answer": "점수 없는 기록"})
        self.assertNotIn("점수 없는 기록", self.log.getvalue())               # 답 글은 오류 기록에 없음

    def test_latest_unscored_refilled(self):
        self.open_mock(lambda ses: ses.update(latest_unscored={"1": {"answer": "지난번에 채점 못 받은 답"}}), {})
        self.assertEqual(self.at.session_state["retry_pending"], {1: "지난번에 채점 못 받은 답"})
        self.at.selectbox(key="retry_no").set_value(1).run()
        self.assertEqual(self.at.text_area(key="retry_answer_1").value, "지난번에 채점 못 받은 답")


if __name__ == "__main__":
    unittest.main()
