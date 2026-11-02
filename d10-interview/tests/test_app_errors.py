# AI 호출 실패의 화면 · 오류 기록 연결 테스트 (E-2). Streamlit AppTest + 가짜 AI. 외부 API 호출 없음.
# 기록은 error_log 를 메모리 버퍼로 설정해 확인한다 (stderr · 프로젝트 logs/ 를 쓰지 않음).
# 실행: d10-interview 폴더에서  python -m unittest discover tests
import ast
import copy
import io
import json
import os
import re
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

import coach
import error_log
import llm
from llm import LLMError
from fake_llm import FakeAskJson, response, sequence

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app.py")
PROFILE = {"f_name": "김예시", "f_company": "클래스로", "f_company_desc": "IT, 헬스케어 진단 서비스",
           "f_experience": "대학 팀 프로젝트에서 중고 거래 앱의 UX/UI 디자인을 맡아 사용자 인터뷰로 결제 이탈 원인을 찾았습니다."}
ANSWER = "자기소개 답: 사용자 인터뷰로 결제 이탈 원인을 찾았습니다."
PRIVATE = ["김예시", "클래스로", ANSWER, "결제 이탈", "OPENAI_API_KEY", "test-key"]


class AppErrorCase(unittest.TestCase):

    def setUp(self):
        self.real_ask_json = llm.ask_json
        self.real_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = ""
        self.log = io.StringIO()
        error_log.configure(force=True, file_enabled=False, stream=self.log)

    def tearDown(self):
        llm.ask_json = self.real_ask_json
        if self.real_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self.real_key
        error_log.configure(force=True, file_enabled=False)

    def open_app(self, script):
        llm.ask_json = FakeAskJson(script)
        self.at = AppTest.from_file(APP, default_timeout=60)
        self.at.run()
        return self.at

    def events(self) -> list[dict]:
        return [json.loads(l) for l in self.log.getvalue().splitlines() if l.strip()]

    def no_exception(self):
        self.assertEqual([e.value for e in self.at.exception], [])

    def click(self, label):
        [b for b in self.at.button if label in b.label][0].click().run()
        self.no_exception()

    def start_interview(self):
        """시작 화면 → [+ 새 면접 시작] → 면접 정보 설정 (회사 · 내 경험은 선택이지만 기록 검사용으로 채운다) → 면접 시작."""
        self.at.button(key="title_new").click().run()
        self.at.text_input(key="f_company").input(PROFILE["f_company"])
        self.at.text_input(key="f_company_desc").input(PROFILE["f_company_desc"])
        self.at.text_area(key="f_experience").input(PROFILE["f_experience"])
        self.at.button(key="setup_start").click().run()
        self.no_exception()

    def to_retry(self):
        """평가 뒤 [평가 확인하기] → 면접 상세의 LNB '재도전 (전체)'."""
        if self.at.session_state["page"] == "interview":
            self.click("평가 확인하기")
        self.at.segmented_control(key="lnb").set_value(":material/replay: 재도전 (전체)").run()
        self.no_exception()

    def finish_interview(self):
        for i in range(6):
            self.at.chat_input[0].set_value(f"답 {i}").run()
        self.assertEqual(self.at.session_state["stage"], "done")

    def assert_event(self, event, error_type, source, **meta):
        self.assertEqual((event["error_type"], event["source"], event["attempt"], event["status"]),
                         (error_type, source, 1, "failed"))
        self.assertIn(event["error_type"], error_log.ERROR_TYPES)
        self.assertIn(event["source"], error_log.SOURCES)
        self.assertEqual(event["meta"].get("model"), os.getenv("OPENAI_MODEL") or llm.DEFAULT_MODEL)
        for k, v in meta.items():
            self.assertEqual(event["meta"].get(k), v)
        self.assertEqual(event["dropped"], 0)

    def assert_no_private_text(self):
        text = self.log.getvalue()
        for s in PRIVATE:
            self.assertNotIn(s, text)


