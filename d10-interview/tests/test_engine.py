# 면접 엔진 기준 테스트 (P0-02). AI 호출 없음. 지금 코드의 실제 동작을 고정한다.
# KnownBehaviorTest 는 '문제일 수 있는 현재 동작' 이다 — 고치기로 하면 그 테스트를 의도적으로 바꾼다.
# 실행: d10-interview 폴더에서  python -m unittest discover tests
import random
import unittest

import numpy as np

import coach
from prompts import PANEL_ROLES

BANK = coach.load_questions()
JOB = "디자인"
FIELD = "헬스케어"
SLOT_TYPES = ["공통", "공통", "직무", "경험", "상황"]  # 자기소개 · 공통 · 직무 · 경험 · 상황 (pick_questions 자리 순서)
SEEDS = range(30)  # 무작위 출제는 여러 번 뽑아 규칙만 확인한다 (시드 인자는 P1 에서 검토)


def row_of(text: str):
    return BANK[BANK["질문"] == text].iloc[0]


def picks(job=JOB, field=coach.DEFAULT_FIELD, company_text="", avoid=None):
    for seed in SEEDS:
        np.random.seed(seed)  # DataFrame.sample 은 numpy 전역 난수를 쓴다
        yield coach.pick_questions(BANK, job, field, company_text, avoid)


def questions5() -> list[dict]:
    return [{"type": t, "question": f"질문 {i + 1}", "point": "", "field": coach.DEFAULT_FIELD, "example": ""}
            for i, t in enumerate(SLOT_TYPES)]


def raw_answer(no: int, s=5, r=5, st=5, e=5, **extra) -> dict:
    return {"no": no, "specific": s, "relevance": r, "structure": st, "evidence": e,
            "weak": f"약점 {no}", "rewrite": f"고친 답 {no}", "check": [], **extra}


def raw_eval(answers=None, panel_scores=(8, 6, 7, 9)) -> dict:
    return {
        "panel": [{"role": role, "against": f"반론 {role}", "good": f"장점 {role}", "score": s}
                  for role, s in zip(PANEL_ROLES, panel_scores)],
        "conflict": "갈린 곳", "agree": "같은 판단",
        "answers": answers if answers is not None else [raw_answer(i) for i in range(1, 6)],
        "next": ["다음 1", "다음 2", "다음 3"],
    }


def evaluation(scores: list[tuple]) -> dict:
    """답 5개의 기준 점수 (구체성, 직무 연관, 구조, 근거) 로 평가를 만든다."""
    return coach.summarize_evaluation(raw_eval([raw_answer(i, *s) for i, s in enumerate(scores, 1)]), questions5())


def attempt(s, r, st, e, answer="다시 쓴 답") -> dict:
    return {"answer": answer, **coach.summarize_retry({"specific": s, "relevance": r, "structure": st, "evidence": e})}


# ── 1. 공통 · 분야별 질문 구성 ─────────────────────────────────────────
class PickQuestionsTest(unittest.TestCase):

    def test_common_interview(self):
        """공통 면접: 자기소개 · 공통 1 (직군 공통) + 이 직군의 분야 '공통' 직무 · 경험 · 상황."""
        for qs in picks():
            self.assertEqual(len(qs), coach.TOTAL_QUESTIONS)
            self.assertIn("자기소개", qs[0]["question"])
            self.assertNotIn("자기소개", qs[1]["question"])
            self.assertEqual([q["type"] for q in qs], SLOT_TYPES)
            self.assertEqual([row_of(q["question"])["직군"] for q in qs], ["공통", "공통", JOB, JOB, JOB])
            self.assertEqual({q["field"] for q in qs}, {coach.DEFAULT_FIELD})

    def test_field_interview(self):
        """분야 면접: 공통 2 + 그 분야 직무 · 경험 · 상황 3."""
        for qs in picks(field=FIELD):
            self.assertEqual([q["type"] for q in qs], SLOT_TYPES)
            self.assertEqual([q["field"] for q in qs], [coach.DEFAULT_FIELD] * 2 + [FIELD] * 3)

    def test_company_keywords_filter(self):
        """회사 키워드가 있는 질문은 회사 이름 · 설명에 키워드가 있을 때만 나온다."""
        self.assertTrue(coach.fits_company("", "아무 회사"))
        self.assertTrue(coach.fits_company("복약/약국", "복약 알림 서비스"))
        self.assertFalse(coach.fits_company("복약/약국", "쇼핑몰"))
        for qs in picks(field=FIELD, company_text="쇼핑몰"):
            for q in qs:
                self.assertTrue(coach.fits_company(row_of(q["question"])["회사 키워드"], "쇼핑몰"))

    def test_avoid_prefers_fresh(self):
        """avoid 에 있는 질문은 다른 질문이 남아 있으면 고르지 않는다."""
        pool = BANK[(BANK["직군"] == JOB) & (BANK["분야"] == coach.DEFAULT_FIELD) & (BANK["유형"] == "경험")]["질문"].tolist()
        keep = pool[0]
        for qs in picks(avoid=set(pool[1:])):
            self.assertEqual(qs[3]["question"], keep)

    def test_all_avoided_reuses(self):
        """모든 질문이 나왔으면 나온 질문을 다시 쓴다 (5문항은 지킨다)."""
        for qs in picks(avoid=set(BANK["질문"])):
            self.assertEqual(len(qs), coach.TOTAL_QUESTIONS)

    def test_unknown_job_raises(self):
        with self.assertRaises(ValueError):
            coach.pick_questions(BANK, "기획")


