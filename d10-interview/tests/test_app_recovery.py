# AI 실패 뒤 답변 보존 · 자동 재시도 테스트 (E-4A). Streamlit AppTest + 가짜 AI. 외부 API 호출 없음.
# HTTP 요청 수 테스트는 실제 OpenAI SDK 에 가짜 전송 계층(MockTransport)을 붙여 SDK 재시도까지 센다 (네트워크 없음).
# 실행: d10-interview 폴더에서  python -m unittest discover tests
import ast
import functools
import os
import unittest

import httpx2
import openai

import coach
import llm
from fake_llm import FakeAskJson, response, sequence
from llm import LLMError
from test_app_errors import ANSWER, ROOT, AppErrorCase

PENDING_MESSAGE = "답변을 보관했어요. 다시 보내거나 수정할 수 있어요."
RETRY_PENDING_MESSAGE = "채점하지 못한 답변이 남아 있어요. 다시 채점할 수 있어요."
MSG_SERVER = "AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요."
MSG_PARSE = "AI 응답을 읽지 못했어요. 다시 시도해 주세요."


def err(kind, status=None, exception=None, code=None, message=MSG_SERVER):
    return LLMError(message, kind, status, exception, code)


PARSE = err("response_parse", code="json_decode", message=MSG_PARSE)


class Raw(dict):
    """가짜 AI 가 스키마 검사 없이 돌려줄 응답 (strict 스키마를 지나온 뒤 E-3 검증에 걸리는 응답 흉내)."""


class LooseFake(FakeAskJson):
    def __call__(self, instructions, user_input, schema, name):
        queue = self.queues.get(name)
        if queue and isinstance(queue[0], Raw):
            self.calls.append({"name": name, "instructions": instructions, "user_input": user_input})
            return dict(queue.pop(0))
        return super().__call__(instructions, user_input, schema, name)


def wrong_retry():
    return Raw(response("retry", "improved"), specific="4")  # 점수 타입 오류 → eval_validation


class RecoveryCase(AppErrorCase):

    def open_app(self, script):
        llm.ask_json = self.fake = LooseFake(script)
        from streamlit.testing.v1 import AppTest
        self.at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
        self.at.run()
        return self.at

    def calls(self, name):
        return [c for c in self.fake.calls if c["name"] == name]

    def user_messages(self):
        return [m["content"] for m in self.at.session_state["messages"] if m["role"] == "user"]

    def statuses(self):
        return [(e["error_type"], e["source"], e["attempt"], e["status"]) for e in self.events()]


