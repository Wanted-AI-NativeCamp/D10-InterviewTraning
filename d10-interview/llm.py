# OpenAI 호출은 이 파일 한 곳에서만 한다.
import json
import os

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    OpenAI,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)

load_dotenv()

DEFAULT_MODEL = "gpt-6-luna"


class LLMError(Exception):
    """화면에 그대로 보여 줄 한국어 한 줄 에러.
    kind: 오류 기록용 분류(error_log 의 D9 코드) · http_status: HTTP 상태(있을 때) · exception: SDK 예외 클래스 이름.
    SDK 예외 메시지 원문은 담지 않는다. LLMError("문구") 처럼 문구만 주면 kind 는 api_other."""

    def __init__(self, message: str, kind: str = "api_other", http_status: int | None = None,
                 exception: str | None = None, code: str | None = None):
        super().__init__(message)
        self.kind = kind
        self.http_status = http_status
        self.exception = exception
        self.code = code  # 오류 기록의 세부 코드 (예: missing_api_key)


def _status(e) -> int | None:
    status = getattr(e, "status_code", None)
    return status if isinstance(status, int) else None


def ask_json(instructions: str, user_input: str, schema: dict, name: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("API 키가 없어요. .env 에 OPENAI_API_KEY 를 넣어 주세요.", "api_auth", code="missing_api_key")

    client = OpenAI(api_key=api_key)  # SDK 기본 재시도(max_retries=2) · 기본 대기 시간 그대로
    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL") or DEFAULT_MODEL,
            instructions=instructions,
            input=user_input,
            text={
                "format": {
                    "type": "json_schema",
                    "name": name,
                    "schema": schema,
                    "strict": True,
                }
            },
        )
    # 문구는 그대로 두고 kind 만 나눈다. 시간 초과는 연결 실패의 하위 예외라 먼저 본다.
    except AuthenticationError as e:
        raise LLMError("API 키가 틀렸어요. .env 의 OPENAI_API_KEY 를 확인해 주세요.",
                       "api_auth", _status(e), type(e).__name__) from None
    except RateLimitError as e:
        if e.code == "insufficient_quota":
            raise LLMError("OpenAI 크레딧이 부족해요. 결제 · 사용 한도를 확인해 주세요.",
                           "api_quota", _status(e), type(e).__name__) from None
        raise LLMError("요청이 너무 많아요. 잠시 뒤 다시 시도해 주세요.",
                       "api_rate_limit", _status(e), type(e).__name__) from None
    except APITimeoutError as e:
        raise LLMError("OpenAI 에 연결하지 못했어요. 인터넷 연결을 확인해 주세요.",
                       "api_timeout", None, type(e).__name__) from None
    except APIConnectionError as e:
        raise LLMError("OpenAI 에 연결하지 못했어요. 인터넷 연결을 확인해 주세요.",
                       "api_connection", None, type(e).__name__) from None
    except OpenAIError as e:
        if isinstance(e, PermissionDeniedError):
            kind = "api_auth"  # 403: 401 과는 http_status 로 구분
        elif isinstance(e, InternalServerError):
            kind = "api_server"
        else:
            kind = "api_other"
        raise LLMError("AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요.",
                       kind, _status(e) if isinstance(e, APIStatusError) else None, type(e).__name__) from None

    try:
        return json.loads(response.output_text)
    except (json.JSONDecodeError, TypeError) as e:
        raise LLMError("AI 응답을 읽지 못했어요. 다시 시도해 주세요.",
                       "response_parse", None, type(e).__name__, code="json_decode") from None