# ── 2. 질문 출제 방식 ───────────────────────────────────────────────
class PlanQuestionsTest(unittest.TestCase):

    def previous(self) -> list[str]:
        np.random.seed(0)
        return [q["question"] for q in coach.pick_questions(BANK, JOB)]

    def test_modes(self):
        self.assertEqual(list(coach.QUESTION_MODES), ["same", "mix", "new"])
        self.assertEqual(coach.MIX_KEEP, 2)

    def test_same_reuses_previous(self):
        prev = self.previous()
        qs, note = coach.plan_questions(BANK, JOB, coach.DEFAULT_FIELD, "", "same", prev, set(prev))
        self.assertEqual([q["question"] for q in qs], prev)
        self.assertIsNone(note)

    def test_same_with_unknown_question_falls_back(self):
        prev = self.previous()[:4] + ["질문 은행에 없는 질문"]
        qs, note = coach.plan_questions(BANK, JOB, coach.DEFAULT_FIELD, "", "same", prev, set(prev))
        self.assertEqual(len(qs), coach.TOTAL_QUESTIONS)
        self.assertIn("질문 은행에 없는 질문이 있어서", note)

    def test_mix_keeps_previous(self):
        """섞어서: 자기소개 말고 지난 질문 MIX_KEEP 개 이상을 같은 자리에 남긴다."""
        prev = self.previous()
        for seed in SEEDS:
            np.random.seed(seed)
            qs, _ = coach.plan_questions(BANK, JOB, coach.DEFAULT_FIELD, "", "mix", prev, set(prev), random.Random(seed))
            kept = sum(qs[i]["question"] == prev[i] for i in range(1, coach.TOTAL_QUESTIONS))
            self.assertGreaterEqual(kept, coach.MIX_KEEP)

    def test_new_avoids_asked(self):
        """새 질문: 2회차까지는 자기소개 말고 지난 질문과 겹치지 않는다 (디자인 · 공통 분야 질문 은행 기준)."""
        prev = self.previous()
        for seed in SEEDS:
            np.random.seed(seed)
            qs, note = coach.plan_questions(BANK, JOB, coach.DEFAULT_FIELD, "", "new", prev, set(prev))
            self.assertEqual({q["question"] for q in qs[1:]} & set(prev), set())
            self.assertIsNone(note)

    def test_new_notes_repeats_when_bank_runs_out(self):
        asked = set()
        notes = []
        for _ in range(4):
            qs, note = coach.plan_questions(BANK, JOB, coach.DEFAULT_FIELD, "", "new", None, asked)
            asked |= {q["question"] for q in qs}
            notes.append(note)
        self.assertIsNone(notes[0])
        self.assertTrue(any(n and "다시 넣었어요" in n for n in notes[2:]))

    def test_mix_without_previous_is_new(self):
        qs, note = coach.plan_questions(BANK, JOB, coach.DEFAULT_FIELD, "", "mix", None, set())
        self.assertEqual(len(qs), coach.TOTAL_QUESTIONS)
        self.assertIsNone(note)