class InterviewerRecoveryTest(RecoveryCase):

    def fail_first_answer(self, *errors):
        self.open_app({"interviewer": [*errors, *sequence("probe_one_follow_up")]})
        self.start_interview()
        self.at.chat_input[0].set_value(ANSWER).run()
        self.no_exception()

    def test_answer_kept_after_failure(self):
        self.fail_first_answer(err("api_server", 503, "InternalServerError"))
        pending = self.at.session_state["pending_answer"]
        self.assertEqual((pending["text"], pending["q"], pending["follow_ups"]), (ANSWER, 0, 0))
        self.assertEqual(self.user_messages(), [])                  # 대화 기록에는 아직 없음
        self.assertEqual(self.at.session_state["q_index"], 0)       # 질문이 넘어가지 않음
        self.assertIn(MSG_SERVER, " ".join(e.value for e in self.at.error))
        self.assertIn(PENDING_MESSAGE, " ".join(i.value for i in self.at.info))
        self.assertIn(ANSWER, " ".join(m.value for m in self.at.markdown))  # 화면에서 보관한 답을 볼 수 있음
        self.assertEqual(len(self.calls("interviewer")), 1)         # 서버 오류는 앱이 다시 부르지 않음 (SDK 몫)
        self.assertEqual(self.statuses(), [("api_server", "interviewer", 1, "failed")])
        self.assert_no_private_text()

        self.at.run()                                               # 그냥 다시 그려도 보관 · 호출 수 그대로
        self.assertEqual(self.at.session_state["pending_answer"]["text"], ANSWER)
        self.assertEqual(len(self.calls("interviewer")), 1)

    def test_resend_same_answer_once(self):
        self.fail_first_answer(err("api_timeout", None, "APITimeoutError"))
        self.click("다시 시도")
        self.assertEqual(self.user_messages(), [ANSWER])            # 한 번만 들어감
        self.assertNotIn("pending_answer", self.at.session_state)
        self.assertEqual(len(self.calls("interviewer")), 2)
        sent = self.calls("interviewer")[1]["user_input"]
        self.assertEqual(sent.count(ANSWER), 1)                     # 면접관에게도 같은 답을 한 번만 보냄
        self.at.run()
        self.assertEqual(self.user_messages(), [ANSWER])            # 다시 그려도 중복 없음
        self.assertEqual(len(self.calls("interviewer")), 2)

    def test_edit_then_send(self):
        self.fail_first_answer(err("api_server", 500, "InternalServerError"))
        self.click("답변 수정")
        box = self.at.text_area(key="pending_edit_text")
        self.assertEqual(box.value, ANSWER)                         # 보관한 답으로 채운 수정 칸
        box.input("고친 답입니다.").run()
        self.assertEqual(self.at.session_state["pending_answer"]["text"], ANSWER)  # 보내기 전에는 그대로
        self.click("수정 취소")
        self.assertEqual(self.at.session_state["pending_answer"]["text"], ANSWER)  # 취소해도 보관한 답 유지
        self.click("답변 수정")
        self.at.text_area(key="pending_edit_text").input("고친 답입니다.").run()
        self.click("수정한 답변 보내기")
        self.assertEqual(self.user_messages(), ["고친 답입니다."])
        self.assertNotIn("pending_answer", self.at.session_state)

    def test_new_chat_input_does_not_overwrite(self):
        """보관한 답이 있을 때 입력창에 새로 쓴 글: 바로 보내지 않고 수정 칸에 옮긴다 (보관한 답은 그대로)."""
        self.fail_first_answer(err("api_server", 500, "InternalServerError"))
        self.at.chat_input[0].set_value("새로 쓴 답").run()
        self.no_exception()
        self.assertEqual(self.at.session_state["pending_answer"]["text"], ANSWER)
        self.assertEqual(self.at.text_area(key="pending_edit_text").value, "새로 쓴 답")
        self.assertEqual(len(self.calls("interviewer")), 1)         # AI 를 부르지 않음
        self.assertEqual(self.user_messages(), [])

    def test_empty_edit_not_sent(self):
        self.fail_first_answer(err("api_server", 500, "InternalServerError"))
        self.click("답변 수정")
        self.at.text_area(key="pending_edit_text").input("   ").run()
        self.click("수정한 답변 보내기")
        self.assertEqual(self.at.session_state["pending_answer"]["text"], ANSWER)
        self.assertEqual(len(self.calls("interviewer")), 1)

    def test_parse_error_auto_retry_recovers(self):
        self.fail_first_answer(PARSE)
        self.assertEqual(self.user_messages(), [ANSWER])
        self.assertNotIn("pending_answer", self.at.session_state)
        self.assertEqual([e.value for e in self.at.error], [])
        self.assertEqual(self.statuses(), [("response_parse", "interviewer", 1, "retrying"),
                                           ("response_parse", "interviewer", 2, "recovered")])
        self.assertEqual(self.events()[0]["codes"], ["json_decode"])

    def test_parse_error_twice_keeps_answer(self):
        self.fail_first_answer(PARSE, PARSE)
        self.assertEqual(self.at.session_state["pending_answer"]["text"], ANSWER)
        self.assertEqual(self.statuses(), [("response_parse", "interviewer", 1, "retrying"),
                                           ("response_parse", "interviewer", 2, "failed")])
        self.assertEqual(len(self.calls("interviewer")), 2)

    def test_changed_error_type_stops(self):
        """재시도에서 오류 유형이 바뀌면 (형식 오류 → 시간 초과) 더 부르지 않는다: 앱 호출 2번."""
        self.fail_first_answer(PARSE, err("api_timeout", None, "APITimeoutError"))
        self.assertEqual(self.statuses(), [("response_parse", "interviewer", 1, "retrying"),
                                           ("api_timeout", "interviewer", 2, "failed")])
        self.assertEqual(len(self.calls("interviewer")), 2)
        self.assertEqual(self.at.session_state["pending_answer"]["text"], ANSWER)


