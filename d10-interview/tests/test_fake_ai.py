# 가짜 AI 응답 검증 (P0-03). 외부 API 호출 없음.
# 1) 응답이 실제 호출 스키마(strict)에 맞는지  2) 지금 엔진에 넣으면 기대한 결과가 나오는지
# 실행: d10-interview 폴더에서  python -m unittest discover tests
import unittest

from jsonschema import Draft202012Validator, ValidationError

import coach
from llm import LLMError
from prompts import EVAL_SCHEMA, INTERVIEWER_SCHEMA, PANEL_ROLES, RETRY_SCHEMA
from fake_llm import FakeAskJson, KINDS, load, response, sequence

SCHEMAS = {"interviewer": INTERVIEWER_SCHEMA, "evaluation": EVAL_SCHEMA, "retry": RETRY_SCHEMA}
QUESTIONS = [{"type": t, "question": f"질문 {i + 1}", "point": "", "field": coach.DEFAULT_FIELD, "example": ""}
             for i, t in enumerate(["공통", "공통", "직무", "경험", "상황"])]


def strict_problems(schema: dict, path: str = "$") -> list[str]:
    """OpenAI strict 모드 조건: object 는 모든 칸이 required · additionalProperties false."""
    problems = []
    if schema.get("type") == "object":
        props = schema.get("properties", {})
        if sorted(schema.get("required", [])) != sorted(props):
            problems.append(f"{path}: required 와 properties 가 달라요")
        if schema.get("additionalProperties") is not False:
            problems.append(f"{path}: additionalProperties 가 false 가 아니에요")
        for key, sub in props.items():
            problems += strict_problems(sub, f"{path}.{key}")
    if schema.get("type") == "array":
        problems += strict_problems(schema.get("items", {}), f"{path}[]")
    return problems


def simulate_interview(profile: dict, replies: list[dict]) -> dict:
    """app.py 면접 반복부(답 보내기 → 꼬리 질문 or 다음 질문)의 판단만 옮긴 것. 화면 없이 응답 순서를 확인한다.
    (app.py 3278-3300 과 같은 규칙: 꼬리 질문 여부는 coach.wants_follow_up 이 정한다)"""
    q_index, follow_ups, shown, used = 0, 0, [], 0
    per_question = [0] * coach.TOTAL_QUESTIONS
    feedback_style = coach.persona_of(profile["job"], profile.get("persona_type"))["style"] == "feedback"
    for result in replies:
        if q_index >= coach.TOTAL_QUESTIONS:
            break
        used += 1
        ai_wants = bool(result.get("follow_up"))
        if coach.wants_follow_up(profile, ai_wants, follow_ups):
            follow_ups += 1
            per_question[q_index] += 1
            shown.append(result["reply"])
        else:
            if result["reply"] and (feedback_style or not ai_wants):
                shown.append(result["reply"])
            q_index += 1
            follow_ups = 0
    return {"finished": q_index == coach.TOTAL_QUESTIONS, "used": used, "follow_ups": per_question, "shown": shown}


class SchemaTest(unittest.TestCase):

    def test_schemas_are_strict(self):
        for kind, schema in SCHEMAS.items():
            with self.subTest(kind=kind):
                self.assertEqual(strict_problems(schema), [])

    def test_every_response_matches_schema(self):
        for kind in KINDS:
            data = load(kind)
            for group in ("cases", "edge_cases"):
                for case, value in data.get(group, {}).items():
                    with self.subTest(kind=kind, case=case):
                        Draft202012Validator(SCHEMAS[kind]).validate(value)

    def test_wrong_response_is_rejected(self):
        """검증이 실제로 동작하는지: 칸이 빠지거나 더 있거나 위원 이름이 틀리면 거부."""
        bad = [
            ("interviewer", {"reply": "x", "follow_up": True}),
            ("interviewer", {"reply": "x", "follow_up": True, "understanding": 1, "extra": 1}),
            ("retry", {"specific": "4", "relevance": 4, "structure": 4, "evidence": 4, "weak": ""}),
        ]
        wrong_role = response("evaluation", "mixed")
        wrong_role["panel"][0]["role"] = "디자이너"
        bad.append(("evaluation", wrong_role))
        for kind, value in bad:
            with self.subTest(kind=kind, value=str(value)[:40]):
                with self.assertRaises(ValidationError):
                    Draft202012Validator(SCHEMAS[kind]).validate(value)


class InterviewerResponseTest(unittest.TestCase):

    def test_probe_one_follow_up(self):
        r = simulate_interview({"job": "디자인", "persona_type": "디자인 팀장"}, sequence("probe_one_follow_up"))
        self.assertEqual((r["finished"], r["used"], r["follow_ups"]), (True, 6, [1, 0, 0, 0, 0]))

    def test_probe_follow_up_limit(self):
        """꼬리 질문 뒤 AI 가 또 묻자고 해도 코드가 막고, 그 질문 문장은 보여 주지 않는다."""
        replies = sequence("probe_follow_up_limit")
        r = simulate_interview({"job": "디자인", "persona_type": "디자인 팀장"}, replies)
        self.assertEqual((r["finished"], r["follow_ups"]), (True, [1, 0, 0, 0, 0]))
        self.assertNotIn(replies[1]["reply"], r["shown"])

    def test_feedback_every_question(self):
        """피드백형: 질문마다 꼬리 질문 1개 + 피드백. 피드백에 follow_up true 가 와도 보여 준다."""
        replies = sequence("feedback_every_question")
        r = simulate_interview({"job": "디자인", "persona_type": "프로덕트 디자인 리드"}, replies)
        self.assertEqual((r["finished"], r["used"], r["follow_ups"]), (True, 10, [1] * 5))
        self.assertIn(replies[-1]["reply"], r["shown"])

    def test_understanding_clamped(self):
        self.assertEqual(coach.clamp(response("interviewer", "understanding_out_of_range")["understanding"], 0, 100), 100)