# ── 3. 꼬리 질문 조건 ───────────────────────────────────────────────
class FollowUpTest(unittest.TestCase):
    PROFILE = {"job": JOB, "persona_type": "디자인 팀장"}

    def test_limit(self):
        self.assertEqual(coach.MAX_FOLLOW_UPS, 1)
        self.assertTrue(coach.should_follow_up(True, 0))
        self.assertFalse(coach.should_follow_up(True, 1))
        self.assertFalse(coach.should_follow_up(False, 0))

    def test_probe_style_follows_ai(self):
        self.assertTrue(coach.wants_follow_up(self.PROFILE, True, 0))
        self.assertFalse(coach.wants_follow_up(self.PROFILE, False, 0))
        self.assertFalse(coach.wants_follow_up(self.PROFILE, True, 1))

    def test_feedback_style_always_once(self):
        """꼬리 질문 뒤 피드백형: AI 판단과 상관없이 질문마다 정확히 1개."""
        profile = {"job": JOB, "persona_type": "프로덕트 디자인 리드"}
        self.assertTrue(coach.wants_follow_up(profile, False, 0))
        self.assertFalse(coach.wants_follow_up(profile, True, 1))

    def test_unknown_or_missing_type_uses_first(self):
        for ptype in (None, "없는 타입"):
            with self.subTest(ptype=ptype):
                self.assertEqual(coach.persona_of(JOB, ptype)["style"], "probe")
                self.assertFalse(coach.wants_follow_up({"job": JOB, "persona_type": ptype}, False, 0))

    def test_job_without_types_is_probe(self):
        self.assertEqual(coach.persona_of("개발")["style"], "probe")


# ── 4. 평가 결과 · 점수 계산 ─────────────────────────────────────────
class SummarizeEvaluationTest(unittest.TestCase):

    def test_shape_and_totals(self):
        ev = coach.summarize_evaluation(raw_eval(), questions5())
        self.assertEqual([m["role"] for m in ev["panel"]], PANEL_ROLES)
        self.assertEqual(ev["panel_average"], 7.5)
        self.assertEqual([a["no"] for a in ev["answers"]], [1, 2, 3, 4, 5])
        self.assertEqual([a["question"] for a in ev["answers"]], [q["question"] for q in questions5()])
        self.assertEqual({a["score"] for a in ev["answers"]}, {coach.ANSWER_MAX})
        self.assertEqual((ev["conflict"], ev["agree"]), ("갈린 곳", "같은 판단"))

    def test_clamp(self):
        """기준 0~5 · 위원 0~10 으로 자른다. 숫자가 아니면 0, 소수는 버림."""
        answers = [raw_answer(1, 7, -1, "x", 4.9)] + [raw_answer(i) for i in range(2, 6)]
        ev = coach.summarize_evaluation(raw_eval(answers, panel_scores=(15, -3, 10, 0)), questions5())
        self.assertEqual(ev["answers"][0]["scores"], {"specific": 5, "relevance": 0, "structure": 0, "evidence": 4})
        self.assertEqual(ev["answers"][0]["score"], 9)
        self.assertEqual([m["score"] for m in ev["panel"]], [10, 0, 10, 0])

    def test_role_order_fixed(self):
        raw = raw_eval()
        raw["panel"].reverse()
        self.assertEqual([m["role"] for m in coach.summarize_evaluation(raw, questions5())["panel"]], PANEL_ROLES)

    def test_needs_rewrite_threshold(self):
        ev = evaluation([(5, 5, 3, 0), (5, 5, 4, 0), (5,) * 4, (5,) * 4, (5,) * 4])  # 13점 · 14점
        self.assertEqual(coach.REWRITE_BELOW, 14)
        self.assertEqual([a["needs_rewrite"] for a in ev["answers"][:2]], [True, False])

    def test_limits(self):
        answers = [raw_answer(1, check=["1", "2", "3"])] + [raw_answer(i) for i in range(2, 6)]
        raw = raw_eval(answers)
        raw["next"] = ["1", "2", "3", "4"]
        ev = coach.summarize_evaluation(raw, questions5())
        self.assertEqual(len(ev["answers"][0]["check"]), coach.MAX_CHECKS)
        self.assertEqual(len(ev["next"]), coach.MAX_NEXT)

    def test_answers_without_no_use_order(self):
        answers = [{k: v for k, v in raw_answer(i, 1, 1, 1, 1).items() if k != "no"} for i in range(1, 6)]
        ev = coach.summarize_evaluation(raw_eval(answers), questions5())
        self.assertEqual([a["weak"] for a in ev["answers"]], [f"약점 {i}" for i in range(1, 6)])

    def test_total_scores(self):
        ev = evaluation([(5,) * 4, (2,) * 4, (3,) * 4, (5,) * 4, (5,) * 4])  # 20 · 8 · 12 · 20 · 20
        retries = {2: attempt(4, 4, 4, 4)}
        self.assertEqual(coach.total_scores(ev, retries), {"first": 80, "latest": 88, "diff": 8, "max": coach.TOTAL_MAX})
        self.assertEqual(coach.total_scores(ev, {})["diff"], 0)


