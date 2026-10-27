# OpenAI 호출은 이 파일 한 곳에서만 한다.
import json
import os

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

load_dotenv()

DEFAULT_MODEL = "gpt-6-luna"


class LLMError(Exception):
    """화면에 그대로 보여 줄 한국어 한 줄 에러."""


def ask_json(instructions: str, user_input: str, schema: dict, name: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("API 키가 없어요. .env 에 OPENAI_API_KEY 를 넣어 주세요.")

    client = OpenAI(api_key=api_key)
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
    except AuthenticationError:
        raise LLMError("API 키가 틀렸어요. .env 의 OPENAI_API_KEY 를 확인해 주세요.") from None
    except RateLimitError as e:
        if e.code == "insufficient_quota":
            raise LLMError("OpenAI 크레딧이 부족해요. 결제 · 사용 한도를 확인해 주세요.") from None
        raise LLMError("요청이 너무 많아요. 잠시 뒤 다시 시도해 주세요.") from None
    except APIConnectionError:
        raise LLMError("OpenAI 에 연결하지 못했어요. 인터넷 연결을 확인해 주세요.") from None
    except OpenAIError:
        raise LLMError("AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요.") from None

    try:
        return json.loads(response.output_text)
    except (json.JSONDecodeError, TypeError):
        raise LLMError("AI 응답을 읽지 못했어요. 다시 시도해 주세요.") from None
