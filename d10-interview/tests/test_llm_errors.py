# llm.py API 오류 분류 테스트 (E-2). 실제 API 를 부르지 않는다 — OpenAI 클라이언트를 가짜로 바꾸고 SDK 예외 객체를 던진다.
# 실행: d10-interview 폴더에서  python -m unittest discover tests
import os
import unittest
from unittest import mock

import httpx2
import openai

import error_log
import llm
from llm import LLMError

REQ = httpx2.Request("POST", "https://api.openai.com/v1/responses")
SECRET_MSG = "SDK-MESSAGE sk-proj-SHOULD-NOT-LEAK request body 김예시"  # 예외 메시지 원문 (남으면 안 됨)

# 변경 전(llm.py · 커밋 779f4aa) 화면 문구 그대로
MSG_NO_KEY = "API 키가 없어요. .env 에 OPENAI_API_KEY 를 넣어 주세요."
MSG_AUTH = "API 키가 틀렸어요. .env 의 OPENAI_API_KEY 를 확인해 주세요."
MSG_QUOTA = "OpenAI 크레딧이 부족해요. 결제 · 사용 한도를 확인해 주세요."
MSG_RATE = "요청이 너무 많아요. 잠시 뒤 다시 시도해 주세요."
MSG_CONN = "OpenAI 에 연결하지 못했어요. 인터넷 연결을 확인해 주세요."
MSG_OTHER = "AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요."
MSG_PARSE = "AI 응답을 읽지 못했어요. 다시 시도해 주세요."


def status_error(cls, status, body=None):
    return cls(SECRET_MSG, response=httpx2.Response(status, request=REQ), body=body)


class FakeResponse:
    def __init__(self, output_text):
        self.output_text = output_text


def fake_client(raise_=None, output_text='{"ok": true}'):
    """llm.OpenAI 자리에 넣을 가짜 클래스. responses.create 가 예외를 던지거나 응답을 돌려준다."""
    calls = []

    class Responses:
        def create(self, **kwargs):
            calls.append(kwargs)
            if raise_ is not None:
                raise raise_
            return FakeResponse(output_text)

    class Client:
        def __init__(self, **kwargs):
            calls.append({"init": kwargs})
            self.responses = Responses()

    return Client, calls


CASES = [  # (예외, kind, http_status, 화면 문구)
    (status_error(openai.AuthenticationError, 401), "api_auth", 401, MSG_AUTH),
    (status_error(openai.PermissionDeniedError, 403), "api_auth", 403, MSG_OTHER),
    (status_error(openai.RateLimitError, 429, {"code": "insufficient_quota"}), "api_quota", 429, MSG_QUOTA),
    (status_error(openai.RateLimitError, 429, {"code": "rate_limit_exceeded"}), "api_rate_limit", 429, MSG_RATE),
    (openai.APITimeoutError(request=REQ), "api_timeout", None, MSG_CONN),
    (openai.APIConnectionError(request=REQ, message=SECRET_MSG), "api_connection", None, MSG_CONN),
    (status_error(openai.InternalServerError, 500), "api_server", 500, MSG_OTHER),
    (status_error(openai.InternalServerError, 503), "api_server", 503, MSG_OTHER),
    (status_error(openai.BadRequestError, 400), "api_other", 400, MSG_OTHER),
    (status_error(openai.NotFoundError, 404), "api_other", 404, MSG_OTHER),
    (status_error(openai.UnprocessableEntityError, 422), "api_other", 422, MSG_OTHER),
    (openai.APIResponseValidationError(response=httpx2.Response(200, request=REQ), body=None, message=SECRET_MSG),
     "api_other", None, MSG_OTHER),
    (openai.OpenAIError(SECRET_MSG), "api_other", None, MSG_OTHER),
]


class ClassifyTest(unittest.TestCase):

    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-not-real"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def ask(self, client):
        with mock.patch.object(llm, "OpenAI", client):
            return llm.ask_json("지시", "입력", {"type": "object"}, "evaluation")

    def test_sdk_exceptions(self):
        for exc, kind, status, message in CASES:
            with self.subTest(exc=type(exc).__name__, status=status):
                client, _ = fake_client(raise_=exc)
                with self.assertRaises(LLMError) as caught:
                    self.ask(client)
                e = caught.exception
                self.assertEqual(str(e), message)                      # 화면 문구 그대로
                self.assertEqual((e.kind, e.http_status, e.exception), (kind, status, type(exc).__name__))
                self.assertIsNone(e.code)
                self.assertIsNone(e.__cause__)                        # from None: SDK 예외를 품지 않는다
                self.assertNotIn("SDK-MESSAGE", repr(vars(e)) + str(e) + repr(e.args))

    def test_missing_key(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            client, calls = fake_client()
            with self.assertRaises(LLMError) as caught:
                self.ask(client)
        e = caught.exception
        self.assertEqual(str(e), MSG_NO_KEY)
        self.assertEqual((e.kind, e.code, e.http_status, e.exception), ("api_auth", "missing_api_key", None, None))
        self.assertEqual(calls, [])  # 호출 전에 멈춘다

    def test_parse_errors(self):
        for text in ("not json", "", None):
            with self.subTest(text=text):
                client, _ = fake_client(output_text=text)
                with self.assertRaises(LLMError) as caught:
                    self.ask(client)
                e = caught.exception
                self.assertEqual(str(e), MSG_PARSE)
                self.assertEqual((e.kind, e.code), ("response_parse", "json_decode"))

    def test_success_unchanged(self):
        client, calls = fake_client(output_text='{"reply": "네", "follow_up": false, "understanding": 50}')
        self.assertEqual(self.ask(client), {"reply": "네", "follow_up": False, "understanding": 50})
        init = calls[0]["init"]
        self.assertEqual(set(init), {"api_key"})                       # max_retries · timeout 은 SDK 기본값 그대로
        req = calls[1]
        self.assertEqual(req["text"]["format"]["strict"], True)
        self.assertEqual(req["text"]["format"]["name"], "evaluation")

    def test_every_kind_is_a_d9_code(self):
        kinds = {kind for _, kind, _, _ in CASES} | {"api_auth", "response_parse"}
        self.assertLessEqual(kinds, error_log.ERROR_TYPES)


class CompatibilityTest(unittest.TestCase):

    def test_message_only_construction(self):
        """기존 방식 LLMError("문구") 그대로 동작 (가짜 AI · 기존 테스트가 쓰는 방식)."""
        e = LLMError("AI 응답을 받지 못했어요.")
        self.assertEqual(str(e), "AI 응답을 받지 못했어요.")
        self.assertEqual((e.kind, e.http_status, e.exception, e.code), ("api_other", None, None, None))
        self.assertIn(e.kind, error_log.ERROR_TYPES)


if __name__ == "__main__":
    unittest.main()