class EvaluationRecoveryTest(RecoveryCase):

    def finish(self, evaluations):
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": evaluations})
        self.start_interview()
        self.finish_interview()

    def test_validation_auto_retry_recovers(self):
        self.finish([response("evaluation", "missing_role"), response("evaluation", "mixed")])
        self.click("평가 받기")
        self.assertIsNotNone(self.at.session_state["evaluation"])
        self.assertEqual([e.value for e in self.at.error], [])
        self.assertEqual(self.statuses(), [("eval_validation", "evaluation", 1, "retrying"),
                                           ("eval_validation", "evaluation", 2, "recovered")])
        self.assertEqual(len(self.calls("evaluation")), 2)

    def test_parse_auto_retry_recovers(self):
        self.finish([PARSE, response("evaluation", "perfect")])
        self.click("평가 받기")
        self.assertEqual(self.at.session_state["evaluation"]["answers"][0]["score"], 20)
        self.assertEqual([s[3] for s in self.statuses()], ["retrying", "recovered"])

    def test_final_failure_keeps_button(self):
        self.finish([response("evaluation", "missing_role"), response("evaluation", "zero_based_numbers"),
                     response("evaluation", "mixed")])
        self.click("평가 받기")
        self.assertIsNone(self.at.session_state["evaluation"])
        self.assertIn("평가 결과를 확인하지 못했어요", " ".join(e.value for e in self.at.error))
        first, second = self.events()
        self.assertEqual((first["attempt"], first["status"]), (1, "retrying"))
        self.assertEqual((second["attempt"], second["status"]), (2, "failed"))
        self.assertIn("panel_role_missing:recruiter", first["codes"])
        self.assertIn("answer_no_range:answers[0]=0", second["codes"])
        self.click("평가 받기")                           # 다시 평가받기 가능
        self.assertIsNotNone(self.at.session_state["evaluation"])
        self.assertEqual(len(self.calls("evaluation")), 3)
        self.assert_no_private_text()

    def test_sdk_retried_kinds_not_retried_by_app(self):
        cases = [err("api_connection", None, "APIConnectionError"), err("api_timeout", None, "APITimeoutError"),
                 err("api_server", 503, "InternalServerError"), err("api_rate_limit", 429, "RateLimitError"),
                 err("api_auth", 401, "AuthenticationError"), err("api_quota", 429, "RateLimitError"),
                 err("api_other", 400, "BadRequestError")]
        for e in cases:
            with self.subTest(kind=e.kind):
                self.log.truncate(0), self.log.seek(0)
                self.finish([e, response("evaluation", "mixed")])
                self.click("평가 받기")
                self.assertIsNone(self.at.session_state["evaluation"])
                self.assertEqual(len(self.calls("evaluation")), 1)
                self.assertEqual(self.statuses(), [(e.kind, "evaluation", 1, "failed")])


class RetryScoringRecoveryTest(RecoveryCase):

    def start_retry(self, retries):
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")],
                       "retry": retries})
        self.start_interview()
        self.finish_interview()
        self.click("평가 받기")
        self.to_retry()
        no = self.at.selectbox(key="retry_no").value
        self.at.text_area(key=f"retry_answer_{no}").input("다시 쓴 답").run()
        return no

    def test_auto_retry_recovers_counts_once(self):
        no = self.start_retry([wrong_retry(), response("retry", "improved")])
        self.click("다시 채점")
        self.assertEqual(len(self.at.session_state["retry_history"][no]), 1)
        self.assertEqual(self.at.session_state["retry_counts"], {no: 1})   # 2 가 아님
        self.assertEqual(self.statuses(), [("eval_validation", "retry", 1, "retrying"),
                                           ("eval_validation", "retry", 2, "recovered")])
        self.assertEqual(self.events()[1]["meta"]["question_no"], no)
        self.assertNotIn(no, self.at.session_state["retry_pending"])

    def test_final_failure_keeps_answer_across_questions(self):
        no = self.start_retry([wrong_retry(), wrong_retry(), response("retry", "improved")])
        before = {k: self.at.session_state[k] for k in ("retry_history", "retries", "retry_counts")}
        self.click("다시 채점")
        self.assertIn("채점 결과를 확인하지 못했어요", " ".join(e.value for e in self.at.error))
        for key, value in before.items():
            self.assertEqual(self.at.session_state[key], value, key)
        self.assertEqual(self.at.session_state["retry_pending"], {no: "다시 쓴 답"})
        self.assertEqual([s[2:] for s in self.statuses()], [(1, "retrying"), (2, "failed")])

        other = next(n for n in range(1, coach.TOTAL_QUESTIONS + 1) if n != no)  # 값은 질문 번호 (보이는 글은 라벨)
        self.at.selectbox(key="retry_no").set_value(other).run()      # 다른 질문으로 갔다가
        # Streamlit 은 그리지 않은 칸의 값을 실행이 끝날 때 지운다 → 보관한 답(retry_pending)으로 다시 채워야 한다
        self.assertNotIn(f"retry_answer_{no}", self.at.session_state)
        self.at.selectbox(key="retry_no").set_value(no).run()         # 돌아오면
        self.assertEqual(self.at.text_area(key=f"retry_answer_{no}").value, "다시 쓴 답")
        self.assertIn(RETRY_PENDING_MESSAGE, " ".join(i.value for i in self.at.info))

        self.at.text_area(key=f"retry_answer_{no}").input("다시 고친 답").run()  # 보관 중인 답을 고치면
        self.assertEqual(self.at.session_state["retry_pending"], {no: "다시 고친 답"})
        self.at.selectbox(key="retry_no").set_value(other).run()
        self.assertNotIn(f"retry_answer_{no}", self.at.session_state)
        self.at.selectbox(key="retry_no").set_value(no).run()
        self.assertEqual(self.at.text_area(key=f"retry_answer_{no}").value, "다시 고친 답")

        self.click("다시 채점")                                        # 다시 채점 성공 → 보관 정리, 기록 1 · 횟수 1
        self.assertEqual(self.at.session_state["retry_history"][no][-1]["answer"], "다시 고친 답")
        self.assertEqual(self.at.session_state["retry_counts"], {no: 1})
        self.assertEqual(self.at.session_state["retry_pending"], {})
        self.assertNotIn("다시", self.log.getvalue())                  # 답 글은 기록에 없음


