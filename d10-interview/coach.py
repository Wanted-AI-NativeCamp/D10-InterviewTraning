# 질문 고르기 · 숫자 규칙 · 프롬프트 칸 채우기 · 리포트. AI 호출은 하지 않는다.
import hashlib
import json
import math
import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from prompts import (
    CONTEXT,
    FIELDS,
    EVALUATOR,
    HIGHLIGHT,
    INTERVIEWER,
    LAST_QUESTION,
    LAST_SUGGEST,
    PANEL_CRITERIA,
    PANEL_ROLES,
    PERSONAS,
    RETRY,
    STRATEGY,
)

TOTAL_QUESTIONS = 5
MAX_FOLLOW_UPS = 1
MIN_EXPERIENCE_CHARS = 30

CRITERIA = {"specific": "구체성", "relevance": "직무 연관", "structure": "구조", "evidence": "근거 · 검증"}
CRITERION_MAX = 5
ANSWER_MAX = CRITERION_MAX * len(CRITERIA)  # 20
PANEL_MAX = 10
REWRITE_BELOW = 14  # 답변 점수(0~20)가 이 점수 미만인 답만 고친 답을 보여 준다
TOTAL_MAX = ANSWER_MAX * TOTAL_QUESTIONS  # 종합 점수 100

# 최종 판결 (모의면접 학습 지표 — 실제 채용 결과와 무관)
# 합격 = 종합 PASS_TOTAL 이상 + 위원 평균 PASS_PANEL 이상
# 합격 후보 = 종합 CANDIDATE_TOTAL 이상 + 위원 평균 CANDIDATE_PANEL 이상 (합격이 아닐 때)
# 평가 탭 타이틀(EVAL_TITLES)도 같은 기준을 쓴다.
PASS_TOTAL = 90        # 합격선: 최신 종합 점수(0~100)
PASS_PANEL = 9.0       # 합격선: 위원 평균(0~10)
CANDIDATE_TOTAL = 70   # 합격 후보선: 최신 종합 점수(0~100)
CANDIDATE_PANEL = 7.0  # 합격 후보선: 위원 평균(0~10)
VERDICT_LABELS = {"pass": "합격", "candidate": "합격 후보", "more": "재도전 필요"}  # 리포트 데이터에는 level(pass · candidate · more)만 남긴다
MAX_CLUES = 2       # 역전의 실마리: 가장 낮은 답 몇 개

# OpenAI 로 보내는 글의 길이 상한 · 재도전 횟수 상한 (사용량 줄이기)
MAX_ANSWER_CHARS = 1500
MAX_EXPERIENCE_CHARS = 1000  # 내 경험은 모든 호출에 들어간다
MAX_LAST_QUESTION_CHARS = 300
MAX_MEMO_CHARS = 200
MAX_RETRIES = 3  # 질문당
MAX_CHECKS = 2
MAX_NEXT = 3
LAST_ANGLES = ["회사", "직무", "성장"]  # 마지막 질문 3개의 관점 (이 순서)
PROMPT_BLANK = "___"

# 리포트 끝에 숨겨 두는 데이터 (마크다운 주석이라 문서에는 안 보임). 다음 면접에서 다시 읽는다.
REPORT_DATA_TAG = "interview-data"
REPORT_DATA_VERSION = 1
REPORT_DATA_RE = re.compile(r"<!--\s*" + REPORT_DATA_TAG + r"\s+(\{.*\})\s*-->", re.DOTALL)
MAX_FIELD_CHARS = 2000  # 리포트에서 읽는 글 한 칸의 최대 길이
MAX_ROUND = 999

QUESTIONS_PATH = Path(__file__).parent / "data" / "questions.csv"
PANEL_RATIONALE_PATH = Path(__file__).parent / "data" / "평가기준_근거.md"
MEMO_STRATEGY_PATH = Path(__file__).parent / "data" / "암기전략.md"
PRECHECK_PATH = Path(__file__).parent / "data" / "사전탐색_체크리스트.csv"

# 사전 탐색에서 '찾아봐도 없어요' 일 때 언제 확인하면 되는지
PRECHECK_TIMING = {
    "마지막": "**핵심 질문을 끝낸 뒤** 면접 마지막에 짧게 확인해 보세요. "
              "\"찾아봤는데 ○○까지는 확인했고, △△은 찾지 못했어요\" 처럼 찾아본 내용을 먼저 말하면 좋아요.",
    "합격 후": "면접에서는 묻지 말고 **합격(취직 확정) 후** 처우 협의 때 인사 담당자에게 확인하세요.",
}
PRECHECK_LATER_LABEL = {"마지막": "핵심 질문을 끝낸 뒤 확인", "합격 후": "합격(취직 확정) 후 확인"}
MAX_PRECHECK_ITEMS = 100
JOBS = list(PERSONAS)
DEFAULT_FIELD = "공통"


