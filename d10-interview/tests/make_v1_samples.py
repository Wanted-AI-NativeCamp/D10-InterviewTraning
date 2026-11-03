# Markdown v1 기준 샘플 만들기 (P0-01).
# 지금 코드(coach.build_report · report_data)로 v1 리포트와 기준값(expected/*.json)을 만든다.
# 저장 형식을 바꾼 뒤에는 다시 돌리지 않는다 — 이 파일들은 '변경 전 v1' 의 기준이다.
# 실행: d10-interview 폴더에서  python tests/make_v1_samples.py
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import coach  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "v1"
DAY = date(2026, 11, 2)
UPDATED_AT = "2026-11-02 12:00"


def mock() -> dict:
    return json.loads((ROOT / "data" / "mock_perfect.json").read_text(encoding="utf-8"))


def write(folder: str, name: str, text: str):
    path = FIXTURES / folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def report(raw: dict, *, round_no: int, profile: dict, retry_history: dict, retry_counts: dict,
           clue_set: list | None, precheck: dict, practice: list, past_hidden: list) -> str:
    """앱의 build_current_report 와 같은 인자 모양으로 리포트를 만든다 (평가 · 재도전은 코드가 다시 계산)."""
    session = coach._parse_session(raw["session"])
    questions = coach.match_questions(coach.load_questions(), profile["job"], raw["questions"])
    evaluation = coach.summarize_evaluation(session["evaluation"], questions)
    retries = {}
    for no, attempts in retry_history.items():
        best = coach.reflected_retry(evaluation["answers"][no - 1]["score"], attempts)
        if best:
            retries[no] = best
    return coach.build_report(
        profile, questions, evaluation, retries, session["messages"],
        last_suggest=None, last_question=None, previous=None, round_no=round_no,
        precheck_items=coach.load_precheck(), precheck=precheck, updated_at=UPDATED_AT, day=DAY,
        retry_counts=retry_counts, understanding=session.get("understanding"), retry_history=retry_history,
        clue_set=clue_set, clue_round=1, memo=None, verdict_open=False, practice=practice, past_hidden=past_hidden,
    )


def attempt(answer: str, s: int, r: int, st: int, e: int, weak: str) -> dict:
    """재도전 한 번 (앱이 state.retry_history 에 넣는 모양: summarize_retry 결과 + answer)."""
    return {"answer": answer, **coach.summarize_retry(
        {"specific": s, "relevance": r, "structure": st, "evidence": e, "weak": weak})}


def no_retry() -> str:
    """정상 v1 · 재도전 없음: 개발용 만점 모의 데이터 그대로."""
    raw = mock()
    return report(raw, round_no=1, profile=raw["profile"], retry_history={}, retry_counts={},
                  clue_set=None, precheck={}, practice=[], past_hidden=[])


def with_retry() -> str:
    """정상 v1 · 재도전 있음: 2 · 3번 답 점수를 낮추고 재도전 기록(반영된 것 · 반영 안 된 것)을 넣는다.
    사전 탐색 체크 · 연습 대본 · 지운 지난 답 칸도 채워 v1 의 모든 칸을 쓴다."""
    raw = mock()
    answers = raw["session"]["evaluation"]["answers"]
    answers[1].update(specific=2, relevance=3, structure=2, evidence=1, weak="(예시) 근거가 약해요.")
    answers[2].update(specific=3, relevance=3, structure=3, evidence=2, weak="(예시) 결과가 빠졌어요.")
    history = {
        2: [attempt("(예시) 2번 재도전 1", 2, 3, 2, 1, "(예시) 그대로예요."),       # 처음과 같은 점수 → 반영 안 됨
            attempt("(예시) 2번 재도전 2", 4, 4, 4, 3, "(예시) 좋아졌어요.")],      # 더 높음 → 반영
        3: [attempt("(예시) 3번 재도전 1", 2, 2, 2, 2, "(예시) 오히려 낮아졌어요.")],  # 더 낮음 → 반영 안 됨
    }
    counts = {2: 2, 3: 1}
    questions = coach.match_questions(coach.load_questions(), raw["profile"]["job"], raw["questions"])
    evaluation = coach.summarize_evaluation(raw["session"]["evaluation"], questions)
    clues = coach.pick_clues(evaluation, retries={}, retry_counts={})  # 재도전 전에 찾은 실마리
    items = coach.load_precheck()
    precheck = {items[0]["item"]: {"found": True, "missing": False, "memo": "(예시) 메모"},
                items[1]["item"]: {"found": False, "missing": True, "memo": ""}}
    practice = [{"question": raw["questions"][1], "script": "(예시) 고친 연습 대본", "round": 2}]
    past_hidden = [{"question": raw["questions"][0], "round": 1}]
    return report(raw, round_no=2, profile=raw["profile"], retry_history=history, retry_counts=counts,
                  clue_set=clues, precheck=precheck, practice=practice, past_hidden=past_hidden)


