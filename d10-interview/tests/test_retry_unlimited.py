# 재도전 횟수 제한 해제 테스트 (E-4B). Streamlit AppTest + 가짜 AI. 외부 API 호출 없음.
# 실행: d10-interview 폴더에서  python -m unittest discover tests
import ast
import unittest
from datetime import date

import coach
from fake_llm import response, sequence
from test_app_errors import ROOT
from test_app_recovery import RecoveryCase, wrong_retry

DUPLICATE_MESSAGE = "이미 채점받은 답변이에요. 답변을 수정하면 다시 채점받을 수 있어요."


def scored(specific, relevance, structure, evidence, weak="약한 점"):
    return {"specific": specific, "relevance": relevance, "structure": structure, "evidence": evidence, "weak": weak}


class RetryCase(RecoveryCase):

    def start(self, retries):
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")],
                       "retry": retries})
        self.start_interview()
        self.finish_interview()
        self.click("위원 4명에게 평가받기")

    def submit(self, no, text):
        self.at.selectbox(key="retry_no").set_value(no).run()
        self.at.text_area(key=f"retry_answer_{no}").input(text).run()
        self.click("다시 채점")

    def history(self, no):
        return self.at.session_state["retry_history"].get(no, [])

    def page_text(self):
        return " ".join(e.value for e in [*self.at.markdown, *self.at.caption, *self.at.info, *self.at.error]) + " ".join(
            str(o) for o in self.at.selectbox(key="retry_no").options) + " ".join(b.label for b in self.at.button)


class UnlimitedRetryTest(RetryCase):

    def test_same_question_six_times(self):
        scores = [(1, 1, 1, 1), (2, 2, 2, 2), (3, 3, 3, 3), (2, 2, 2, 2), (4, 4, 4, 4), (5, 5, 5, 5)]
        self.start([scored(*s) for s in scores])
        for i in range(6):
            self.submit(5, f"질문 5 재도전 {i + 1}")
        self.assertEqual([a["score"] for a in self.history(5)], [4, 8, 12, 8, 16, 20])
        self.assertEqual(self.at.session_state["retry_counts"], {5: 6})
        self.assertEqual(self.at.session_state["retries"][5]["answer"], "질문 5 재도전 6")  # 최고 점수 반영
        self.assertEqual(len(self.calls("retry")), 6)
        text = self.page_text()
        for removed in ("/3", "남은 기회", "모두 했어요", "모두 받았어요"):
            self.assertNotIn(removed, text)
        self.assertEqual(self.at.session_state["evaluation"]["answers"][4]["score"], 8)  # 최초 평가 그대로

    def test_alternating_questions(self):
        self.start([scored(3, 3, 3, 3)] * 8)
        for i in range(4):
            self.submit(2, f"질문 2 재도전 {i}")
            self.submit(3, f"질문 3 재도전 {i}")
        self.assertEqual((len(self.history(2)), len(self.history(3))), (4, 4))
        self.assertEqual(self.at.session_state["retry_counts"], {2: 4, 3: 4})
        self.assertEqual(self.history(2)[-1]["answer"], "질문 2 재도전 3")

    def test_failure_after_third_then_recover(self):
        self.start([scored(3, 3, 3, 3)] * 3 + [wrong_retry(), wrong_retry(), scored(4, 4, 4, 4)])
        for i in range(3):
            self.submit(5, f"재도전 {i}")
        self.submit(5, "네 번째 답")                                   # 자동 재시도까지 실패
        self.assertEqual(self.at.session_state["retry_counts"], {5: 3})  # 실패는 세지 않음
        self.assertEqual(len(self.history(5)), 3)
        self.assertEqual(self.at.session_state["retry_pending"], {5: "네 번째 답"})
        self.click("다시 채점")                                         # 같은 답 다시 제출 (실패한 답은 허용)
        self.assertEqual(self.at.session_state["retry_counts"], {5: 4})
        self.assertEqual(self.history(5)[-1]["answer"], "네 번째 답")
        self.assertEqual(self.at.session_state["retry_pending"], {})


class DuplicateAnswerTest(RetryCase):

    def test_same_answer_not_rescored(self):
        self.start([scored(3, 3, 3, 3), scored(5, 5, 5, 5)])
        self.submit(5, "고친 답 하나")
        before = {k: self.at.session_state[k] for k in ("retry_history", "retries", "retry_counts")}
        self.submit(5, "고친  답\n하나")                                # 띄어쓰기 · 줄바꿈만 다름 → 같은 답
        self.assertIn(DUPLICATE_MESSAGE, " ".join(i.value for i in self.at.info))
        self.assertEqual(len(self.calls("retry")), 1)                  # AI 를 부르지 않음
        for key, value in before.items():
            self.assertEqual(self.at.session_state[key], value, key)

    def test_interview_answer_counts_as_scored(self):
        """면접 때 답도 최초 평가로 채점된 답이다 → 그대로 다시 내면 부르지 않는다."""
        self.start([scored(5, 5, 5, 5)])
        original = coach.answer_text(self.at.session_state["messages"], 4)
        self.submit(5, original)
        self.assertIn(DUPLICATE_MESSAGE, " ".join(i.value for i in self.at.info))
        self.assertEqual(len(self.calls("retry")), 0)

    def test_other_question_not_compared(self):
        self.start([scored(3, 3, 3, 3), scored(3, 3, 3, 3)])
        self.submit(2, "같은 글")
        self.submit(3, "같은 글")                                       # 다른 질문이면 채점한다
        self.assertEqual(len(self.calls("retry")), 2)

    def test_failed_answer_can_be_resubmitted(self):
        self.start([wrong_retry(), wrong_retry(), scored(4, 4, 4, 4)])
        self.submit(5, "실패한 답")
        self.assertEqual(len(self.history(5)), 0)
        self.submit(5, "실패한 답")                                     # 채점에 실패한 답은 중복이 아님
        self.assertEqual(len(self.history(5)), 1)
        self.assertNotIn(DUPLICATE_MESSAGE, " ".join(i.value for i in self.at.info))