# ── 5. 재도전 결과 반영 ─────────────────────────────────────────────
class ReflectedRetryTest(unittest.TestCase):

    def test_best_higher_attempt(self):
        history = [attempt(3, 3, 3, 3), attempt(4, 4, 4, 4), attempt(3, 3, 3, 4)]  # 12 · 16 · 13
        self.assertEqual(coach.reflected_retry(10, history)["score"], 16)

    def test_not_higher_is_not_reflected(self):
        self.assertIsNone(coach.reflected_retry(12, [attempt(3, 3, 3, 3), attempt(2, 2, 2, 2)]))  # 같거나 낮음
        self.assertIsNone(coach.reflected_retry(12, []))

    def test_tie_keeps_earlier_best(self):
        """동점이면 먼저 받은 최고 점수 답을 유지한다 (E-4B). 더 높은 점수가 와야 바뀐다."""
        history = [attempt(4, 4, 4, 4, "앞"), attempt(4, 4, 4, 4, "뒤")]
        self.assertEqual(coach.reflected_retry(10, history)["answer"], "앞")
        history.append(attempt(5, 4, 4, 4, "더 높음"))
        self.assertEqual(coach.reflected_retry(10, history)["answer"], "더 높음")

    def test_failed_retries(self):
        history = [attempt(2, 2, 2, 2), attempt(4, 4, 4, 4), attempt(3, 3, 3, 3)]  # 8 · 16 · 12
        self.assertEqual([i for i, _ in coach.failed_retries(10, history)], [1, 3])

    def test_latest_answers(self):
        ev = evaluation([(5,) * 4, (2,) * 4, (5,) * 4, (5,) * 4, (5,) * 4])
        latest = coach.latest_answers(ev, {2: attempt(4, 4, 4, 4)})
        self.assertEqual([a["score"] for a in latest], [20, 16, 20, 20, 20])
        self.assertEqual(ev["answers"][1]["score"], 8)  # 최초 평가는 그대로


# ── 6. 기존 회차 복원 ───────────────────────────────────────────────
class RebuildSessionTest(unittest.TestCase):

    def session(self, **extra) -> dict:
        raw = raw_eval([raw_answer(i, 2, 2, 2, 2) for i in range(1, 6)])  # 모두 8점
        return {"messages": [{"role": "user", "content": f"답 {i}", "q": i} for i in range(5)],
                "evaluation": raw, **extra}

    def retry_raw(self, n: int) -> dict:
        return {"answer": f"재도전 {n}", "specific": n, "relevance": n, "structure": n, "evidence": n, "weak": ""}

    def test_scores_recalculated(self):
        s = coach.rebuild_session(self.session(), questions5())
        self.assertEqual([a["score"] for a in s["evaluation"]["answers"]], [8] * 5)
        self.assertEqual((s["retries"], s["retry_history"], s["retry_counts"]), ({}, {}, {}))
        self.assertEqual((s["clue_round"], s["clue_set"]), (1, None))

    def test_history_reflects_best_not_trimmed(self):
        """재도전 기록은 3개로 자르지 않는다 (E-4B): 4번째 이후의 최고 점수도 복원된다."""
        history = {"1": [self.retry_raw(n) for n in (1, 4, 3, 5, 2)]}  # 4 · 16 · 12 · 20 · 8
        s = coach.rebuild_session(self.session(retry_history=history, retry_counts={"1": 5}), questions5())
        self.assertEqual([a["score"] for a in s["retry_history"][1]], [4, 16, 12, 20, 8])
        self.assertEqual(s["retries"][1]["score"], 20)
        self.assertEqual(s["retry_counts"], {1: 5})

    def test_old_report_with_only_retries(self):
        """재도전 기록 기능 전 리포트: 남은 재도전 하나를 기록으로 쓰고, 처음보다 낮으면 반영하지 않는다."""
        s = coach.rebuild_session(self.session(retries={"1": self.retry_raw(4), "2": self.retry_raw(1)}), questions5())
        self.assertEqual({no: len(h) for no, h in s["retry_history"].items()}, {1: 1, 2: 1})
        self.assertEqual(list(s["retries"]), [1])

    def test_invalid_values_dropped_or_clamped(self):
        s = coach.rebuild_session(self.session(
            retry_history={"0": [self.retry_raw(5)], "6": [self.retry_raw(5)], "x": [self.retry_raw(5)]},
            retry_counts={"1": 9, "7": 1}, understanding=150,
            last_suggest=[["회사", "좋은 질문"], ["모르는 관점", "버림"]],
            clues={"round": 3, "set": [{"no": 9, "score": 5, "retry_count": 0}]},
        ), questions5())
        self.assertEqual(s["retry_history"], {})
        self.assertEqual(s["retry_counts"], {})  # 횟수는 기록 개수로 계산 (파일의 9 는 쓰지 않음, E-5)
        self.assertEqual(set(s["retry_unreadable"]), {"0", "6", "x"})  # 모르는 질문 번호의 기록도 버리지 않고 원본 보존 (E-5)
        self.assertEqual(s["understanding"], 100)
        self.assertEqual(s["last_suggest"], [("회사", "좋은 질문")])
        self.assertEqual((s["clue_round"], s["clue_set"]), (3, None))  # 모르는 질문 번호면 실마리를 새로 찾는다

    def test_saved_clues_restored(self):
        s = coach.rebuild_session(self.session(clues={"round": 2, "set": [{"no": 3, "score": 8, "retry_count": 1}]}),
                                  questions5())
        self.assertEqual(s["clue_round"], 2)
        self.assertEqual([(c["no"], c["score"], c["retry_count"], c["criterion"]) for c in s["clue_set"]],
                         [(3, 8, 1, "specific")])


