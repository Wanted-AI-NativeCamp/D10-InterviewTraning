# 질문 고르기 · 숫자 규칙 · 프롬프트 칸 채우기. AI 호출은 하지 않는다.
from pathlib import Path

import pandas as pd

from prompts import CONTEXT, INTERVIEWER, PERSONAS

TOTAL_QUESTIONS = 5
MAX_FOLLOW_UPS = 1
MIN_EXPERIENCE_CHARS = 30

QUESTIONS_PATH = Path(__file__).parent / "data" / "questions.csv"
JOBS = list(PERSONAS)


def load_questions(path: Path = QUESTIONS_PATH) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def pick_questions(df: pd.DataFrame, job: str) -> list[dict]:
    """자기소개 1 + 공통 1 + 직무 1 + 경험 1 + 상황 1 = 5개를 이 순서로 고른다."""
    common = df[df["직군"] == "공통"]
    is_intro = common["질문"].str.contains("자기소개")
    mine = df[df["직군"] == job]

    pools = [
        common[is_intro],
        common[~is_intro],
        mine[mine["유형"] == "직무"],
        mine[mine["유형"] == "경험"],
        mine[mine["유형"] == "상황"],
    ]
    picked = []
    for pool in pools:
        if pool.empty:
            raise ValueError(f"'{job}' 직군 질문이 질문 은행에 부족해요.")
        row = pool.sample(1).iloc[0]
        picked.append({"type": row["유형"], "question": row["질문"], "point": row["보는 점"]})
    assert len(picked) == TOTAL_QUESTIONS
    return picked


def build_interviewer(job: str, company: str, experience: str, question: dict) -> str:
    context = CONTEXT.format(company=company, job=job, experience=experience)
    return INTERVIEWER.format(
        persona=PERSONAS[job],
        context=context,
        question=question["question"],
        point=question["point"],
    )


def format_transcript(messages: list[dict]) -> str:
    """지금까지의 대화를 AI에게 넘길 글로 만든다."""
    names = {"assistant": "면접관", "user": "지원자"}
    return "\n".join(f"[{names[m['role']]}] {m['content']}" for m in messages)


def clamp(value, low: int, high: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return low
    return max(low, min(high, value))


def should_follow_up(ai_wants: bool, follow_ups_done: int) -> bool:
    """AI가 더 묻자고 해도 질문당 MAX_FOLLOW_UPS 번까지만 허용한다."""
    return bool(ai_wants) and follow_ups_done < MAX_FOLLOW_UPS