def data_of(text: str) -> dict:
    return json.loads(coach.REPORT_DATA_RE.search(text).group(1))


def with_data(text: str, data: dict) -> str:
    """리포트 본문은 그대로 두고 숨은 데이터만 바꾼다 (옛 버전 · 깨진 파일 흉내)."""
    head = text[: coach.REPORT_DATA_RE.search(text).start()]
    return head + coach.embed_report_data(data) + "\n"


def legacy_no_session(base: str) -> str:
    """부분 복원 · 결과 저장 기능 전 리포트 흉내: report_data 주석이 '나중에 더한 칸' 이라고 한 칸을 뺀다."""
    data = data_of(base)
    for key in ("session", "total_first", "total_latest", "passed", "verdict", "criteria_version", "precheck"):
        data.pop(key, None)
    return with_data(base, data)


def session_without_evaluation(base: str) -> str:
    """부분 복원 · session 은 있지만 평가가 없음 → 면접 없이 이어 하기 불가 (_parse_session 이 None)."""
    data = data_of(base)
    data["session"].pop("evaluation")
    return with_data(base, data)


def job_without_persona(base: str) -> str:
    """부분 복원 · 파서는 읽지만 앱이 막는 직군 (면접관 페르소나가 비어 있는 '개발')."""
    data = data_of(base)
    data["profile"]["job"] = "개발"
    return with_data(base, data)


def unsupported(base: str) -> dict[str, str]:
    """복원 실패 형식 (parse_report 가 ValueError)."""
    data = data_of(base)
    head = base[: coach.REPORT_DATA_RE.search(base).start()]
    out = {
        "no_data.md": head,  # 숨은 데이터 없음 (사람이 읽는 본문만)
        "broken_json.md": head + "<!-- interview-data {\"version\": 1, \"round\": } -->\n",  # { } 는 있지만 JSON 이 깨짐
        "truncated_json.md": head + "<!-- interview-data {\"version\": 1, \"round\": -->\n",  # 잘려서 } 가 없음 → '데이터 없음' 으로 판정
    }
    v = dict(data, version=2)
    out["unknown_version.md"] = with_data(base, v)
    j = json.loads(json.dumps(data))
    j["profile"]["job"] = "기획"
    out["unknown_job.md"] = with_data(base, j)
    n = json.loads(json.dumps(data))
    n["profile"]["name"] = 123
    out["bad_profile.md"] = with_data(base, n)
    return out


def summary(parsed: dict, job: str) -> dict:
    """기준값: parse_report 결과 + (session 이 있으면) rebuild_session 으로 다시 계산한 점수 · 재도전."""
    out = {"parsed": parsed}
    questions = coach.match_questions(coach.load_questions(), job, parsed["questions"])
    out["questions_matched"] = questions is not None  # False 면 앱도 이어 하기를 막는다 (app.py resume_without_interview)
    if parsed["session"] is not None and questions is not None:
        s = coach.rebuild_session(parsed["session"], questions)
        totals = coach.total_scores(s["evaluation"], s["retries"])
        out["rebuilt"] = {
            "answer_scores": [a["score"] for a in s["evaluation"]["answers"]],
            "panel_average": s["evaluation"]["panel_average"],
            "total_first": totals["first"],
            "total_latest": totals["latest"],
            "reflected": {str(no): r["score"] for no, r in s["retries"].items()},
            "retry_history_scores": {str(no): [a["score"] for a in h] for no, h in s["retry_history"].items()},
            "retry_counts": {str(k): v for k, v in s["retry_counts"].items()},
            "clue_round": s["clue_round"],
            "clue_set": s["clue_set"],
            "first_answers": [coach.answer_text(s["messages"], i) for i in range(coach.TOTAL_QUESTIONS)],
        }
    return out


def main():
    base = no_retry()
    samples = {
        ("supported", "v1_no_retry.md"): base,
        ("supported", "v1_with_retry.md"): with_retry(),
        ("partial", "v1_legacy_no_session.md"): legacy_no_session(base),
        ("partial", "v1_session_without_evaluation.md"): session_without_evaluation(base),
        ("partial", "v1_job_without_persona.md"): job_without_persona(base),
    }
    for (folder, name), text in samples.items():
        write(folder, name, text)
        parsed = coach.parse_report(text)
        expected = json.dumps(summary(parsed, parsed["profile"]["job"]), ensure_ascii=False, indent=1, sort_keys=True)
        write("expected", name.replace(".md", ".json"), expected + "\n")
    for name, text in unsupported(base).items():
        write("unsupported", name, text)
    print(f"v1 샘플 {len(samples)}개 · 실패 샘플 {len(unsupported(base))}개를 {FIXTURES} 에 만들었어요.")


if __name__ == "__main__":
    main()
