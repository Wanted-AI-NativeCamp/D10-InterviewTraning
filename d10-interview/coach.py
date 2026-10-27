# 질문 고르기 · 숫자 규칙 · 프롬프트 칸 채우기 · 리포트. AI 호출은 하지 않는다.
import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path

import pandas as pd

from prompts import (
    CONTEXT,
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
# 합격 후보 = 종합 PASS_TOTAL 이상 + 위원 평균 CANDIDATE_PANEL 이상 PASS_PANEL 미만
PASS_TOTAL = 70        # 최신 종합 점수(0~100) 이상
PASS_PANEL = 9.0       # 합격선: 위원 평균(0~10)
CANDIDATE_PANEL = 7.0  # 합격 후보선: 위원 평균(0~10)
VERDICT_LABELS = {"pass": "합격", "candidate": "합격 후보", "more": "추가 학습 필요"}
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


def pick_clues(evaluation: dict, count: int = MAX_CLUES) -> list[dict]:
    """역전의 실마리: 만점이 아닌 답 중 가장 낮은 답 count 개(같은 점수면 앞 번호)와
    각 답의 가장 낮은 기준 1개(같으면 기준 순서). 모두 만점이면 빈 목록."""
    order = list(CRITERIA)
    candidates = sorted(
        (a for a in evaluation["answers"] if a["score"] < ANSWER_MAX), key=lambda x: (x["score"], x["no"])
    )
    clues = []
    for a in candidates[:count]:
        key = min(order, key=lambda k: (a["scores"][k], order.index(k)))
        clues.append({
            "no": a["no"], "question": a["question"], "score": a["score"], "weak": a["weak"],
            "criterion": key, "name": CRITERIA[key], "criterion_score": a["scores"][key],
        })
    return clues


def verdict(totals: dict, panel_average: float) -> dict:
    """최종 판결: pass(합격) · candidate(합격 후보) · more(추가 학습 필요).
    short 는 '다음 단계' 까지 모자란 점수 (합격이면 빈 목록)."""
    total_ok = totals["latest"] >= PASS_TOTAL
    if total_ok and panel_average >= PASS_PANEL:
        level = "pass"
    elif total_ok and panel_average >= CANDIDATE_PANEL:
        level = "candidate"
    else:
        level = "more"

    target_panel = PASS_PANEL if level == "candidate" else CANDIDATE_PANEL
    short = []
    if level != "pass":
        if not total_ok:
            short.append(f"종합 점수 {PASS_TOTAL - totals['latest']}점")
        if panel_average < target_panel:
            # 0.1 단위로 올림 (8.99 처럼 바로 아래일 때 '0.0점 부족' 으로 보이지 않게)
            gap = math.ceil(round((target_panel - panel_average) * 10, 6)) / 10
            short.append(f"위원 평균 {gap:.1f}점")
    return {
        "level": level, "label": VERDICT_LABELS[level], "passed": level == "pass",
        "total": totals["latest"], "panel": panel_average, "short": short,
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


def report_data(
    profile: dict, questions: list[dict], evaluation: dict, retries: dict, round_no: int, precheck: dict, day: date
) -> dict:
    """다음 면접에서 이어 하기 위해 리포트에 숨겨 둘 데이터. 이 회차 데이터만 넣는다 (지난 회차는 넣지 않음).
    total_* · criteria_version · passed 는 나중에 더한 칸이라, 없는 옛 리포트도 그대로 읽힌다."""
    totals = total_scores(evaluation, retries)
    return {
        "total_first": totals["first"],
        "total_latest": totals["latest"],
        "passed": verdict(totals, evaluation["panel_average"])["passed"],
        "verdict": verdict(totals, evaluation["panel_average"])["level"],
        "criteria_version": criteria_version(),
        "precheck": precheck,
        "version": REPORT_DATA_VERSION,
        "round": round_no,
        "date": day.isoformat(),
        "profile": {k: profile[k] for k in ("name", "job", "company", "company_desc", "experience")},
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
        row = rows.iloc[0]
        picked.append({"type": row["유형"], "question": row["질문"], "point": row["보는 점"]})
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
) -> str:
    """면접리포트.md.
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
        f"- 직군: {profile['job']} 신입",
        f"- 회사: {profile['company']} ({profile['company_desc']})",
        f"- 날짜: {day.isoformat()}",
        *([f"- 마지막 업데이트: {updated_at}"] if updated_at else []),
        "",
        "> 점수는 모두 앱이 계산한 값이에요. **AI 의견** 표시가 붙은 글은 AI가 쓴 것이라 사실인지 직접 확인해 주세요.",
        "",
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
    lines += ["", f"### 재도전 전 → 후 (0~{ANSWER_MAX})", ""]
    if not diffs:
        lines.append("재도전 기록 없음")
    else:
        lines += ["| 질문 | 전 | 후 | 차이 |", "| --- | --- | --- | --- |"]
        for no, diff in diffs.items():
            lines.append(
                f"| {no}. {_cell(questions[no - 1]['question'])} | {diff['before']} | {diff['after']} | {diff['diff']:+d} |"
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
        f"합격 후보: 최신 종합 {PASS_TOTAL} 이상 · 위원 평균 {CANDIDATE_PANEL:.1f} 이상)",
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
            lines.append("- ⚠️ 지난 회차와 평가 기준이 달라서 점수 비교가 정확하지 않을 수 있어요.")
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
        if a["needs_rewrite"]:
            lines += ["**AI 의견 · 고친 답**", ""] + _quote(a["rewrite"]) + [""]
            if a["check"]:
                lines += ["**사람이 확인할 것**", ""] + [f"- {fact}" for fact in a["check"]] + [""]
        if no in retries:
            diff = diffs[no]
            lines += [f"**재도전한 답** ({diff['before']} → {diff['after']}점, {diff['diff']:+d})", ""]
            lines += _quote(retries[no]["answer"])
            lines += ["", f"**AI 의견 · 재도전 답의 약한 점:** {retries[no]['weak']}", ""]

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

    lines += ["", embed_report_data(report_data(profile, questions, evaluation, retries, round_no, precheck, day))]
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