def load_questions(path: Path = QUESTIONS_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "분야" not in df.columns:  # 분야 칸이 생기기 전 질문 은행은 모두 공통
        df["분야"] = DEFAULT_FIELD
    df["분야"] = df["분야"].fillna(DEFAULT_FIELD)
    if "만점 예시" not in df.columns:  # 만점 예시 칸이 생기기 전 질문 은행
        df["만점 예시"] = ""
    df["만점 예시"] = df["만점 예시"].fillna("")
    return df


def question_row(row) -> dict:
    """질문 은행 한 줄 → 면접에서 쓰는 질문. example: 가상 지원자의 만점 예시 답 (사용자 정보와 무관, 없으면 빈칸)."""
    return {"type": row["유형"], "question": row["질문"], "point": row["보는 점"], "field": row["분야"],
            "example": str(row["만점 예시"]).strip()}


def past_result(report: dict, index: int) -> dict:
    """지난 리포트에서 질문 하나의 최신 결과 {answer, score}: 처음 점수보다 높은 재도전이 있으면 그중 최고 점수,
    없으면 면접 때 답 · 점수 (그 회차에 반영된 답과 같은 규칙 · reflected_retry)."""
    session = report.get("session") or {}
    first = answer_text(session.get("messages") or [], index).strip()
    scores = report.get("scores") or []
    score = scores[index] if index < len(scores) else None
    items = (session.get("retry_history") or {}).get(str(index + 1)) or []
    attempts = []
    for r in items if isinstance(items, list) else []:
        if isinstance(r, dict) and isinstance(r.get("answer"), str) and r["answer"].strip():
            attempts.append({"answer": r["answer"].strip(), **summarize_retry(r)})
    best = reflected_retry(score, attempts) if score is not None and attempts else None
    return {"answer": best["answer"], "score": best["score"]} if best else {"answer": first, "score": score}


def past_answer(report: dict, index: int) -> str:
    return past_result(report, index)["answer"]


def question_history(reports: list[dict]) -> dict[str, list[dict]]:
    """지난 회차 리포트에서 질문 글마다 나온 회차 기록: {질문 글: [{round, answer, score}, ...]} (회차 오름차순).
    같은 회차 리포트가 여러 개면 (같은 회차 이어 하기) 나중 것 하나만 쓴다."""
    history: dict[str, dict[int, dict]] = {}
    for report in reports:
        round_no = report.get("round", 1)
        for i, text in enumerate(report.get("questions") or []):
            history.setdefault(text, {})[round_no] = {"round": round_no, **past_result(report, i)}
    return {text: [rows[r] for r in sorted(rows)] for text, rows in history.items()}


def practice_questions(reports: list[dict], current: list[str], bank: pd.DataFrame, job: str,
                       field: str = DEFAULT_FIELD) -> list[dict]:
    """암기 탭 '다른 질문': 이번 회차 질문이 아닌 질문 (연습만 · 점수에는 들어가지 않는다).
    지난 회차 질문(최근 회차 먼저, 그 회차의 최신 답) → 질문 은행의 나머지 질문(내 답 없음) 순서.
    id 는 질문 글로 만든 짧은 값이라 목록 순서가 바뀌어도 연습 기록이 그 질문에 남는다."""
    seen = set(current)
    picked = []
    saved = saved_practice(reports)  # 지난 회차에 고치거나 직접 쓴 연습 대본

    def add(text: str, row: dict | None, past: dict | None):
        if text in seen:
            return
        seen.add(text)
        picked.append({
            "id": practice_id(text), "question": text,
            "point": row["point"] if row else "", "example": row["example"] if row else "", "past": past,
            "saved": saved.get(text),
        })

    rows = {r["질문"]: question_row(r) for _, r in bank[bank["직군"].isin(["공통", job])].iterrows()}
    for report in sorted(reports, key=lambda r: r.get("round", 1), reverse=True):
        for i, text in enumerate(report.get("questions") or []):
            answer = past_answer(report, i)
            add(text, rows.get(text), {"round": report.get("round", 1), "answer": answer} if answer else None)
    for text in saved:  # 연습 대본만 있는 질문 (예: 다른 분야로 바꾸기 전에 연습한 질문)
        if text not in rows or rows[text]["field"] in (field, DEFAULT_FIELD):
            add(text, rows.get(text), None)
    for text, row in rows.items():
        if row["field"] in (field, DEFAULT_FIELD):
            add(text, row, None)
    return picked


def practice_id(text: str) -> str:
    """'다른 질문' 의 짧은 id (질문 글로 만든다: 목록 순서가 바뀌어도 그 질문의 연습 기록이 남는다)."""
    return "x" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def pick_questions(df: pd.DataFrame, job: str, field: str = DEFAULT_FIELD) -> list[dict]:
    """자기소개 1 + 공통 1 + 직무 1 + 경험 1 + 상황 1 = 5개를 이 순서로 무작위로 고른다.
    자리마다 고른 분야의 질문이 있으면 그중에서, 없으면 분야 공통 질문에서 고른다."""
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
        in_field = pool[pool["분야"] == field] if field != DEFAULT_FIELD else pool.iloc[0:0]
        pool = in_field if not in_field.empty else pool[pool["분야"] == DEFAULT_FIELD]
        if pool.empty:
            raise ValueError(f"'{job}' 직군 질문이 질문 은행에 부족해요.")
        picked.append(question_row(pool.sample(1).iloc[0]))
    assert len(picked) == TOTAL_QUESTIONS
    return picked


def field_of(profile: dict) -> str:
    """분야 (분야 기능 전 면접 · 리포트는 '공통')."""
    return profile.get("field") if profile.get("field") in FIELDS else DEFAULT_FIELD


def build_context(profile: dict) -> str:
    field = field_of(profile)
    return CONTEXT.format(
        company=profile["company"],
        company_desc=profile["company_desc"],
        field=field,
        field_desc=FIELDS[field],
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


def format_panel_criteria() -> str:
    return "\n".join(f"- {role}: {PANEL_CRITERIA[role]}" for role in PANEL_ROLES)


def build_evaluator(profile: dict) -> str:
    return EVALUATOR.format(panel_criteria=format_panel_criteria(), context=build_context(profile))


MAX_TIPS_PER_CRITERION = 2


def build_strategy(profile: dict, question: dict, answer: dict, evaluation: dict) -> str:
    scores = "\n".join(f"- {name}({key}): {answer['scores'][key]}" for key, name in CRITERIA.items())
    opinion = "\n".join(
        [f"- 가장 약한 점: {answer['weak']}"] + [f"- 다음 연습에서 고칠 것: {n}" for n in evaluation["next"]]
    )
    return STRATEGY.format(
        context=build_context(profile),
        question=question["question"],
        point=question["point"],
        scores=scores,
        opinion=opinion,
    )


def total_scores(evaluation: dict, retries: dict) -> dict:
    """종합 점수(0~100). 최초 = 답변 점수 5개 합. 최신 = 재도전한 질문만 재도전 점수로 바꿔 넣은 합."""
    first = sum(a["score"] for a in evaluation["answers"])
    latest = sum(retries[a["no"]]["score"] if a["no"] in retries else a["score"] for a in evaluation["answers"])
    return {"first": first, "latest": latest, "diff": latest - first, "max": TOTAL_MAX}


def reflected_retry(original_score: int, history: list[dict]) -> dict | None:
    """최고 점수 반영: 처음 점수보다 높은 재도전 중 가장 높은 것 (같은 점수면 나중 것). 없으면 None (처음 점수 반영).
    state.retries[no] 에는 이 값만 넣는다 → 종합 점수 · 판정 · 실마리 · 리포트가 모두 최고 점수를 쓴다."""
    best = None
    for attempt in history:
        if attempt["score"] > original_score and (best is None or attempt["score"] >= best["score"]):
            best = attempt
    return best


def failed_retries(original_score: int, history: list[dict]) -> list[tuple[int, dict]]:
    """반영되지 않은 재도전 (몇 번째, 재도전). 처음 점수보다 낮거나 같은 것, 더 높은 재도전에 밀린 것."""
    best = reflected_retry(original_score, history)
    return [(i, a) for i, a in enumerate(history, 1) if a is not best]


def latest_answers(evaluation: dict, retries: dict | None = None) -> list[dict]:
    """답마다 최신 점수: 재도전한 답은 재도전 점수 · 기준 점수 · 약한 점으로 바꾼다."""
    retries = retries or {}
    return [
        {**a, **{k: retries[a["no"]][k] for k in ("scores", "score", "weak")}} if a["no"] in retries else a
        for a in evaluation["answers"]
    ]


def pick_clues(evaluation: dict, count: int = MAX_CLUES, retries: dict | None = None,
               retry_counts: dict | None = None) -> list[dict]:
    """역전의 실마리: 최신 점수로 만점이 아닌 답 중 가장 낮은 답 count 개(같은 점수면 앞 번호)와
    각 답의 가장 낮은 기준 1개(같으면 기준 순서). 모두 만점이면 빈 목록.
    retry_count 는 실마리를 찾은 때의 재도전 횟수 (그 뒤에 재도전했는지 clue_progress 가 본다)."""
    order = list(CRITERIA)
    retry_counts = retry_counts or {}
    # 재도전을 MAX_RETRIES 번 모두 쓴 답은 더 고칠 수 없어서 실마리로 고르지 않는다
    candidates = sorted(
        (a for a in latest_answers(evaluation, retries)
         if a["score"] < ANSWER_MAX and retry_counts.get(a["no"], 0) < MAX_RETRIES),
        key=lambda x: (x["score"], x["no"]),
    )
    clues = []
    for a in candidates[:count]:
        key = min(order, key=lambda k: (a["scores"][k], order.index(k)))
        clues.append({
            "no": a["no"], "question": a["question"], "score": a["score"], "weak": a["weak"],
            "criterion": key, "name": CRITERIA[key], "criterion_score": a["scores"][key],
            "retry_count": retry_counts.get(a["no"], 0),
        })
    return clues


def clue_progress(clues: list[dict], evaluation: dict, retries: dict, retry_counts: dict) -> dict:
    """실마리마다 찾은 뒤 재도전했는지 · 점수 전 → 후. done: 실마리를 모두 재도전했으면 True (다시 찾기 가능)."""
    latest = {a["no"]: a["score"] for a in latest_answers(evaluation, retries)}
    rows = []
    for clue in clues:
        retried = retry_counts.get(clue["no"], 0) > clue.get("retry_count", 0)
        after = latest[clue["no"]]
        rows.append({"no": clue["no"], "retried": retried, "before": clue["score"], "after": after,
                     "diff": after - clue["score"], "up": retried and after > clue["score"]})
    return {"rows": rows, "done": bool(rows) and all(r["retried"] for r in rows)}


def highlight_criteria() -> list[dict]:
    """형광펜 기준표: HIGHLIGHT 지시문의 [기준] 줄(- key(이름): 설명)을 그대로 읽는다.
    AI에게 준 기준과 화면의 표가 늘 같게 하려고 문장을 따로 적지 않는다 (prompts.py 는 읽기만)."""
    return [
        {"key": key, "name": name, "rule": rule.strip()}
        for key, name, rule in re.findall(r"^- (\w+)\(([^)]+)\): (.+)$", HIGHLIGHT, re.MULTILINE)
        if key in CRITERIA
    ]


def perfect_hints(evaluation: dict) -> list[dict]:
    """모두 만점일 때 '힌트 확인하기': 평가에 이미 들어 있는 더 다듬을 점 · 다듬은 답 · 확인할 것을 답마다 모은다.
    AI를 새로 부르지 않는다. 셋 다 비어 있는 답은 뺀다."""
    return [
        {"no": a["no"], "question": a["question"], "weak": a["weak"], "rewrite": a["rewrite"], "check": a["check"]}
        for a in evaluation["answers"]
        if a["weak"] or a["rewrite"] or a["check"]
    ]


MOCK_PATH = Path(__file__).parent / "data" / "mock_perfect.json"


def load_mock(path: Path = MOCK_PATH) -> dict:
    """개발용 모의 데이터(만점)를 리포트 데이터와 같은 모양으로 읽는다. 점수 · 합계는 rebuild_session 이 다시 계산한다."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    session = _parse_session(raw.get("session"))
    if session is None:
        raise ValueError("모의 데이터의 session 모양이 달라요.")
    return {**raw, "session": session}


# 평가 탭 타이틀: (위원 평균 이상, 최신 종합 이상, 타이틀) — 위에서부터 먼저 맞는 것. 둘 다 넘어야 그 단계.
EVAL_TITLES = [
    (PASS_PANEL, PASS_TOTAL, "이제 남은 것은 연습입니다."),
    (CANDIDATE_PANEL, CANDIDATE_TOTAL, "한 걸음만 더 가면 됩니다."),
    (0.0, 0, "승부는 지금부터입니다."),
]


def eval_title(totals: dict, panel_average: float) -> str:
    """평가 탭 타이틀. 최신 종합(재도전 최고 점수 반영)과 위원 평균으로 코드가 고른다."""
    return next(title for panel, total, title in EVAL_TITLES
                if panel_average >= panel and totals["latest"] >= total)


def verdict(totals: dict, panel_average: float) -> dict:
    """최종 판결: pass(합격) · candidate(합격 후보) · more(재도전 필요).
    short 는 '다음 단계' 까지 모자란 점수 (합격이면 빈 목록)."""
    latest = totals["latest"]
    if latest >= PASS_TOTAL and panel_average >= PASS_PANEL:
        level = "pass"
    elif latest >= CANDIDATE_TOTAL and panel_average >= CANDIDATE_PANEL:
        level = "candidate"
    else:
        level = "more"

    # 다음 단계: 합격 후보 → 합격, 재도전 필요 → 합격 후보
    target_panel, target_total = (PASS_PANEL, PASS_TOTAL) if level == "candidate" else (CANDIDATE_PANEL, CANDIDATE_TOTAL)
    short = []
    # 재도전은 종합 점수만 올린다. 위원 평균은 다음 회차 면접에서만 바뀌므로 안내를 나눈다.
    panel_short = level != "pass" and panel_average < target_panel
    if level != "pass":
        if latest < target_total:
            short.append(f"종합 점수 {target_total - latest}점")
        if panel_average < target_panel:
            # 0.1 단위로 올림 (8.99 처럼 바로 아래일 때 '0.0점 부족' 으로 보이지 않게)
            gap = math.ceil(round((target_panel - panel_average) * 10, 6)) / 10
            short.append(f"위원 평균 {gap:.1f}점")
    return {
        "level": level, "label": VERDICT_LABELS[level], "passed": level == "pass",
        "total": totals["latest"], "panel": panel_average, "short": short, "panel_short": panel_short,
    }


def criteria_version() -> str:
    """평가 기준의 짧은 지문. 기준 문장 · 점수 범위가 바뀌면 값이 바뀐다 (이어 하기 때 비교)."""
    payload = json.dumps(
        {"panel": PANEL_CRITERIA, "criteria": CRITERIA, "criterion_max": CRITERION_MAX, "panel_max": PANEL_MAX},
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:8]


def persona_summary(job: str) -> str:
    """브리핑용 면접관 한 줄 (페르소나의 첫 문장)."""
    persona = PERSONAS.get(job, "").strip()
    return persona.split(". ")[0].rstrip(".") if persona else "(페르소나 없음)"


# ── 암기 시뮬레이션 (AI 없이 코드로) ──
MEMO_LEVELS = {1: 4, 2: 2, 3: 1}  # 빈칸 단계 → 핵심어 n개마다 1개를 가린다
MEMO_PASS = 80  # 실전 시뮬레이션: 핵심어를 이 % 이상 기억하면 다음 질문으로
MEMO_MODES = ["① 뼈대 보기", "② 빈칸 채우기", "③ 실전 시뮬레이션"]
# 단계별 연습 순서: (모드, 빈칸 단계). 낮은 단계부터 올라간다.
MEMO_STEPS = [(0, None), (1, 1), (1, 2), (1, 3), (2, None)]
# 실전 시뮬레이션 점수가 낮을 때 돌아갈 단계: 이 % 미만이면 그 단계부터 (MEMO_STEPS 번호)
MEMO_FALLBACK = [(40, 0), (60, 1), (MEMO_PASS, 2)]
SPEAK_LOG_KEEP = 5            # 말하기 타이머 기록은 답마다 최근 몇 번
INTRO_TARGET = (50, 60)       # 1분 자기소개 목표 초
SPEAK_SMOOTH = 0.2            # 대본 없이 말하기가 대본 읽기보다 20% 이내로 더 걸리면 '거의 안 막힘'
SPEAK_STUCK = 0.5             # 50% 넘게 더 걸리면 '많이 막힘'
SENTENCE_RECALL = 0.5         # 문장의 핵심어를 이 비율 이상 쓰면 그 문장을 기억한 것으로 본다
REVIEW_DAYS = [(0, "오늘"), (1, "내일"), (3, "3일 뒤"), (7, "1주 뒤")]  # 간격 반복 복습
SPEAK_CHARS_PER_SEC = 4.5  # 소리 내어 말할 때 1초에 읽는 글자 수 (대략)
STOPWORDS = {
    "그리고", "그래서", "하지만", "그런데", "그러나", "또한", "저는", "제가", "저희", "있습니다", "했습니다",
    "합니다", "입니다", "됩니다", "있었습니다", "것을", "것이", "것은", "통해", "위해", "대한", "때문에", "생각합니다",
}
PARTICLES = sorted(["을", "를", "이", "가", "은", "는", "에", "에서", "으로", "로", "와", "과", "도", "의",
                    "에게", "께서", "까지", "부터", "보다", "처럼", "이라", "라고", "이고", "하고"], key=len, reverse=True)


def _core(word: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", word)


def stem(word: str) -> str:
    """끝에 붙은 조사 하나를 뗀다 (남는 글자가 2자 이상일 때만). '테스트를' → '테스트'."""
    core = _core(word)
    for p in PARTICLES:
        if core.endswith(p) and len(core) - len(p) >= 2:
            return core[: -len(p)]
    return core


PREDICATE_ENDINGS = ("니다", "어요", "아요", "해요", "에요", "예요", "어서", "아서", "해서", "었고", "았고", "했고", "다")


def is_keyword(word: str) -> bool:
    """핵심어: 숫자가 들어 있거나, 조사를 떼고도 3자 이상이고, 흔한 말(STOPWORDS)이 아닌 단어.
    '진행했습니다' 같은 서술어는 말투만 달라도 틀린 것으로 잡히니 뺀다 (외울 건 내용)."""
    core = _core(word)
    if not core or core in STOPWORDS:
        return False
    if any(ch.isdigit() for ch in core):
        return True
    return len(stem(word)) >= 3 and not core.endswith(PREDICATE_ENDINGS)


def key_words(text: str) -> list[str]:
    """답에서 핵심어(조사 뗀 형태)를 나온 순서대로, 중복 없이."""
    return list(dict.fromkeys(stem(w) for w in text.split() if is_keyword(w)))


def skeleton(text: str) -> list[dict]:
    """뼈대 보기: 문장마다 그 문장의 핵심어."""
    return [{"sentence": s, "keys": key_words(s)} for s in split_sentences(text)]


def speak_seconds(text: str) -> int:
    return round(len(re.sub(r"\s", "", text)) / SPEAK_CHARS_PER_SEC)


def cloze(text: str, level: int) -> list[tuple[str, bool]]:
    """빈칸 채우기: (단어, 가림 여부) 목록. 핵심어 중 MEMO_LEVELS[level] 개마다 1개를 가린다."""
    step = MEMO_LEVELS.get(level, 1)
    out, nth = [], 0
    for word in text.split():
        hide = False
        if is_keyword(word):
            hide = nth % step == 0
            nth += 1
        out.append((word, hide))
    return out


def recall_check(original: str, attempt: str) -> dict:
    """실전 시뮬레이션 채점: 원래 답의 핵심어 중 몇 개를 기억해 썼는지 (조사 뗀 형태로 비교)."""
    keys = key_words(original)
    written = re.sub(r"\s", "", attempt)
    found = [k for k in keys if k in written]
    missing = [k for k in keys if k not in written]
    ratio = round(100 * len(found) / len(keys)) if keys else 0
    return {"total": len(keys), "found": found, "missing": missing, "recall": ratio}


def mark_words(text: str) -> list[tuple[str, str]]:
    """뼈대 보기 '전체 문장' 용: 단어마다 'key'(핵심어) 또는 'rest'(나머지 내용)."""
    return [(word, "key" if is_keyword(word) else "rest") for word in text.split()]


MEMO_TAGS = {1: "가볍게", 2: "절반", 3: "전부"}  # 빈칸 채우기 태그 (가리는 양). 아이콘은 화면에서만 붙인다


def step_label(index: int) -> str:
    mode, level = MEMO_STEPS[index]
    return MEMO_MODES[mode] + (f" {MEMO_TAGS[level]}" if level else "")


def fallback_step(recall: int) -> int | None:
    """실전 시뮬레이션이 덜 외워졌으면 돌아갈 단계 번호 (MEMO_STEPS). 통과면 None."""
    for limit, index in MEMO_FALLBACK:
        if recall < limit:
            return index
    return None


def next_step(mode: int, level: int | None) -> int | None:
    """지금 단계의 다음 단계 번호. 마지막(③)이면 None."""
    here = MEMO_STEPS.index((mode, level if mode == 1 else None))
    return here + 1 if here + 1 < len(MEMO_STEPS) else None


def sentence_recall(original: str, attempt: str) -> list[dict]:
    """문장 단위로 기억했는지: 원래 답의 문장마다 그 문장 핵심어를 SENTENCE_RECALL 이상 썼으면 기억한 것.
    핵심어가 없는 문장(짧은 맺음말 등)은 판단하지 않는다 (remembered=None)."""
    written = re.sub(r"\s", "", attempt)
    rows = []
    for sentence in split_sentences(original):
        keys = key_words(sentence)
        if not keys:
            rows.append({"sentence": sentence, "remembered": None})
            continue
        hit = sum(1 for k in keys if k in written)
        rows.append({"sentence": sentence, "remembered": hit / len(keys) >= SENTENCE_RECALL})
    return rows


def reading_speed(seconds: int, text: str) -> float:
    """대본을 보고 읽은 속도 (1초에 몇 자, 띄어쓰기 빼고)."""
    return len(re.sub(r"\s", "", text)) / max(seconds, 1)


def intro_feedback(seconds: int) -> tuple[str, str]:
    low, high = INTRO_TARGET
    if seconds < low:
        return "info", f"자기소개 목표({low}~{high}초)보다 {low - seconds}초 짧아요. 경험 하나를 조금 더 구체적으로 말해 보세요."
    if seconds > high:
        return "warning", f"자기소개 목표({low}~{high}초)보다 {seconds - high}초 길어요. 핵심어만 남기고 줄여 보세요."
    return "success", f"자기소개 목표({low}~{high}초) 안이에요."


# ── 말하기 모드: 1단계 대본 읽기 → 2단계 힌트(뼈대 → 빈칸 가볍게 · 절반 · 전부) → 3단계 대본 없이 ──
SPEAK_STEP_NAMES = {1: "1단계 · 대본 보고 읽기", 2: "2단계 · 힌트 보고 말하기", 3: "3단계 · 대본 없이 말하기"}
SPEAK_HINTS = {"skeleton": "뼈대", 1: MEMO_TAGS[1], 2: MEMO_TAGS[2], 3: MEMO_TAGS[3]}  # 2단계 힌트: 점점 적게
SPEAK_PHASES = ["read", "hint:skeleton", "hint:1", "hint:2", "hint:3", "speak"]  # 점진적으로 연습하는 순서


def speak_phase(step: int, hint=None) -> str:
    return {1: "read", 3: "speak"}.get(step) or f"hint:{hint}"


def phase_step(phase: str) -> tuple[int, object]:
    """'hint:2' → (2, 2), 'hint:skeleton' → (2, 'skeleton'), 'read' → (1, None)."""
    if phase.startswith("hint:"):
        value = phase.split(":", 1)[1]
        return 2, int(value) if value.isdigit() else value
    return (1 if phase == "read" else 3), None


def phase_label(phase: str) -> str:
    step, hint = phase_step(phase)
    name = SPEAK_STEP_NAMES[step]
    return f"{name} ({SPEAK_HINTS[hint]})" if step == 2 else name


def next_phase(phase: str) -> str | None:
    i = SPEAK_PHASES.index(phase)
    return SPEAK_PHASES[i + 1] if i + 1 < len(SPEAK_PHASES) else None


def easier_phase(phase: str) -> str | None:
    """한 단계 쉬운 연습 (대본에 더 가까운 쪽). 1단계면 None."""
    i = SPEAK_PHASES.index(phase)
    return SPEAK_PHASES[i - 1] if i > 0 else None


def phase_feedback(read_s: int | None, seconds: int, phase: str, text: str, question: str) -> list[tuple[str, str]]:
    """말하기 단계 결과 안내 [(종류, 문장)]. 2 · 3단계는 1단계(대본 읽기) 시간과 비교한다."""
    label = phase_label(phase)
    if phase == "read":
        return [("info", f"{label} {seconds}초 · 내 읽기 속도는 1초에 {reading_speed(seconds, text):.1f}자예요. "
                         "이제 2단계로 힌트를 보며 말해 보세요.")]
    if not read_s:
        return [("info", f"{label} {seconds}초. 먼저 1단계 대본 보고 읽기를 재면 얼마나 막혔는지 비교할 수 있어요.")]
    gap = seconds - read_s
    ratio = gap / read_s
    following, easier = next_phase(phase), easier_phase(phase)
    if ratio < -SPEAK_SMOOTH:
        messages = [("info", f"{label} {seconds}초 · 읽기보다 {-gap}초 빨라요. 빠뜨린 내용이 없는지 확인해 보세요.")]
    elif ratio <= SPEAK_SMOOTH:
        tail = f" {phase_label(following)} 로 넘어가 보세요." if following else " 대본 없이도 자연스럽게 말할 수 있어요."
        messages = [("success", f"{label} {seconds}초 · 읽기와 {abs(gap)}초 차이로 거의 막히지 않았어요.{tail}")]
    elif ratio <= SPEAK_STUCK:
        messages = [("warning", f"{label} {seconds}초 · 읽기보다 {gap}초(+{round(ratio * 100)}%) 더 걸렸어요. "
                                "막힌 곳을 떠올리며 같은 단계를 한 번 더 해 보세요.")]
    else:
        back = f" {phase_label(easier)} 로 돌아가 연습해 보세요." if easier else ""
        messages = [("warning", f"{label} {seconds}초 · 읽기보다 {gap}초(+{round(ratio * 100)}%) 더 걸려서 많이 막혔어요.{back}")]
    if phase == "speak" and "자기소개" in question:
        messages.append(intro_feedback(seconds))
    return messages


def review_schedule(today: date) -> list[tuple[str, date]]:
    return [(label, today + timedelta(days=d)) for d, label in REVIEW_DAYS]


def strategy_gap(scores: dict) -> dict:
    """기준별로 더 받을 수 있는 점수 (5점 만점 - 지금 점수). 0점 차이는 뺀다."""
    return {key: CRITERION_MAX - scores[key] for key in CRITERIA if scores[key] < CRITERION_MAX}


def summarize_strategy(raw: dict, scores: dict) -> list[dict]:
    """5점이 아닌 기준의 전략만, 기준 순서대로, 기준마다 2개까지. 더 받을 수 있는 점수는 코드가 붙인다."""
    gap = strategy_gap(scores)
    grouped = {key: [] for key in gap}
    for t in raw.get("tips", []):
        key = t.get("criterion")
        if key in grouped and len(grouped[key]) < MAX_TIPS_PER_CRITERION and str(t.get("tip", "")).strip():
            grouped[key].append({
                "action": str(t.get("action", "")),
                "target": str(t.get("target", "")).strip(),
                "tip": str(t.get("tip", "")).strip(),
            })
    return [
        {"criterion": key, "name": CRITERIA[key], "score": scores[key], "gain": gap[key], "tips": tips}
        for key, tips in grouped.items()
    ]


def load_precheck(path: Path = PRECHECK_PATH) -> list[dict]:
    """사전 탐색 체크리스트. 모르는 '못 찾으면' 값은 '마지막' 으로 본다."""
    df = pd.read_csv(path, encoding="utf-8-sig").fillna("")
    return [
        {
            "group": row["분류"],
            "item": row["항목"],
            "where": row["찾는 곳"],
            "timing": row["못 찾으면"] if row["못 찾으면"] in PRECHECK_TIMING else "마지막",
        }
        for _, row in df.iterrows()
    ]


def precheck_summary(items: list[dict], found: list[bool], missing: list[bool]) -> dict:
    """찾은 것 · 못 찾은 것 개수와, 못 찾은 것을 언제 확인할지 묶음."""
    later = {timing: [] for timing in PRECHECK_TIMING}
    for item, is_found, is_missing in zip(items, found, missing):
        if is_missing and not is_found:
            later[item["timing"]].append(item["item"])
    missing_count = sum(len(names) for names in later.values())
    return {"total": len(items), "found": sum(found), "missing": missing_count, "later": later}


def precheck_state(items: list[dict], found: list[bool], missing: list[bool], memos: list[str]) -> dict:
    """리포트 · 이어 하기용. 항목 글자를 key 로 저장한다 (CSV 순서가 바뀌어도 맞게 이어지도록)."""
    return {
        item["item"]: {"found": f, "missing": m, "memo": memo.strip()}
        for item, f, m, memo in zip(items, found, missing, memos)
        if f or m or memo.strip()
    }


def load_memo_strategy(path: Path = MEMO_STRATEGY_PATH) -> str:
    return path.read_text(encoding="utf-8")


def load_panel_rationale(path: Path = PANEL_RATIONALE_PATH) -> str:
    return path.read_text(encoding="utf-8")


def build_retry(profile: dict, question: dict, before: str, weak: str) -> str:
    return RETRY.format(
        persona=PERSONAS[profile["job"]],
        context=build_context(profile),
        question=question["question"],
        point=question["point"],
        before=before,
        weak=weak,
    )


def build_last_question(profile: dict) -> str:
    return LAST_QUESTION.format(context=build_context(profile))


def build_last_suggest(profile: dict) -> str:
    return LAST_SUGGEST.format(context=build_context(profile))


def summarize_last_suggest(raw: dict) -> list[tuple[str, str]]:
    questions = [str(q).strip() for q in raw.get("questions", []) if str(q).strip()]
    return list(zip(LAST_ANGLES, questions))


def build_highlight(profile: dict) -> str:
    return HIGHLIGHT.format(context=build_context(profile))


def split_sentences(text: str) -> list[str]:
    """문장 끝(. ! ? …) 뒤의 공백이나 줄바꿈에서 자른다."""
    parts = re.split(r"(?<=[.!?…。])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def build_highlight_input(blocks: list[dict]) -> tuple[str, list[list[int]]]:
    """blocks: [{question, point, sentences}]. 문장에 전체 번호(1부터)를 붙인다.
    돌려주는 numbers[i] 는 i번째 블록 문장들의 번호."""
    lines, numbers, no = [], [], 0
    for block in blocks:
        lines += [f"[질문] {block['question']}", f"[보는 점] {block['point']}"]
        ids = []
        for sentence in block["sentences"]:
            no += 1
            ids.append(no)
            lines.append(f"{no}) {sentence}")
        numbers.append(ids)
        lines.append("")
    return "\n".join(lines).strip(), numbers


def summarize_highlight(raw: dict) -> dict:
    """번호 → {tags(기준 순서대로, 중복 없음), why}. 모르는 기준은 버린다."""
    result = {}
    for item in raw.get("sentences", []):
        no = item.get("no")
        if not isinstance(no, int):
            continue
        tags = set(item.get("tags", []))
        result[no] = {"tags": [key for key in CRITERIA if key in tags], "why": str(item.get("why", "")).strip()}
    return result


def is_prompt_ready(prompt: str) -> bool:
    """프롬프트에 채우지 않은 빈칸(___)이 남아 있으면 쓰지 않는다."""
    return PROMPT_BLANK not in prompt


def summarize_last_question(raw: dict) -> dict:
    questions = [str(q).strip() for q in raw.get("questions", []) if str(q).strip()]
    return {
        "questions": list(zip(LAST_ANGLES, questions)),  # 3개까지, 관점과 짝지음
        "why": str(raw.get("why", "")).strip(),
    }


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
            f"[{names[m['role']]}] {plain(m['content'])}"
            for m in messages
            if m.get("q") == i and m.get("kind") != "question"
        ]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


ICON_CODE = re.compile(r":material/[a-z0-9_]+:\s?")


def plain(text: str) -> str:
    """화면용 아이콘 표기(:material/…:)를 뺀 글 (AI 에게는 보내지 않는다)."""
    return ICON_CODE.sub("", text)


def format_transcript(messages: list[dict]) -> str:
    """지금까지의 대화를 AI에게 넘길 글로 만든다."""
    names = {"assistant": "면접관", "user": "지원자"}
    return "\n".join(f"[{names[m['role']]}] {plain(m['content'])}" for m in messages)


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


# 위원 코치 피드백 (AI 호출 없음): 위원마다 PANEL_CRITERIA 에 가까운 기준 2개의 점수 변화로 고정 문장을 고른다.
# 첫 기준은 위원마다 달라서 4명이 기준 4개를 나눠 말한다 (같은 문장 되풀이 방지).
PANEL_FOCUS = {
    "실무 전문가": ["relevance", "specific"],      # 직무 지식 · 실제 업무에 쓸 경험
    "논리 분석가": ["evidence", "structure"],      # 주장과 근거 · 문제 → 원인 → 해결 → 결과
    "커뮤니케이션 전문가": ["structure", "relevance"],  # 결론부터 간결 · 질문 의도에 맞게
    "채용 담당자": ["specific", "relevance"],      # 성장 가능성을 보여 주는 실제 경험 · 회사 · 직무 적합성
}
COACH_UP = {
    "specific": "상황 · 숫자가 더 구체적으로 보여요.",
    "relevance": "직무와의 연결이 분명해졌어요.",
    "structure": "답의 흐름이 더 분명해졌어요.",
    "evidence": "근거와 확인 방법이 더 생겼어요.",
}
COACH_DOWN = {
    "specific": "구체적인 상황 · 숫자가 줄었어요. 지난 답의 숫자를 되살려 보세요.",
    "relevance": "직무와의 연결이 약해졌어요. 이 경험을 회사 업무와 이어 주세요.",
    "structure": "흐름이 흐려졌어요. 결론을 첫 문장에 두세요.",
    "evidence": "근거가 줄었어요. 데이터나 테스트 결과를 한 줄 넣어 보세요.",
}
COACH_SAME = {
    "specific": "숫자나 사례를 하나 더 넣으면 올라가요.",
    "relevance": "회사 · 직무와 연결하는 한 문장을 더해 보세요.",
    "structure": "결론 → 이유 → 결과 순서로 다시 배치해 보세요.",
    "evidence": "어떻게 확인했는지(테스트 · 데이터)를 넣어 보세요.",
}


def panel_coaching(before: dict, after: dict) -> list[dict]:
    """재도전 전 → 후 기준 점수로 위원 4명의 코칭 한 문장씩.
    위원마다 첫 기준(주 기준)으로 말한다. 주 기준이 서로 달라서 4명이 같은 말을 하지 않는다.
    둘째 기준은 changes 에 점수 변화만 함께 보여 준다."""
    rows = []
    for role, keys in PANEL_FOCUS.items():
        key = keys[0]
        changes = " · ".join(f"{CRITERIA[k]} {before[k]}→{after[k]}" for k in keys)
        if after[key] != before[key]:
            trend = "up" if after[key] > before[key] else "down"
            message = (COACH_UP if trend == "up" else COACH_DOWN)[key]
        else:
            trend = "same"
            message = COACH_SAME[key] if after[key] < CRITERION_MAX else f"{_topic(CRITERIA[key])} 만점이에요. 이대로 지켜 주세요."
        rows.append({"role": role, "changes": changes, "message": message, "trend": trend})
    return rows


def _topic(word: str) -> str:
    """은/는: 마지막 글자에 받침이 있으면 '은', 없으면 '는'."""
    last = word[-1]
    has_final = "가" <= last <= "힣" and (ord(last) - ord("가")) % 28 != 0
    return word + ("은" if has_final else "는")


def compare(before: dict, after: dict) -> dict:
    """전 → 후 점수 차이. before · after 는 기준별 점수 dict."""
    rows = [
        {"기준": name, "전": before[key], "후": after[key], "차이": after[key] - before[key]}
        for key, name in CRITERIA.items()
    ]
    before_score, after_score = answer_score(before), answer_score(after)
    return {"before": before_score, "after": after_score, "diff": after_score - before_score, "rows": rows}


def _cell(text: str) -> str:
    """마크다운 표 칸 안에서 | 와 줄바꿈이 표를 깨지 않게."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def _quote(text: str) -> list[str]:
    """여러 줄 글을 마크다운 인용(>)으로."""
    return [f"> {line}" if line.strip() else ">" for line in str(text).strip().splitlines()] or ["> (없음)"]


def next_round(previous: dict | None) -> int:
    """처음이면 1회차, 지난 리포트로 이어 하면 그 회차 + 1."""
    return min(previous["round"] + 1, MAX_ROUND) if previous else 1


def _file_part(text: str) -> str:
    """파일 이름에 쓸 수 없는 글자와 띄어쓰기를 _ 로 바꾼다."""
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "_", text.strip()).strip("._")
    return cleaned or "회사"


def report_file_name(company: str, job: str, round_no: int, day: date | None = None) -> str:
    """yymmdd-회사이름-직군-n회차-면접리포트.md (예: 261028-토스-디자인-2회차-면접리포트.md)"""
    day_text = (day or date.today()).strftime("%y%m%d")
    return f"{day_text}-{_file_part(company)}-{job}-{round_no}회차-면접리포트.md"


MAX_SESSION_MESSAGES = 40  # 면접 대화는 질문 5개 × (질문 · 답 · 꼬리 질문 · 답 · 반응) 안쪽


def session_data(
    messages: list[dict],
    evaluation: dict,
    retries: dict,
    retry_counts: dict | None = None,
    last_suggest: list | None = None,
    last_question: dict | None = None,
    understanding: int | None = None,
    retry_history: dict | None = None,
    clue_set: list[dict] | None = None,
    clue_round: int = 1,
    practice: list[dict] | None = None,
) -> dict:
    """'면접 없이 이어 하기' 용: 이 회차의 대화 · 평가 · 재도전(반영된 것 · 모든 기록) · 마지막 질문을 그대로 남긴다.
    practice: 연습 대본 [{question, script, round}] — 지난 회차 것까지 이어 붙인 목록 (merge_practice).
    평가는 AI 응답과 같은 모양으로 남겨서, 읽을 때 summarize_evaluation() 으로 다시 검증 · 계산한다."""
    return {
        "messages": [
            {"role": m["role"], "content": m["content"], "q": m.get("q"), "kind": m.get("kind")}
            for m in messages
        ],
        "evaluation": {
            "panel": [{k: m[k] for k in ("role", "against", "good", "score")} for m in evaluation["panel"]],
            "conflict": evaluation["conflict"],
            "agree": evaluation["agree"],
            "answers": [
                {"no": a["no"], **a["scores"], "weak": a["weak"], "rewrite": a["rewrite"], "check": a["check"]}
                for a in evaluation["answers"]
            ],
            "next": evaluation["next"],
        },
        "retries": {str(no): {"answer": r["answer"], **r["scores"], "weak": r["weak"]} for no, r in retries.items()},
        "retry_history": {
            str(no): [{"answer": r["answer"], **r["scores"], "weak": r["weak"]} for r in attempts]
            for no, attempts in (retry_history or {}).items()
        },
        "retry_counts": {str(no): n for no, n in (retry_counts or {}).items()},
        # 역전의 실마리: 회차와 지금 보고 있는 실마리 (질문 번호 · 찾을 때 점수 · 찾을 때 재도전 횟수만)
        "clues": {
            "round": clue_round,
            "set": [{k: cl[k] for k in ("no", "score", "retry_count")} for cl in clue_set] if clue_set is not None else None,
        },
        "last_suggest": [list(pair) for pair in (last_suggest or [])],
        "last_question": (
            {"questions": [list(p) for p in last_question["questions"]], "why": last_question["why"]}
            if last_question else None
        ),
        "understanding": understanding,
        "practice": [
            {"question": p["question"], "script": p["script"], "round": p["round"]} for p in (practice or [])
        ][:MAX_PRACTICE],
    }


MAX_PRACTICE = 40  # 리포트에 남기는 연습 대본 수 (질문 은행 한 분야 · 직군보다 넉넉히)


def saved_practice(reports: list[dict]) -> dict[str, dict]:
    """불러온 리포트들의 연습 대본: {질문 글: {script, round}}. 같은 질문이면 가장 최근 회차 대본.
    모양이 다른 칸은 건너뛴다 (연습 대본 기능 전 리포트에는 없다)."""
    saved = {}
    for report in reports:
        items = (report.get("session") or {}).get("practice")
        for p in items if isinstance(items, list) else []:
            if not (isinstance(p, dict) and isinstance(p.get("question"), str) and isinstance(p.get("script"), str)):
                continue
            text, script = p["question"].strip(), p["script"].strip()
            round_no = p.get("round") if isinstance(p.get("round"), int) else report.get("round", 1)
            if text and script and round_no >= saved.get(text, {}).get("round", 0):
                saved[text] = {"script": script, "round": round_no}
    return saved


def merge_practice(saved: dict[str, dict], current: dict[str, str], round_no: int) -> list[dict]:
    """리포트에 남길 연습 대본: 지난 회차 대본(saved) 위에 이번 회차에 고친 대본(current {질문 글: 대본})을 덮어쓴다."""
    merged = {text: dict(v) for text, v in saved.items()}
    for text, script in current.items():
        if text.strip() and script.strip():
            merged[text] = {"script": script.strip(), "round": round_no}
    rows = [{"question": t, **v} for t, v in merged.items()]
    return sorted(rows, key=lambda r: -r["round"])[:MAX_PRACTICE]  # 넘치면 최근 회차부터 남긴다


def _trim(value, depth: int = 0):
    """리포트에서 읽은 값: 글은 MAX_FIELD_CHARS 로 자르고, 목록 · 사전은 크기를 제한한다 (이상한 파일 대비)."""
    if depth > 6:  # session → evaluation → answers → 답 하나 → check → 글 (깊이 5)
        return None
    if isinstance(value, str):
        return value.strip()[:MAX_FIELD_CHARS]
    if isinstance(value, bool) or value is None or isinstance(value, (int, float)):
        return value
    if isinstance(value, list):
        return [_trim(v, depth + 1) for v in value[:MAX_SESSION_MESSAGES]]
    if isinstance(value, dict):
        return {str(k)[:40]: _trim(v, depth + 1) for k, v in list(value.items())[:MAX_SESSION_MESSAGES]}
    return None


def _parse_session(raw) -> dict | None:
    """숨은 데이터의 session 을 모양만 확인해서 읽는다. 없거나 모양이 다르면 None (면접 없이 이어 하기 불가)."""
    if not isinstance(raw, dict):
        return None
    raw = _trim(raw)
    messages = []
    for m in raw.get("messages") or []:
        if not isinstance(m, dict) or m.get("role") not in ("assistant", "user") or not isinstance(m.get("content"), str):
            continue
        q = m.get("q")
        messages.append({
            "role": m["role"],
            "content": m["content"],
            "q": q if isinstance(q, int) and 0 <= q < TOTAL_QUESTIONS else None,
            "kind": "question" if m.get("kind") == "question" else None,
        })
    evaluation = raw.get("evaluation")
    if not messages or not isinstance(evaluation, dict):
        return None
    return {**raw, "messages": messages}


def rebuild_clues(raw, evaluation: dict, retries: dict) -> dict:
    """리포트의 실마리 데이터로 실마리 회차 · 목록을 되살린다. 없거나 모양이 다르면 1회차 · 새로 찾기(None)."""
    if not isinstance(raw, dict):
        return {"clue_round": 1, "clue_set": None}
    clue_round = clamp(raw.get("round"), 1, 99) if isinstance(raw.get("round"), int) else 1
    items = raw.get("set")
    if not isinstance(items, list):
        return {"clue_round": clue_round, "clue_set": None}
    latest = {a["no"]: a for a in latest_answers(evaluation, retries)}
    order = list(CRITERIA)
    clues = []
    for it in items[:MAX_CLUES]:
        no = it.get("no") if isinstance(it, dict) else None
        if not isinstance(no, int) or no not in latest:
            return {"clue_round": clue_round, "clue_set": None}
        a = latest[no]
        key = min(order, key=lambda k: (a["scores"][k], order.index(k)))
        clues.append({
            "no": no, "question": a["question"], "score": clamp(it.get("score"), 0, ANSWER_MAX), "weak": a["weak"],
            "criterion": key, "name": CRITERIA[key], "criterion_score": a["scores"][key],
            "retry_count": clamp(it.get("retry_count"), 0, MAX_RETRIES),
        })
    return {"clue_round": clue_round, "clue_set": clues}


def rebuild_session(session: dict, questions: list[dict]) -> dict:
    """리포트의 session 으로 면접 끝난 상태를 다시 만든다. 점수 · 합계는 여기서 다시 검증 · 계산한다."""
    evaluation = summarize_evaluation(session["evaluation"], questions)
    def attempt(r) -> dict | None:
        return {"answer": r["answer"], **summarize_retry(r)} if isinstance(r, dict) and isinstance(r.get("answer"), str) else None

    def question_no(key) -> int | None:
        return int(key) if str(key).isdigit() and 1 <= int(key) <= TOTAL_QUESTIONS else None

    # 모든 재도전 기록. 기록이 없는 옛 리포트는 남아 있던 재도전 하나를 기록으로 쓴다.
    history = {}
    for key, items in (session.get("retry_history") or {}).items():
        attempts = [a for a in (attempt(r) for r in (items if isinstance(items, list) else [])) if a][:MAX_RETRIES]
        if question_no(key) and attempts:
            history[question_no(key)] = attempts
    for key, r in (session.get("retries") or {}).items():
        if question_no(key) and question_no(key) not in history and attempt(r):
            history[question_no(key)] = [attempt(r)]
    # 반영 점수는 기록에서 다시 고른다 (최고 점수 반영 · 옛 리포트의 낮은 재도전도 여기서 걸러진다)
    original = {a["no"]: a["score"] for a in evaluation["answers"]}
    retries = {}
    for no, attempts in history.items():
        best = reflected_retry(original[no], attempts)
        if best:
            retries[no] = best
    retry_counts = {
        int(k): clamp(v, 0, MAX_RETRIES)
        for k, v in (session.get("retry_counts") or {}).items()
        if str(k).isdigit() and 1 <= int(k) <= TOTAL_QUESTIONS
    }

    def pairs(items) -> list[tuple[str, str]]:
        return [
            (p[0], p[1]) for p in items or []
            if isinstance(p, list) and len(p) == 2 and p[0] in LAST_ANGLES and isinstance(p[1], str)
        ]

    last_question = session.get("last_question")
    if isinstance(last_question, dict):
        last_question = {"questions": pairs(last_question.get("questions")), "why": str(last_question.get("why") or "")}
    else:
        last_question = None
    understanding = session.get("understanding")
    return {
        "messages": session["messages"],
        "evaluation": evaluation,
        "retries": retries,
        "retry_history": history,
        "retry_counts": retry_counts,
        **rebuild_clues(session.get("clues"), evaluation, retries),
        "last_suggest": pairs(session.get("last_suggest")) or None,
        "last_question": last_question if last_question and last_question["questions"] else None,
        "understanding": clamp(understanding, 0, 100) if isinstance(understanding, int) else None,
    }


def report_data(
    profile: dict, questions: list[dict], evaluation: dict, retries: dict, round_no: int, precheck: dict, day: date,
    session: dict | None = None,
) -> dict:
    """다음 면접에서 이어 하기 위해 리포트에 숨겨 둘 데이터. 이 회차 데이터만 넣는다 (지난 회차는 넣지 않음).
    total_* · criteria_version · passed · session 은 나중에 더한 칸이라, 없는 옛 리포트도 그대로 읽힌다."""
    totals = total_scores(evaluation, retries)
    return {
        "session": session,
        "total_first": totals["first"],
        "total_latest": totals["latest"],
        "passed": verdict(totals, evaluation["panel_average"])["passed"],
        "verdict": verdict(totals, evaluation["panel_average"])["level"],
        "criteria_version": criteria_version(),
        "precheck": precheck,
        "version": REPORT_DATA_VERSION,
        "round": round_no,
        "date": day.isoformat(),
        "profile": {
            **{k: profile[k] for k in ("name", "job", "company", "company_desc", "experience")},
            "field": field_of(profile),
        },
        "questions": [{"type": q["type"], "question": q["question"]} for q in questions],
        "scores": [a["score"] for a in evaluation["answers"]],
        "panel_average": round(evaluation["panel_average"], 2),
        "next": evaluation["next"],
    }


def embed_report_data(data: dict) -> str:
    # '>' 를 > 로 바꿔 글 안의 '-->' 가 주석을 끝내지 않게 한다 (JSON 으로는 같은 값).
    payload = json.dumps(data, ensure_ascii=False).replace(">", "\\u003e")
    return f"<!-- {REPORT_DATA_TAG} {payload} -->"


def _text(value, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"리포트의 '{field}' 값을 읽지 못했어요.")
    return value.strip()[:MAX_FIELD_CHARS]


def parse_report(text: str) -> dict:
    """면접리포트.md 에서 숨겨 둔 데이터를 읽는다. 문제가 있으면 한국어 한 줄로 ValueError."""
    found = REPORT_DATA_RE.search(text)
    if not found:
        raise ValueError("이 파일에는 이어 하기 데이터가 없어요. 이 앱에서 받은 면접리포트.md 를 올려 주세요.")
    try:
        raw = json.loads(found.group(1))
    except json.JSONDecodeError:
        raise ValueError("리포트의 이어 하기 데이터가 깨져 있어요.") from None
    if not isinstance(raw, dict) or raw.get("version") != REPORT_DATA_VERSION:
        raise ValueError("지원하지 않는 리포트 형식이에요.")

    p = raw.get("profile") or {}
    profile = {k: _text(p.get(k), k) for k in ("name", "job", "company", "company_desc", "experience")}
    profile["field"] = field_of(p)  # 분야가 없거나 모르는 값이면 '공통'
    if profile["job"] not in JOBS:
        raise ValueError("리포트의 직군을 알 수 없어요.")

    questions = [_text((q or {}).get("question"), "question") for q in raw.get("questions", [])]
    scores = [clamp(s, 0, ANSWER_MAX) for s in raw.get("scores", [])]
    try:
        panel_average = max(0.0, min(float(PANEL_MAX), float(raw.get("panel_average", 0))))
    except (TypeError, ValueError):
        panel_average = 0.0
    precheck = {}
    raw_precheck = raw.get("precheck") or {}  # 체크리스트 기능 전 리포트에는 없다
    if isinstance(raw_precheck, dict):
        for name, value in list(raw_precheck.items())[:MAX_PRECHECK_ITEMS]:
            if isinstance(name, str) and isinstance(value, dict):
                precheck[name.strip()[:MAX_FIELD_CHARS]] = {
                    "found": value.get("found") is True,
                    "missing": value.get("missing") is True,
                    "memo": value["memo"].strip()[:MAX_FIELD_CHARS] if isinstance(value.get("memo"), str) else "",
                }
    total_latest = raw.get("total_latest")  # 종합 점수 기능 전 리포트에는 없다
    version = raw.get("criteria_version")
    return {
        "session": _parse_session(raw.get("session")),  # 결과 저장 기능 전 리포트는 None
        "total_latest": clamp(total_latest, 0, TOTAL_MAX) if isinstance(total_latest, int) else None,
        "criteria_version": version.strip()[:16] if isinstance(version, str) else "",
        "precheck": precheck,
        "round": clamp(raw.get("round", 1), 1, MAX_ROUND),
        "date": _text(raw.get("date", ""), "date"),
        "profile": profile,
        "questions": questions,
        "scores": scores,
        "panel_average": panel_average,
        "next": [_text(n, "next") for n in raw.get("next", []) if isinstance(n, str)][:MAX_NEXT],
    }


def match_questions(df: pd.DataFrame, job: str, texts: list[str]) -> list[dict] | None:
    """지난 리포트의 질문을 질문 은행에서 다시 찾는다. 하나라도 없으면 None (새 질문을 쓴다)."""
    bank = df[df["직군"].isin(["공통", job])]
    picked = []
    for text in texts:
        rows = bank[bank["질문"] == text]
        if rows.empty:
            return None
        picked.append(question_row(rows.iloc[0]))
    return picked if len(picked) == TOTAL_QUESTIONS else None


def criteria_changed(previous: dict) -> bool:
    """지난 회차와 평가 기준이 다른가. 기준 버전이 없는 옛 리포트는 알 수 없으니 False."""
    return bool(previous.get("criteria_version")) and previous["criteria_version"] != criteria_version()


def compare_previous(previous: dict, evaluation: dict, questions: list[dict], retries: dict | None = None) -> dict:
    """지난 면접 → 이번 면접. 같은 질문 글이면 질문별 점수도 비교한다.
    종합 점수는 지난 리포트에 있을 때만 비교한다 (옛 리포트는 None)."""
    before_by_text = dict(zip(previous["questions"], previous["scores"]))
    rows = []
    for a in evaluation["answers"]:
        text = questions[a["no"] - 1]["question"]
        if text in before_by_text:
            before = before_by_text[text]
            rows.append({"질문": f"{a['no']}. {text}", "지난": before, "이번": a["score"], "차이": a["score"] - before})
    return {
        "round": previous["round"],
        "date": previous["date"],
        "panel_before": previous["panel_average"],
        "panel_after": evaluation["panel_average"],
        "panel_diff": evaluation["panel_average"] - previous["panel_average"],
        "total_before": previous.get("total_latest"),
        "total_after": total_scores(evaluation, retries or {})["latest"],
        "criteria_changed": criteria_changed(previous),
        "rows": rows,
    }


def clue_status(evaluation: dict | None, retries: dict, retry_counts: dict,
                clue_set: list[dict] | None, clue_round: int = 1) -> dict | None:
    """지금 실마리 회차의 진행: {round, total, done}. 실마리가 없으면(모두 만점 · 기회 소진) total 0. 평가 전이면 None."""
    if not evaluation:
        return None
    clues = clue_set if clue_set is not None else pick_clues(evaluation, retries=retries, retry_counts=retry_counts)
    rows = clue_progress(clues, evaluation, retries, retry_counts)["rows"]
    return {"round": clue_round, "total": len(rows), "done": sum(r["retried"] for r in rows), "rows": rows}


STEP_NAMES = ["면접", "평가", "재도전", "최종 결과", "암기", "점검하기", "리포트"]  # 탭 6개 순서 + 리포트 버튼


def report_checklist(
    messages: list[dict], evaluation: dict | None, clues: dict | None, verdict_open: bool, memo: dict | None,
    last_suggest: list | None, last_question: dict | None,
    precheck_items: list[dict] | None, precheck: dict | None, report_done: bool,
) -> list[dict]:
    """단계 체크리스트: 탭 7개와 같은 순서 · 같은 이름. 위쪽 진행 막대와 리포트가 같은 목록을 쓴다 (앱이 자동 표시).
    하위 항목이 있는 단계(재도전 · 암기 · 점검하기)는 sub 에 나눠 담는다. optional: 안 해도 되는 단계.
    clues = clue_status() · memo = 암기 기록 요약 {speak, edited, checked}."""
    answered = sum(bool(answer_text(messages, i).strip()) for i in range(TOTAL_QUESTIONS))

    # 재도전: 지금 실마리 회차를 모두 재도전하면 완료. 실마리마다 하위 항목
    if not evaluation or clues is None:
        retry = {"done": False, "detail": "평가 뒤에 열려요", "sub": []}
    elif not clues["total"]:  # 모두 만점이거나 재도전 기회를 다 씀
        retry = {"done": True, "detail": "남은 실마리 없음", "sub": []}
    else:
        retry = {
            "done": clues["done"] == clues["total"],
            "detail": f"역전의 실마리 {clues['round']}회차 · 완료 {clues['done']}/{clues['total']}",
            "sub": [
                {"item": f"질문 {r['no']}", "done": r["retried"],
                 "detail": f"{r['before']} → {r['after']}점" if r["retried"] else "아직 재도전 전"}
                for r in clues["rows"]
            ],
        }

    memo = {"speak": 0, "edited": 0, "checked": 0, **(memo or {})}
    found = sum(1 for it in (precheck_items or []) if (precheck or {}).get(it["item"], {}).get("found"))
    total_items = len(precheck_items or [])
    rows = [
        {"done": answered == TOTAL_QUESTIONS, "detail": f"답변 {answered}/{TOTAL_QUESTIONS}", "optional": False, "sub": []},
        {"done": bool(evaluation), "detail": "위원 4명" if evaluation else "", "optional": False, "sub": []},
        {**retry, "optional": True},
        {"done": bool(verdict_open), "detail": "", "optional": False, "sub": []},
        {"done": memo["speak"] > 0 or memo["checked"] > 0, "detail": "", "optional": True, "sub": [
            {"item": "대본 고치기", "done": memo["edited"] > 0,
             "detail": f"고친 질문 {memo['edited']}개" if memo["edited"] else ""},
            {"item": "텍스트 연습", "done": memo["checked"] > 0,
             "detail": f"실전 시뮬레이션 {memo['checked']}개 질문" if memo["checked"] else ""},
            {"item": "말하기 연습", "done": memo["speak"] > 0, "detail": f"{memo['speak']}번" if memo["speak"] else ""},
        ]},
        {"done": bool(last_suggest or last_question), "detail": "", "optional": True, "sub": [
            {"item": "사전 정보 탐색", "done": total_items > 0 and found == total_items,
             "detail": f"찾음 {found}/{total_items}" if total_items else ""},
            {"item": "추천 질문 받기", "done": bool(last_suggest), "detail": ""},
            {"item": "내 질문 다듬기", "done": bool(last_question), "detail": ""},
        ]},
        {"done": bool(report_done), "detail": "면접리포트.md 받기", "optional": False, "sub": []},
    ]
    # 리포트는 탭이 아니라 위쪽 버튼이라 번호를 붙이지 않는다 (step None)
    return [{"step": i + 1 if i < len(STEP_NAMES) - 1 else None, "item": name, **row}
            for i, (name, row) in enumerate(zip(STEP_NAMES, rows))]


def checklist_summary(rows: list[dict]) -> str:
    """'7단계 중 n단계 완료 · 남은 단계 n개' (진행 막대 · 체크리스트 · 리포트가 같은 문장을 쓴다)."""
    done = sum(r["done"] for r in rows)
    left = len(rows) - done
    return f"{len(rows)}단계 중 {done}단계 완료 · 남은 단계 {left}개" if left else f"{len(rows)}단계를 모두 마쳤어요"


def checklist_report_lines(rows: list[dict]) -> list[str]:
    """리포트의 단계 체크리스트 (마크다운 작업 목록: GitHub · VS Code 미리보기에서 읽기 전용 체크 상자로 보인다)."""
    lines = [f"### 단계 체크리스트 · {checklist_summary(rows)} (앱이 자동으로 표시)", ""]
    for r in rows:
        detail = f" ({r['detail']})" if r["detail"] else ""
        number = f"{r['step']}. " if r["step"] else ""
        lines.append(f"- [{'x' if r['done'] else ' '}] {number}{r['item']}{detail}{' · 선택' if r['optional'] else ''}")
        for s in r["sub"]:
            sub_detail = f" ({s['detail']})" if s["detail"] else ""
            lines.append(f"  - [{'x' if s['done'] else ' '}] {s['item']}{sub_detail}")
    return lines + [""]


def precheck_report_lines(items: list[dict], precheck: dict) -> list[str]:
    """리포트의 '사전 정보 탐색' 섹션. 지금 체크리스트 항목 순서대로."""
    found = [it for it in items if precheck.get(it["item"], {}).get("found")]
    missing = [it for it in items if it not in found and precheck.get(it["item"], {}).get("missing")]
    todo = [it for it in items if it not in found and it not in missing]
    lines = [f"## 6. 사전 정보 탐색 (찾음 {len(found)}/{len(items)})", ""]

    lines += ["**찾은 정보**", ""]
    lines += [f"- {it['item']}: {_cell(precheck[it['item']]['memo']) or '(메모 없음)'}" for it in found] or ["- (없음)"]

    lines += ["", "**못 찾은 정보**", ""]
    if missing:
        for timing, label in PRECHECK_LATER_LABEL.items():
            names = [it["item"] for it in missing if it["timing"] == timing]
            if names:
                lines.append(f"- {label}: " + " · ".join(names))
    else:
        lines.append("- (없음)")

    lines += ["", "**아직 안 찾아본 정보**", ""]
    lines += [f"- {it['item']} — 찾는 곳: {it['where']}" for it in todo] or ["- (없음)"]
    return lines


def build_report(
    profile: dict,
    questions: list[dict],
    evaluation: dict,
    retries: dict,
    messages: list[dict],
    last_suggest: list[tuple[str, str]] | None = None,
    last_question: dict | None = None,
    previous: dict | None = None,
    round_no: int = 1,
    precheck_items: list[dict] | None = None,
    precheck: dict | None = None,
    updated_at: str | None = None,
    day: date | None = None,
    retry_counts: dict | None = None,
    understanding: int | None = None,
    retry_history: dict | None = None,
    clue_set: list[dict] | None = None,
    clue_round: int = 1,
    memo: dict | None = None,
    verdict_open: bool = False,
    practice: list[dict] | None = None,
) -> str:
    """면접리포트.md. 재도전은 최고 점수만 반영하고, 반영되지 않은 재도전은 접기(<details>)로 남긴다.
    숫자는 모두 이 파일에서 계산한 값만 쓴다 (AI가 쓴 합계 · 숫자는 넣지 않음).
    AI가 쓴 글은 'AI 의견' 으로 구분해 넣는다. 끝에는 이 회차의 이어 하기 데이터를 숨겨 둔다.
    day 는 사용자 시간대의 오늘 (배포 서버 날짜는 UTC 라서 하루 다를 수 있다)."""
    day = day or date.today()
    criteria = list(CRITERIA.values())
    lines = [
        f"# 면접 리포트 · {round_no}회차",
        "",
        f"- 회차: {round_no}회차",
        f"- 이름: {profile['name']}",
        f"- 분야: {field_of(profile)}",
        f"- 직군: {profile['job']} 신입",
        f"- 회사: {profile['company']} ({profile['company_desc']})",
        f"- 날짜: {day.isoformat()}",
        *([f"- 마지막 업데이트: {updated_at}"] if updated_at else []),
        "",
        "> 점수는 모두 앱이 계산한 값이에요. **AI 의견** 표시가 붙은 글은 AI가 쓴 것이라 사실인지 직접 확인해 주세요.",
        "",
        # 리포트 파일이 곧 '리포트 받기' 라서 7단계는 완료로 적는다
        *checklist_report_lines(report_checklist(
            messages, evaluation, clue_status(evaluation, retries, retry_counts or {}, clue_set, clue_round),
            verdict_open, memo, last_suggest, last_question, precheck_items, precheck, report_done=True,
        )),
        "## 1. 점수",
        "",
        "### 위원 평가 (0~10)",
        "",
        "| 위원 | 점수 |",
        "| --- | --- |",
    ]
    lines += [f"| {m['role']} | {m['score']} |" for m in evaluation["panel"]]
    lines += [
        "",
        f"**위원 평균: {evaluation['panel_average']:.1f} / {PANEL_MAX}**",
        "",
        f"### 답변 점수 (기준 4개 합, 0~{ANSWER_MAX})",
        "",
        "| 질문 | " + " | ".join(criteria) + " | 점수 |",
        "| --- |" + " --- |" * (len(criteria) + 1),
    ]
    for a in evaluation["answers"]:
        cells = " | ".join(str(a["scores"][key]) for key in CRITERIA)
        lines.append(f"| {a['no']}. {_cell(questions[a['no'] - 1]['question'])} | {cells} | {a['score']} |")

    by_no = {a["no"]: a for a in evaluation["answers"]}
    diffs = {no: compare(by_no[no]["scores"], retries[no]["scores"]) for no in sorted(retries)}
    # 기록이 없으면(옛 호출) 반영된 재도전만 기록으로 본다
    history = retry_history if retry_history is not None else {no: [r] for no, r in retries.items()}
    fails = {no: failed_retries(by_no[no]["score"], attempts) for no, attempts in history.items() if attempts}
    lines += ["", f"### 재도전 전 → 후 (0~{ANSWER_MAX}) · 최고 점수 반영", ""]
    if not fails:
        lines.append("재도전 기록 없음")
    else:
        lines += ["| 질문 | 전 | 후 (반영) | 차이 | 재도전 | 반영 안 된 재도전 |", "| --- | --- | --- | --- | --- | --- |"]
        for no in sorted(fails):
            before = by_no[no]["score"]
            after = retries[no]["score"] if no in retries else before
            lines.append(
                f"| {no}. {_cell(questions[no - 1]['question'])} | {before} | {after} | {after - before:+d} "
                f"| {len(history[no])}번 | {len(fails[no])}번 |"
            )

    totals = total_scores(evaluation, retries)
    result = verdict(totals, evaluation["panel_average"])
    lines += [
        "",
        f"### 종합 점수 (0~{TOTAL_MAX})",
        "",
        f"- 최초 종합: {totals['first']}",
        f"- 최신 종합 (재도전 반영): {totals['latest']} ({totals['diff']:+d})",
        f"- 모의면접 판정: **{result['label']}** "
        f"(합격: 최신 종합 {PASS_TOTAL} 이상 · 위원 평균 {PASS_PANEL:.1f} 이상 / "
        f"합격 후보: 최신 종합 {CANDIDATE_TOTAL} 이상 · 위원 평균 {CANDIDATE_PANEL:.1f} 이상)",
        "- 이 판정은 AI 모의면접 학습 지표이며 실제 채용 결과와 무관해요.",
    ]

    if previous:
        prev = compare_previous(previous, evaluation, questions, retries)
        lines += [
            "",
            f"### 지난 면접({prev['round']}회차 · {prev['date']})과 비교",
            "",
            f"- 위원 평균: {prev['panel_before']:.1f} → {prev['panel_after']:.1f} ({prev['panel_diff']:+.1f})",
        ]
        if prev["total_before"] is not None:
            lines.append(
                f"- 최신 종합: {prev['total_before']} → {prev['total_after']} ({prev['total_after'] - prev['total_before']:+d})"
            )
        if prev["criteria_changed"]:
            lines.append("- **주의:** 지난 회차와 평가 기준이 달라서 점수 비교가 정확하지 않을 수 있어요.")
        if prev["rows"]:
            lines += ["", "| 질문 | 지난 | 이번 | 차이 |", "| --- | --- | --- | --- |"]
            lines += [f"| {_cell(r['질문'])} | {r['지난']} | {r['이번']} | {r['차이']:+d} |" for r in prev["rows"]]
        else:
            lines.append("- 지난 면접과 같은 질문이 없어서 질문별 비교는 없어요.")

    # ── 질문별 기록: 내 답 원문 + AI 의견 ──
    lines += ["", "## 2. 질문별 기록", ""]
    for a in evaluation["answers"]:
        no = a["no"]
        lines += [f"### 질문 {no}. {questions[no - 1]['question']} ({a['score']}/{ANSWER_MAX}점)", ""]
        # 대화 순서대로: 내 답 → 면접관(꼬리 질문 · 반응) → 내 답
        for m in messages:
            if m.get("q") != no - 1 or m.get("kind") == "question":
                continue
            if m["role"] == "user":
                lines += ["**내 답**", ""] + _quote(m["content"]) + [""]
            else:
                lines += [f"*면접관:* {m['content']}", ""]
        lines += [f"**AI 의견 · 가장 약한 점:** {a['weak']}", ""]
        example = questions[no - 1].get("example", "")
        if a["score"] < ANSWER_MAX and example:
            lines += ["**만점 예시 답안** (가상 지원자 · 질문 은행에 미리 적어 둔 예시라 내 경험 · 숫자와 무관해요)", ""]
            lines += _quote(example) + [""]
        if no in retries:
            diff = diffs[no]
            lines += [f"**재도전한 답 · 최고 점수 반영** ({diff['before']} → {diff['after']}점, {diff['diff']:+d})", ""]
            lines += _quote(retries[no]["answer"])
            lines += ["", f"**AI 의견 · 재도전 답의 약한 점:** {retries[no]['weak']}", ""]
        elif fails.get(no):
            lines += [f"재도전 {len(fails[no])}번 모두 처음 점수({a['score']}점)보다 높지 않아서 처음 점수를 반영했어요.", ""]
        if fails.get(no):
            # 접기: GitHub · VS Code 미리보기 등에서 눌러 펼친다. 안쪽 마크다운이 보이도록 앞뒤에 빈 줄을 둔다.
            lines += ["<details>", f"<summary>반영 안 된 재도전 {len(fails[no])}번 보기</summary>", ""]
            for n, r in fails[no]:
                lines += [f"**{n}번째 재도전** ({a['score']} → {r['score']}점, {r['score'] - a['score']:+d})", ""]
                lines += _quote(r["answer"])
                lines += ["", f"**AI 의견 · 약한 점:** {r['weak']}", ""]
            lines += ["</details>", ""]

    # ── 위원회 의견 ──
    lines += ["## 3. 위원회 의견 (AI 의견)", ""]
    for m in evaluation["panel"]:
        lines += [
            f"- **{m['role']}** ({m['score']}점)",
            f"  - 평가 기준: {PANEL_CRITERIA[m['role']]}",
            f"  - 뽑지 말아야 할 이유: {m['against']}",
            f"  - 좋은 점: {m['good']}",
        ]
    lines += ["", f"- **판단이 갈린 곳:** {evaluation['conflict']}", f"- **모두 같은 판단:** {evaluation['agree']}", ""]

    lines += ["## 4. 다음 연습에서 고칠 것 (AI 의견)", ""]
    lines += [f"{i}. {item}" for i, item in enumerate(evaluation["next"], 1)] or ["(없음)"]

    # ── 마지막 질문 ──
    if last_suggest or last_question:
        lines += ["", "## 5. 마지막에 할 질문 (AI 의견)", ""]
        if last_suggest:
            lines += ["**추천 질문**", ""] + [f"- ({angle}) {q}" for angle, q in last_suggest] + [""]
        if last_question:
            lines += ["**내 질문을 다듬은 질문**", ""] + [f"- ({angle}) {q}" for angle, q in last_question["questions"]]
            if last_question["why"]:
                lines += ["", f"원래 질문에서 빠진 것: {last_question['why']}"]

    precheck = precheck or {}
    if precheck_items:
        lines += ["", *precheck_report_lines(precheck_items, precheck)]

    session = session_data(messages, evaluation, retries, retry_counts, last_suggest, last_question, understanding, history,
                           clue_set, clue_round, practice)
    lines += ["", embed_report_data(report_data(profile, questions, evaluation, retries, round_no, precheck, day, session))]
    return "\n".join(lines) + "\n"


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
