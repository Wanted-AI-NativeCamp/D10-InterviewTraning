# 가짜 AI 응답 (P0-03). llm.ask_json 과 같은 모양으로 불리고, fixtures/ai 의 응답을 순서대로 돌려준다.
# 외부 API 를 부르지 않는다. 화면 테스트(P0-04)에서 llm.ask_json 자리에 끼워 쓴다.
import json
from pathlib import Path

# jsonschema 는 requirements.txt 에 없다 (streamlit → altair 를 따라 설치됨).
# P0-05 검토: ① 명시적 의존성으로 추가할지  ② 테스트 전용 의존성(예: requirements-dev.txt)으로 분리할지
from jsonschema import Draft202012Validator

from llm import LLMError

AI_FIXTURES = Path(__file__).parent / "fixtures" / "ai"
KINDS = ("interviewer", "evaluation", "retry")  # ask_json 의 name · 파일 이름


def load(kind: str) -> dict:
    return json.loads((AI_FIXTURES / f"{kind}.json").read_text(encoding="utf-8"))


def response(kind: str, case: str) -> dict:
    """정상 응답(cases) 또는 경계 응답(edge_cases) 하나. 돌려줄 때마다 새 사본."""
    data = load(kind)
    found = data["cases"].get(case) or data.get("edge_cases", {}).get(case)
    if found is None:
        raise KeyError(f"{kind}.json 에 '{case}' 응답이 없어요.")
    return json.loads(json.dumps(found))


def sequence(name: str) -> list[dict]:
    """면접관 응답 순서 (interviewer.json 의 sequences)."""
    return [response("interviewer", case) for case in load("interviewer")["sequences"][name]]


class FakeAskJson:
    """script: {name: [응답 dict 또는 LLMError, ...]} — name 마다 앞에서부터 하나씩 돌려준다.
    LLMError 를 넣으면 그 차례에 실패한다 (평가 실패 흐름 시험용). 부른 기록은 calls 에 남는다.
    응답이 그 호출의 스키마에 맞지 않거나, 준비하지 않은 name 이 불리면 AssertionError (테스트를 바로 멈춘다)."""

    def __init__(self, script: dict[str, list]):
        self.queues = {name: list(items) for name, items in script.items()}
        self.calls: list[dict] = []

    def __call__(self, instructions: str, user_input: str, schema: dict, name: str) -> dict:
        self.calls.append({"name": name, "instructions": instructions, "user_input": user_input})
        queue = self.queues.get(name)
        if not queue:
            raise AssertionError(f"가짜 AI 응답이 준비되지 않은 호출이에요: '{name}'")
        item = queue.pop(0)
        if isinstance(item, LLMError):
            raise item
        Draft202012Validator(schema).validate(item)
        return json.loads(json.dumps(item))

    def remaining(self) -> dict[str, int]:
        return {name: len(items) for name, items in self.queues.items() if items}