class MaxHttpRequestsTest(RecoveryCase):
    """실제 SDK(기본 재시도 2회) + 앱 재시도: 클릭 1번의 HTTP 요청 수를 센다. 네트워크 대신 MockTransport."""

    def use_transport(self, statuses):
        self.requests = 0

        def handler(request):
            self.requests += 1
            status = statuses[min(self.requests, len(statuses)) - 1]
            if status == "timeout":
                raise httpx2.ReadTimeout("timeout", request=request)
            if status == 200:
                return httpx2.Response(200, json={"id": "r", "object": "response", "created_at": 0, "model": "m",
                                                  "output": [{"type": "message", "id": "m", "role": "assistant",
                                                              "status": "completed", "content": [
                                                                  {"type": "output_text", "text": "not json",
                                                                   "annotations": []}]}]})
            return httpx2.Response(status, json={"error": {"message": "x", "code": None}})

        self.real_openai = llm.OpenAI
        llm.OpenAI = functools.partial(openai.OpenAI, http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))
        self.addCleanup(setattr, llm, "OpenAI", self.real_openai)
        os.environ["OPENAI_API_KEY"] = "test-key-not-real"

    def evaluate_with(self, statuses):
        self.open_app({"interviewer": sequence("probe_one_follow_up")})
        self.start_interview()
        self.finish_interview()
        self.use_transport(statuses)
        llm.ask_json = self.real_ask_json                              # 평가는 실제 ask_json → 실제 SDK
        self.click("평가 받기")
        return self.requests

    def test_worst_case_four(self):
        """형식 오류(200, 1번) → 앱 재시도 1회 → 서버 오류가 계속 (SDK 3번) = 4번."""
        self.assertEqual(self.evaluate_with([200, 503, 503, 503, 503]), 4)
        self.assertEqual(self.statuses(), [("response_parse", "evaluation", 1, "retrying"),
                                           ("api_server", "evaluation", 2, "failed")])

    def test_server_error_three(self):
        self.assertEqual(self.evaluate_with([503] * 6), 3)            # SDK 1 + 2, 앱 재시도 없음
        self.assertEqual(self.statuses(), [("api_server", "evaluation", 1, "failed")])

    def test_timeout_three(self):
        self.assertEqual(self.evaluate_with(["timeout"] * 6), 3)
        self.assertEqual(self.statuses(), [("api_timeout", "evaluation", 1, "failed")])

    def test_quota_three(self):
        """할당량 부족 429 도 SDK 는 다시 시도한다 (서버가 x-should-retry: false 를 주지 않으면). 앱은 다시 부르지 않음."""
        self.assertEqual(self.evaluate_with([429] * 6), 3)

    def test_parse_twice_two(self):
        self.assertEqual(self.evaluate_with([200, 200, 200]), 2)
        self.assertEqual([s[3] for s in self.statuses()], ["retrying", "failed"])

    def test_auth_one(self):
        self.assertEqual(self.evaluate_with([401] * 3), 1)


class StaticRecoveryTest(unittest.TestCase):

    def source(self):
        return (ROOT / "app.py").read_text(encoding="utf-8")

    def test_retry_policy_constants(self):
        tree = ast.parse(self.source())
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                try:
                    values[node.targets[0].id] = ast.literal_eval(node.value)
                except ValueError:
                    pass
        self.assertEqual(values["AUTO_RETRY_KINDS"], {"response_parse", "eval_validation"})
        self.assertEqual(values["AUTO_RETRY_SOURCES"], {"interviewer", "evaluation", "retry"})
        self.assertEqual(values["MAX_APP_ATTEMPTS"], 2)
        self.assertEqual(openai._constants.DEFAULT_MAX_RETRIES, 2)  # SDK 설정은 바꾸지 않음 (llm.py 그대로)

    def test_interviewer_goes_through_run_ai(self):
        source = self.source()
        self.assertIn('"interviewer", container=live', source)
        self.assertEqual(source.count('INTERVIEWER_SCHEMA, "interviewer")'), 1)
        self.assertNotIn("log_ai_error", source)


if __name__ == "__main__":
    unittest.main()