class BestScoreTest(RetryCase):

    def test_higher_tie_lower(self):
        self.start([scored(4, 4, 4, 4), scored(4, 4, 4, 4), scored(1, 1, 1, 1), scored(5, 5, 5, 4)])
        self.submit(5, "첫 16점")
        self.submit(5, "둘째 16점")                                     # 동점 → 먼저 받은 답 유지
        self.assertEqual(self.at.session_state["retries"][5]["answer"], "첫 16점")
        self.submit(5, "낮은 4점")                                      # 낮은 점수 → 그대로
        self.assertEqual(self.at.session_state["retries"][5]["answer"], "첫 16점")
        self.submit(5, "19점")                                          # 더 높음 → 갱신
        self.assertEqual(self.at.session_state["retries"][5]["score"], 19)
        self.assertEqual(self.at.session_state["evaluation"]["answers"][4]["score"], 8)  # 최초 점수 그대로


class CluesTest(RetryCase):

    def test_clue_button_after_many_retries(self):
        """실마리 질문을 4번 넘게 재도전해도 (점수가 그대로 낮으면) 버튼이 켜져 있고 남은 기회 표시가 없다."""
        self.start([scored(1, 1, 1, 1)] * 5)
        clue_nos = [c["no"] for c in self.at.session_state["clue_set"]]
        no = clue_nos[0]
        for i in range(5):
            self.submit(no, f"실마리 재도전 {i}")
        button = self.at.button(key=f"clue_retry_{no}")
        self.assertFalse(button.disabled)
        self.assertNotIn("남은 기회", button.label)
        clues = coach.pick_clues(self.at.session_state["evaluation"], retries=self.at.session_state["retries"],
                                 retry_counts=self.at.session_state["retry_counts"])
        self.assertIn(no, [c["no"] for c in clues])                    # 다시 찾아도 후보에서 빠지지 않음


class SaveRestoreTest(RetryCase):

    def test_six_retries_round_trip(self):
        scores = [(1, 1, 1, 1), (2, 2, 2, 2), (3, 3, 3, 3), (5, 5, 5, 4), (2, 2, 2, 2), (5, 5, 5, 4)]
        self.start([scored(*s) for s in scores])
        for i in range(6):
            self.submit(5, f"재도전 {i + 1}")
        ss = self.at.session_state
        text = coach.build_report(
            ss["profile"], ss["questions"], ss["evaluation"], ss["retries"], ss["messages"],
            None, None, None, 1, coach.load_precheck(), {}, "2026-11-02 12:00", date(2026, 11, 2),
            retry_counts=ss["retry_counts"], understanding=ss["understanding"], retry_history=ss["retry_history"],
            clue_set=ss["clue_set"], clue_round=1,
        )
        parsed = coach.parse_report(text)
        s = coach.rebuild_session(parsed["session"], ss["questions"])
        self.assertEqual([a["answer"] for a in s["retry_history"][5]], [f"재도전 {i + 1}" for i in range(6)])
        self.assertEqual(s["retries"][5]["answer"], "재도전 4")      # 19점 동점 → 먼저 받은 답 (6번째 아님)
        self.assertEqual(s["retry_counts"], {5: 6})
        self.assertEqual(coach.total_scores(s["evaluation"], s["retries"]),
                         coach.total_scores(ss["evaluation"], ss["retries"]))


class TrimLimitTest(unittest.TestCase):
    """E-5 로 넘긴 위험을 기록하는 테스트: 리포트에서 읽을 때 _trim 이 목록을 40개로 자른다 (이번에는 바꾸지 않음)."""

    def test_more_than_40_attempts_trimmed_on_read(self):
        session = {"retry_history": {"1": [{"answer": f"a{i}", **scored(1, 1, 1, 1)} for i in range(45)]}}
        self.assertEqual(len(coach._trim(session)["retry_history"]["1"]), coach.MAX_SESSION_MESSAGES)
        self.assertEqual(coach.MAX_SESSION_MESSAGES, 40)


class StaticTest(unittest.TestCase):

    def test_no_retry_limit_left(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        engine = (ROOT / "coach.py").read_text(encoding="utf-8")
        self.assertNotIn("MAX_RETRIES", app + engine)
        self.assertNotIn("남은 기회", app)
        self.assertFalse(hasattr(coach, "MAX_RETRIES"))

    def test_memo_review_not_limited(self):
        """암기 탭 재도전 검토 (대화 상자라 화면 테스트 대신): 횟수 비교 분기가 없고, 성공 시 횟수를 1 늘린다."""
        tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
        dialog = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "script_dialog")
        source = ast.unparse(dialog)
        self.assertNotIn("retry_counts.get(no, 0) >=", source)
        self.assertIn("graded_answers(no)", source)                    # 같은 대본 다시 채점 안 함 (기존)
        store = next(n for n in ast.walk(dialog) if isinstance(n, ast.FunctionDef) and n.name == "store")
        self.assertIn("record_retry(no, attempt", ast.unparse(store))
        record = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "record_retry")
        self.assertIn("state.retry_counts[no] = len(history)", ast.unparse(record))  # 횟수 = 기록 개수 (E-5)


if __name__ == "__main__":
    unittest.main()