class EvaluationResponseTest(unittest.TestCase):

    def test_mixed(self):
        ev = coach.summarize_evaluation(response("evaluation", "mixed"), QUESTIONS)
        self.assertEqual([a["score"] for a in ev["answers"]], [20, 10, 12, 15, 8])
        self.assertEqual(ev["panel_average"], 7.0)
        self.assertEqual(coach.total_scores(ev, {})["first"], 65)
        self.assertEqual([a["needs_rewrite"] for a in ev["answers"]], [False, True, True, False, True])
        self.assertEqual([(c["no"], c["criterion"]) for c in coach.pick_clues(ev)], [(5, "relevance"), (2, "structure")])
        self.assertEqual(len(ev["answers"][4]["check"]), 2)

    def test_perfect(self):
        ev = coach.summarize_evaluation(response("evaluation", "perfect"), QUESTIONS)
        totals = coach.total_scores(ev, {})
        self.assertEqual((totals["latest"], ev["panel_average"]), (100, 10.0))
        self.assertEqual(coach.verdict(totals, ev["panel_average"])["level"], "pass")
        self.assertEqual(coach.pick_clues(ev), [])

    def test_edge_cases_reproduce_known_behavior(self):
        """경계 응답은 test_engine KnownBehaviorTest #3 · #4 를 그대로 재현한다 (1차 평가 응답 검증 작업용)."""
        missing = coach.summarize_evaluation(response("evaluation", "missing_role"), QUESTIONS)
        self.assertEqual(missing["panel_average"], 2.0)
        self.assertEqual([m["role"] for m in missing["panel"]], PANEL_ROLES)
        shifted = coach.summarize_evaluation(response("evaluation", "zero_based_numbers"), QUESTIONS)
        self.assertEqual([a["weak"] for a in shifted["answers"]], ["답 2", "답 3", "답 4", "답 5", "답 5"])


class RetryResponseTest(unittest.TestCase):

    def setUp(self):
        self.ev = coach.summarize_evaluation(response("evaluation", "mixed"), QUESTIONS)

    def attempt(self, case: str) -> dict:
        return {"answer": f"다시 쓴 답 ({case})", **coach.summarize_retry(response("retry", case))}

    def test_reflection(self):
        q2 = self.ev["answers"][1]["score"]  # 10
        self.assertIsNone(coach.reflected_retry(q2, [self.attempt("same")]))     # 같은 점수 → 반영 안 됨
        self.assertIsNone(coach.reflected_retry(q2, [self.attempt("lower")]))    # 낮음 → 반영 안 됨
        best = coach.reflected_retry(q2, [self.attempt("lower"), self.attempt("improved"), self.attempt("same")])
        self.assertEqual(best["score"], 16)

    def test_totals_after_retry(self):
        retries = {5: self.attempt("perfect")}  # 8 → 20
        self.assertEqual(coach.total_scores(self.ev, retries), {"first": 65, "latest": 77, "diff": 12, "max": coach.TOTAL_MAX})

    def test_out_of_range_clamped(self):
        self.assertEqual(coach.summarize_retry(response("retry", "out_of_range"))["score"], 15)  # 5 + 0 + 5 + 5


class FakeAskJsonTest(unittest.TestCase):

    def test_returns_in_order_and_records(self):
        fake = FakeAskJson({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")]})
        first = fake("지시문", "기록", INTERVIEWER_SCHEMA, "interviewer")
        self.assertTrue(first["follow_up"])
        fake("지시문", "기록", EVAL_SCHEMA, "evaluation")
        self.assertEqual([c["name"] for c in fake.calls], ["interviewer", "evaluation"])
        self.assertEqual(fake.remaining(), {"interviewer": 5})

    def test_failure_and_unprepared_call(self):
        fake = FakeAskJson({"evaluation": [LLMError("AI 응답을 받지 못했어요."), response("evaluation", "perfect")]})
        with self.assertRaises(LLMError):
            fake("지시문", "기록", EVAL_SCHEMA, "evaluation")  # 첫 평가는 실패
        self.assertEqual(fake("지시문", "기록", EVAL_SCHEMA, "evaluation")["panel"][0]["score"], 10)  # 다시 시도는 성공
        with self.assertRaises(AssertionError):
            fake("지시문", "글", RETRY_SCHEMA, "highlight")  # 준비하지 않은 호출

    def test_schema_checked_per_call(self):
        fake = FakeAskJson({"retry": [response("interviewer", "enough")]})  # 다른 스키마의 응답
        with self.assertRaises(ValidationError):
            fake("지시문", "답", RETRY_SCHEMA, "retry")


if __name__ == "__main__":
    unittest.main()