class InterviewerErrorTest(AppErrorCase):

    def test_timeout_logged_message_unchanged(self):
        err = LLMError("OpenAI 에 연결하지 못했어요. 인터넷 연결을 확인해 주세요.", "api_timeout", None, "APITimeoutError")
        self.open_app({"interviewer": [err]})
        self.start_interview()
        self.at.chat_input[0].set_value(ANSWER).run()
        self.no_exception()
        self.assertIn("OpenAI 에 연결하지 못했어요", " ".join(e.value for e in self.at.error))
        self.assertNotIn("api_timeout", " ".join(e.value for e in self.at.error))  # 개발자 코드는 화면에 없음
        [event] = self.events()
        self.assert_event(event, "api_timeout", "interviewer", exception="APITimeoutError")
        self.assertEqual(event["session_id"], self.at.session_state["error_session_id"])
        self.assert_no_private_text()

    def test_missing_key_code(self):
        err = LLMError("API 키가 없어요. .env 에 OPENAI_API_KEY 를 넣어 주세요.", "api_auth", code="missing_api_key")
        self.open_app({"interviewer": [err]})
        self.start_interview()
        self.at.chat_input[0].set_value(ANSWER).run()
        [event] = self.events()
        self.assert_event(event, "api_auth", "interviewer")
        self.assertEqual(event["codes"], ["missing_api_key"])
        self.assertNotIn("http_status", event["meta"])  # 값이 없는 칸은 넘기지 않는다


class CallAiErrorTest(AppErrorCase):
    """call_ai 를 거치는 호출 (평가 · 재도전 · 전략 · 형광펜 · 마지막 질문) 이 같은 구조로 기록된다."""

    def test_evaluation_server_error(self):
        err = LLMError("AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요.", "api_server", 503, "InternalServerError")
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [err]})
        self.start_interview()
        self.finish_interview()
        self.click("평가 받기")
        self.assertIsNone(self.at.session_state["evaluation"])
        [event] = self.events()
        self.assert_event(event, "api_server", "evaluation", http_status=503, exception="InternalServerError")
        self.assert_no_private_text()

    def test_retry_and_strategy_errors_share_session(self):
        retry_err = LLMError("요청이 너무 많아요. 잠시 뒤 다시 시도해 주세요.", "api_rate_limit", 429, "RateLimitError")
        strat_err = LLMError("AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요.", "api_auth", 403, "PermissionDeniedError")
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")],
                       "retry": [retry_err], "strategy": [strat_err]})
        self.start_interview()
        self.finish_interview()
        self.click("평가 받기")
        self.to_retry()
        no = self.at.selectbox(key="retry_no").value
        self.at.text_area(key=f"retry_answer_{no}").input("다시 쓴 답")
        self.click("다시 채점")
        self.assertEqual(self.at.session_state["retry_history"], {})  # 실패한 채점은 기록되지 않음
        self.click("전략 가이드 받기")
        retry_event, strategy_event = self.events()
        self.assert_event(retry_event, "api_rate_limit", "retry", http_status=429)
        self.assert_event(strategy_event, "api_auth", "strategy", http_status=403)
        self.assertEqual(retry_event["session_id"], strategy_event["session_id"])  # 같은 면접 세션 = 같은 ID
        self.assertNotEqual(retry_event["error_id"], strategy_event["error_id"])
        self.assert_no_private_text()


class SessionIdTest(AppErrorCase):

    def test_created_once_per_session(self):
        """같은 면접 세션의 실패 두 건: 세션 ID 는 한 번만 만들고 같은 값을 쓴다."""
        from unittest import mock
        err = LLMError("AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요.", "api_other", 400, "BadRequestError")
        with mock.patch.object(error_log, "new_session_id", wraps=error_log.new_session_id) as maker:
            self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [err, err]})
            self.start_interview()
            self.finish_interview()
            self.click("평가 받기")
            self.click("평가 받기")
        first, second = self.events()
        self.assertEqual(first["session_id"], second["session_id"])
        self.assertEqual(maker.call_count, 1)


class LoggingFailureTest(AppErrorCase):

    def test_broken_log_stream_does_not_break_app(self):
        class Broken(io.StringIO):
            def write(self, s):
                raise OSError("disk full")

        error_log.configure(force=True, file_enabled=False, stream=Broken())
        err = LLMError("AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요.", "api_other", 400, "BadRequestError")
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [err, response("evaluation", "perfect")]})
        self.start_interview()
        self.finish_interview()
        self.click("평가 받기")          # 실패 + 기록 실패
        self.assertIn("AI 응답을 받지 못했어요", " ".join(e.value for e in self.at.error))
        self.click("평가 받기")          # 다시 누르면 정상 평가
        self.assertEqual(self.at.session_state["evaluation"]["answers"][0]["score"], 20)