# ── 7. 다음 회차 계산 ───────────────────────────────────────────────
class NextRoundTest(unittest.TestCase):

    def test_next_round(self):
        self.assertEqual(coach.next_round(None), 1)
        self.assertEqual(coach.next_round({"round": 2}), 3)
        self.assertEqual(coach.next_round({"round": coach.MAX_ROUND}), coach.MAX_ROUND)


# ── 8. 실마리 선택 기준 ─────────────────────────────────────────────
class PickCluesTest(unittest.TestCase):

    def test_lowest_two_with_weakest_criterion(self):
        ev = evaluation([(5,) * 4, (2, 3, 1, 4), (5,) * 4, (2, 1, 2, 3), (4, 4, 4, 4)])  # 20 · 10 · 20 · 8 · 16
        clues = coach.pick_clues(ev)
        self.assertEqual(coach.MAX_CLUES, 2)
        self.assertEqual([(c["no"], c["score"], c["criterion"], c["criterion_score"]) for c in clues],
                         [(4, 8, "relevance", 1), (2, 10, "structure", 1)])

    def test_ties_by_number_and_criterion_order(self):
        ev = evaluation([(3, 3, 3, 3)] * 3 + [(5,) * 4] * 2)  # 12 · 12 · 12 · 20 · 20
        clues = coach.pick_clues(ev)
        self.assertEqual([c["no"] for c in clues], [1, 2])
        self.assertEqual({c["criterion"] for c in clues}, {"specific"})  # 기준 점수가 같으면 CRITERIA 순서

    def test_uses_latest_and_keeps_many_retries(self):
        """재도전을 여러 번 한 답도 실마리 후보다 (E-4B: 3번 다 쓴 답 제외 규칙 삭제)."""
        ev = evaluation([(2,) * 4, (3,) * 4, (4,) * 4, (5,) * 4, (5,) * 4])  # 8 · 12 · 16 · 20 · 20
        clues = coach.pick_clues(ev, retries={1: attempt(5, 5, 5, 4)}, retry_counts={2: 5})
        self.assertEqual([(c["no"], c["score"], c["retry_count"]) for c in clues], [(2, 12, 5), (3, 16, 0)])

    def test_all_perfect(self):
        self.assertEqual(coach.pick_clues(evaluation([(5,) * 4] * 5)), [])

    def test_progress(self):
        ev = evaluation([(2,) * 4, (3,) * 4, (5,) * 4, (5,) * 4, (5,) * 4])
        clues = coach.pick_clues(ev)
        progress = coach.clue_progress(clues, ev, {1: attempt(4, 4, 4, 4)}, {1: 1})
        self.assertEqual([(r["no"], r["retried"], r["diff"]) for r in progress["rows"]], [(1, True, 8), (2, False, 0)])
        self.assertFalse(progress["done"])


