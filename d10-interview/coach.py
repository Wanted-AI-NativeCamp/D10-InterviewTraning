# 질문 고르기 · 숫자 규칙 · 프롬프트 칸 채우기. AI 호출은 하지 않는다.
from pathlib import Path

import pandas as pd

from prompts import CONTEXT, EVALUATOR, INTERVIEWER, PANEL_ROLES, PERSONAS, RETRY

TOTAL_QUESTIONS = 5
MAX_FOLLOW_UPS = 1
MIN_EXPERIENCE_CHARS = 30

CRITERIA = {"specific": "구체성", "relevance": "직무 연관", "structure": "구조", "evidence": "근거 · 검증"}
CRITERION_MAX = 5
ANSWER_MAX = CRITERION_MAX * len(CRITERIA)  # 20
PANEL_MAX = 10
REWRITE_BELOW = 14  # 답변 점수(0~20)가 이 점수 미만인 답만 고친 답을 보여 준다
MAX_CHECKS = 2
MAX_NEXT = 3

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


def build_context(profile: dict) -> str:
    return CONTEXT.format(
        company=profile["company"],
        company_desc=profile["company_desc"],
        job=profile["job"],
        experience=profile["experience"],
    )


def build_interviewer(profile: dict, question: dict) -> str:
    return INTERVIEWER.format(
        persona=PERSONAS[profile["job"]],
        context=build_context(profile),
        question=question["question"],
        point=question["point"],
    )


def build_evaluator(profile: dict) -> str:
    return EVALUATOR.format(context=build_context(profile))


def build_retry(profile: dict, question: dict, before: str, weak: str) -> str:
    return RETRY.format(
        persona=PERSONAS[profile["job"]],
        context=build_context(profile),
        question=question["question"],
        point=question["point"],
        before=before,
        weak=weak,
    )


def answer_text(messages: list[dict], index: int) -> str:
    """한 질문에 대한 지원자의 답(꼬리 질문 답 포함)을 이어 붙인다."""
    return "\n".join(m["content"] for m in messages if m.get("q") == index and m["role"] == "user")


def format_record(questions: list[dict], messages: list[dict]) -> str:
    """면접 기록을 질문별로 묶는다. 메시지의 'q' 는 질문 번호(0부터)."""
    names = {"assistant": "면접관", "user": "지원자"}
    blocks = []
    for i, q in enumerate(questions):
        lines = [f"[질문 {i + 1} · {q['type']}] {q['question']}"]
        lines += [
            f"[{names[m['role']]}] {m['content']}"
            for m in messages
            if m.get("q") == i and m.get("kind") != "question"
        ]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


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


def panel_average(panel: list[dict]) -> float:
    """위원 점수(0~10)의 평균. AI가 쓴 합계 · 평균은 쓰지 않는다."""
    if not panel:
        return 0.0
    return sum(m["score"] for m in panel) / len(panel)


def answer_score(scores: dict) -> int:
    """기준 4개(각 0~5)의 합 = 답변 점수 0~20."""
    return sum(scores[key] for key in CRITERIA)


def clamp_scores(raw: dict) -> dict:
    return {key: clamp(raw.get(key), 0, CRITERION_MAX) for key in CRITERIA}


def retry_order(answers: list[dict]) -> list[dict]:
    """재도전할 질문을 답변 점수가 낮은 순으로 (같으면 질문 번호 순)."""
    return sorted(answers, key=lambda a: (a["score"], a["no"]))


def summarize_retry(raw: dict) -> dict:
    scores = clamp_scores(raw)
    return {"scores": scores, "score": answer_score(scores), "weak": str(raw.get("weak", ""))}


def compare(before: dict, after: dict) -> dict:
    """전 → 후 점수 차이. before · after 는 기준별 점수 dict."""
    rows = [
        {"기준": name, "전": before[key], "후": after[key], "차이": after[key] - before[key]}
        for key, name in CRITERIA.items()
    ]
    before_score, after_score = answer_score(before), answer_score(after)
    return {"before": before_score, "after": after_score, "diff": after_score - before_score, "rows": rows}


def summarize_evaluation(raw: dict, questions: list[dict]) -> dict:
    """AI 평가를 범위 안으로 자르고, 평균 · 합계는 여기서 다시 계산한다."""
    by_role = {m.get("role"): m for m in raw.get("panel", [])}
    panel = []
    for role in PANEL_ROLES:
        m = by_role.get(role, {})
        panel.append({
            "role": role,
            "against": str(m.get("against", "")),
            "good": str(m.get("good", "")),
            "score": clamp(m.get("score"), 0, PANEL_MAX),
        })

    raw_answers = raw.get("answers", [])
    by_number = {a.get("no"): a for a in raw_answers}
    answers = []
    for i, q in enumerate(questions):
        # 질문 번호(no, 1부터)로 찾고, 없으면 순서로 찾는다.
        a = by_number.get(i + 1) or (raw_answers[i] if i < len(raw_answers) else {})
        scores = clamp_scores(a)
        score = answer_score(scores)
        answers.append({
            "no": i + 1,
            "question": q["question"],
            "scores": scores,
            "score": score,
            "weak": str(a.get("weak", "")),
            "rewrite": str(a.get("rewrite", "")),
            "check": [str(c) for c in a.get("check", [])][:MAX_CHECKS],
            "needs_rewrite": score < REWRITE_BELOW,
        })

    return {
        "panel": panel,
        "panel_average": panel_average(panel),
        "conflict": str(raw.get("conflict", "")),
        "agree": str(raw.get("agree", "")),
        "answers": answers,
        "next": [str(n) for n in raw.get("next", [])][:MAX_NEXT],
    }