class ValidationFailureTest(AppErrorCase):
    """E-3: 검증을 통과하지 못한 평가 · 재도전 채점은 저장하지 않고, 기존 데이터를 그대로 둔다."""

    MSG_EVAL = "평가 결과를 확인하지 못했어요. 잠시 뒤 다시 평가받아 주세요."
    MSG_RETRY = "채점 결과를 확인하지 못했어요. 잠시 뒤 다시 채점해 주세요."

    def errors(self):
        return " ".join(e.value for e in self.at.error)

    def test_invalid_evaluation_not_saved_then_retry_works(self):
        self.open_app({"interviewer": sequence("probe_one_follow_up"),
                       "evaluation": [response("evaluation", "missing_role"), response("evaluation", "missing_role"),
                                      response("evaluation", "mixed")]})
        self.start_interview()
        self.finish_interview()
        self.click("평가 받기")
        self.assertIsNone(self.at.session_state["evaluation"])  # 0점 채운 평가가 저장되지 않음
        self.assertIn(self.MSG_EVAL, self.errors())
        self.assertTrue([b for b in self.at.button if "평가 받기" in b.label])  # 다시 평가받기 버튼이 남음
        first, event = self.events()  # E-4A: 자동 재시도 1회 뒤 최종 실패 (1회차 retrying · 2회차 failed)
        self.assertEqual((first["attempt"], first["status"]), (1, "retrying"))
        self.assertEqual((event["error_type"], event["source"], event["attempt"], event["status"]),
                         ("eval_validation", "evaluation", 2, "failed"))
        self.assertEqual(event["meta"]["item_count"], len(event["codes"]))
        self.assertIn("panel_role_missing:recruiter", event["codes"])
        self.assertNotIn("question_no", event["meta"])
        self.assert_no_private_text()

        self.click("평가 받기")  # 다시 누르면 정상 평가 저장
        ev = self.at.session_state["evaluation"]
        self.assertEqual([m["role"] for m in ev["panel"]], coach.PANEL_ROLES)
        self.assertEqual(len(self.events()), 2)

    def test_invalid_retry_keeps_scores_history_and_count(self):
        wrong_type = dict(response("retry", "improved"), specific="4", relevance=5.0)
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")],
                       "retry": [response("retry", "improved"), response("retry", "out_of_range")]})
        fake = llm.ask_json
        self.start_interview()
        self.finish_interview()
        self.click("평가 받기")
        self.to_retry()
        no = self.at.selectbox(key="retry_no").value
        self.at.text_area(key=f"retry_answer_{no}").input("다시 쓴 답 하나")
        self.click("다시 채점")                       # 정상 채점 → 기록 1개 · 최고 점수 반영
        snapshot = {k: copy.deepcopy(self.at.session_state[k])
                    for k in ("evaluation", "retry_history", "retries", "retry_counts")}
        self.assertEqual(snapshot["retry_counts"], {no: 1})

        self.at.selectbox(key="retry_no").set_value(no).run()
        self.at.text_area(key=f"retry_answer_{no}").input("다시 쓴 답 둘").run()
        # 가짜 AI 는 strict 스키마를 흉내 내 타입 오류 응답을 막는다 → 이 한 번만 스키마 검사 없이 돌려준다 (방어 경로 시험)
        llm.ask_json = lambda instructions, user_input, schema, name: copy.deepcopy(wrong_type)
        self.click("다시 채점")                       # 점수 타입 오류 ("4", 5.0) → 자동 재시도도 같은 오류 → 저장하지 않음
        llm.ask_json = fake
        self.assertIn(self.MSG_RETRY, self.errors())
        for key, before in snapshot.items():
            self.assertEqual(self.at.session_state[key], before, key)
        self.assertEqual(self.at.text_area(key=f"retry_answer_{no}").value, "다시 쓴 답 둘")  # 쓴 글은 입력 칸에 남음
        first, event = self.events()
        self.assertEqual((first["attempt"], first["status"]), (1, "retrying"))
        self.assertEqual((event["error_type"], event["source"], event["attempt"], event["status"]),
                         ("eval_validation", "retry", 2, "failed"))
        self.assertEqual((event["meta"]["question_no"], event["meta"]["item_count"]), (no, 2))
        self.assertEqual(event["codes"], ["score_type:specific", "score_type:relevance"])
        self.assertNotIn("다시 쓴 답", self.log.getvalue())
        self.assert_no_private_text()

        self.click("다시 채점")                       # 범위 밖 점수 (7, -1) → 5, 0 으로 잘라 저장 (실패 아님)
        attempt = self.at.session_state["retry_history"][no][-1]
        self.assertEqual(attempt["scores"], {"specific": 5, "relevance": 0, "structure": 5, "evidence": 5})
        self.assertEqual(attempt["score"], 15)
        self.assertEqual(self.at.session_state["retry_counts"], {no: 2})
        self.assertEqual(len(self.events()), 2)          # 자르기는 오류 기록을 남기지 않는다 (보정은 정상 처리)