# ── 문제일 수 있는 현재 동작 (보고됨 · 고치면 여기를 바꾼다) ───────────────────
# 향후 작업 (P0-02 에서 발견 · 지금은 고치지 않음)
#   #1 분야 질문 소진 시 조용히 공통으로      → P3 질문 출제 정책 개선 (P3-05)
#   #2 섞어서 + 분야 변경 시 분야 질문 부족   → P3 질문 출제 정책 개선 (P3-05)
#   #3 위원 누락을 0점으로 평균               → 1차 · AI 평가 응답 검증 · 오류 처리 (임의 점수 계산 금지 방안 검토)
#   #4 0부터 매긴 답 번호가 밀려 붙음         → 1차 · AI 평가 응답 검증 · 오류 처리 (잘못된 연결 금지 방안 검토)
#   #5 check 글이 글자로 쪼개짐               → 1차 · 입력 데이터 검증 필요성 검토
#   #6 재도전 횟수가 기록에서 복원되지 않음   → P1 저장 · 복원 구조 개선 시 검토
#   #7 디자인 · 공통 분야 3회차부터 재출제    → 질문 은행 확장 정책 결정 시 검토 (데이터 · 테스트 없음, PlanQuestionsTest 참고)
class KnownBehaviorTest(unittest.TestCase):

    def test_field_exhausted_falls_back_to_common_silently(self):
        """#1 분야 질문을 모두 피하면 분야 자리가 분야 '공통' 질문으로 바뀌고, 안내(note)도 없다."""
        asked = set(BANK[(BANK["직군"] == JOB) & (BANK["분야"] == FIELD)]["질문"])
        qs, note = coach.plan_questions(BANK, JOB, FIELD, "헬스케어", "new", None, asked)
        self.assertEqual([q["field"] for q in qs], [coach.DEFAULT_FIELD] * 5)
        self.assertIsNone(note)

    def test_mix_after_field_change_keeps_common_questions(self):
        """#2 '섞어서' 로 분야를 바꾸면 지난 공통 질문이 분야 자리에 남아 분야 질문이 3개보다 적어진다."""
        np.random.seed(0)
        prev = [q["question"] for q in coach.pick_questions(BANK, JOB)]
        np.random.seed(0)
        qs, _ = coach.plan_questions(BANK, JOB, FIELD, "", "mix", prev, set(prev), random.Random(0))
        self.assertLess(sum(q["field"] == FIELD for q in qs), 3)

    def test_missing_panel_role_counts_as_zero(self):
        """#3 AI 가 위원을 빠뜨리면 그 위원을 0점으로 넣어 평균이 내려간다."""
        raw = raw_eval()
        raw["panel"] = raw["panel"][:1]  # 8점 한 명만
        self.assertEqual(coach.summarize_evaluation(raw, questions5())["panel_average"], 2.0)

    def test_zero_based_numbers_shift_answers(self):
        """#4 AI 가 답 번호를 0부터 매기면 답이 한 칸씩 밀려 붙고 마지막 답이 겹친다."""
        answers = [raw_answer(i) for i in range(5)]
        ev = coach.summarize_evaluation(raw_eval(answers), questions5())
        self.assertEqual([a["weak"] for a in ev["answers"]], ["약점 1", "약점 2", "약점 3", "약점 4", "약점 4"])

    def test_check_string_split_into_letters(self):
        """#5 check 가 목록이 아니라 글이면 글자 단위로 쪼개진다 (strict 스키마라 실제로는 드묾)."""
        answers = [raw_answer(1, check="ab")] + [raw_answer(i) for i in range(2, 6)]
        self.assertEqual(coach.summarize_evaluation(raw_eval(answers), questions5())["answers"][0]["check"], ["a", "b"])

    def test_retry_counts_derived_from_history(self):
        """#6 (E-5 에서 해결) retry_counts 가 없는 리포트도 횟수를 재도전 기록 개수로 계산한다 (파일 값은 쓰지 않음)."""
        session = {"messages": [{"role": "user", "content": "답", "q": 0}],
                   "evaluation": raw_eval([raw_answer(i, 2, 2, 2, 2) for i in range(1, 6)]),
                   "retry_history": {"1": [{"answer": "다시", "specific": 4, "relevance": 4, "structure": 4,
                                            "evidence": 4, "weak": ""}]}}
        s = coach.rebuild_session(session, questions5())
        self.assertEqual((len(s["retry_history"][1]), s["retry_counts"]), (1, {1: 1}))


if __name__ == "__main__":
    unittest.main()