class PerfectHintsDisplayTest(AppErrorCase):

    def test_checks_two_then_more(self):
        """확인할 것: 저장은 원본 전체, 화면은 기본 2개 + [더 보기] (D6)."""
        raw = response("evaluation", "perfect")
        raw["answers"][0]["check"] = ["확인 가", "확인 나", "확인 다", "확인 라"]
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [raw]})
        self.start_interview()
        self.finish_interview()
        self.click("평가 받기")
        self.assertEqual(self.at.session_state["evaluation"]["answers"][0]["check"],
                         ["확인 가", "확인 나", "확인 다", "확인 라"])
        self.to_retry()  # 만점 힌트는 재도전 (전체) 의 역전의 실마리 자리
        self.click("힌트 확인하기")
        [more] = [e for e in self.at.expander if e.label.startswith("더 보기")]
        self.assertEqual(more.label, "더 보기 · 2개")
        inside = " ".join(m.value for m in more.markdown)
        self.assertIn("확인 다", inside)
        self.assertIn("확인 라", inside)
        self.assertNotIn("확인 가", inside)


class StaticCheckTest(unittest.TestCase):

    def test_ai_scores_go_through_validation(self):
        """AI 응답 저장 3곳은 검증 함수를 쓰고, 보정 함수(summarize_*)는 app.py 에서 쓰지 않는다."""
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("coach.checked_retry(raw)"), 1)  # 재도전 (전체) 한 곳 (암기 탭은 제외 기능이라 없앴다)
        self.assertEqual(source.count("coach.checked_evaluation(raw, state.questions)"), 1)
        self.assertNotIn("summarize_retry", source)
        self.assertNotIn("summarize_evaluation", source)

    def test_every_ai_call_name_is_a_source(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        names = set(re.findall(r'_SCHEMA,\s*"([a-z_]+)"', source))
        # 마지막에 할 질문은 MVP1 IA 에 없어 화면에서 뺐다 (기록 코드는 error_log 에 남는다)
        self.assertEqual(names, {"interviewer", "evaluation", "retry", "highlight", "strategy"})
        self.assertLessEqual(names, error_log.SOURCES)
        self.assertIn('"interviewer", container=live', source)  # 면접관도 run_ai 로 기록 (E-4A)
        self.assertIn("name, question_no)", source)              # call_ai → run_ai(..., name, question_no)

    def test_every_llm_kind_is_a_d9_code(self):
        tree = ast.parse((ROOT / "llm.py").read_text(encoding="utf-8"))
        kinds = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "LLMError" and len(node.args) >= 2:
                if isinstance(node.args[1], ast.Constant):
                    kinds.add(node.args[1].value)
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "kind" for t in node.targets):
                if isinstance(node.value, ast.Constant):
                    kinds.add(node.value.value)
        self.assertTrue(kinds)
        self.assertLessEqual(kinds, error_log.ERROR_TYPES)

    def test_session_id_not_kept_across_reset(self):
        """reset() 이 보존하는 키에 error_session_id 가 없다 → 새 면접 세션에서 새 ID."""
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        reset_body = source[source.index("def reset_app("):source.index("st.session_state.clear()")]
        self.assertNotIn("error_session_id", reset_body)


if __name__ == "__main__":
    unittest.main()
