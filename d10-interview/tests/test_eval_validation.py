# 평가 응답 검증 테스트 (E-3). coach.validate_* · checked_* 만 부른다. 외부 API 호출 없음.
# 실행: d10-interview 폴더에서  python -m unittest discover tests
import copy
import unittest

import coach
import error_log
from fake_llm import response
from prompts import PANEL_ROLES

QUESTIONS = [{"question": f"질문 {i}"} for i in range(1, 6)]


def mixed():
    return response("evaluation", "mixed")


def codes_of(raw):
    return coach.validate_evaluation(raw, QUESTIONS)


class PanelKeysTest(unittest.TestCase):

    def test_keys_match_roles(self):
        """영문 키는 한글 위원 이름 4개와 하나씩 짝이 맞고, 화면 이름(PANEL_ROLES)은 그대로다."""
        self.assertEqual(list(coach.PANEL_KEYS), PANEL_ROLES)
        self.assertEqual(sorted(coach.PANEL_KEYS.values()), ["communicator", "logician", "practitioner", "recruiter"])


class ValidEvaluationTest(unittest.TestCase):

    def test_fixture_cases_pass(self):
        for case in ("mixed", "perfect"):
            with self.subTest(case=case):
                self.assertEqual(codes_of(response("evaluation", case)), [])

    def test_same_result_as_legacy_for_valid_response(self):
        """정상 응답: 점수 · 평균 · 고친 답 여부 · 글이 기존 summarize_evaluation 과 같다 (목록이 상한 안일 때)."""
        for case in ("mixed", "perfect"):
            with self.subTest(case=case):
                raw = response("evaluation", case)
                self.assertEqual(coach.checked_evaluation(raw, QUESTIONS), coach.summarize_evaluation(raw, QUESTIONS))

    def test_order_independent(self):
        """위원 · 답 순서가 섞여 와도 번호 · 이름으로 찾는다 (순서로 추측하지 않음)."""
        raw = mixed()
        raw["panel"].reverse()
        raw["answers"].reverse()
        self.assertEqual(coach.checked_evaluation(raw, QUESTIONS), coach.checked_evaluation(mixed(), QUESTIONS))

    def test_empty_strings_allowed(self):
        raw = mixed()
        for m in raw["panel"]:
            m["against"] = m["good"] = ""
        raw["conflict"] = raw["agree"] = ""
        for a in raw["answers"]:
            a["weak"] = a["rewrite"] = ""
            a["check"] = []
        raw["next"] = []
        self.assertEqual(codes_of(raw), [])

    def test_boundary_scores_allowed(self):
        raw = mixed()
        raw["panel"][0]["score"], raw["panel"][1]["score"] = 0, 10
        raw["answers"][0]["specific"], raw["answers"][0]["evidence"] = 0, 5
        self.assertEqual(codes_of(raw), [])

    def test_lists_kept_in_full(self):
        """확인할 것 · 다음에 고칠 것: 원본 전체를 남긴다 (기존 함수는 2개 · 3개로 잘랐다)."""
        raw = mixed()
        raw["answers"][0]["check"] = ["가", "나", "다", "라"]
        raw["next"] = ["1", "2", "3", "4", "5"]
        ev = coach.checked_evaluation(raw, QUESTIONS)
        self.assertEqual(ev["answers"][0]["check"], ["가", "나", "다", "라"])
        self.assertEqual(ev["next"], ["1", "2", "3", "4", "5"])
        self.assertEqual(len(coach.summarize_evaluation(raw, QUESTIONS)["next"]), coach.MAX_NEXT)  # 복원 경로는 아직 그대로

    def test_extra_fields_ignored_not_stored(self):
        raw = mixed()
        raw["total"] = 99
        raw["panel"][0]["extra"] = "x"
        raw["answers"][0]["score"] = 20
        self.assertEqual(codes_of(raw), [])
        ev = coach.checked_evaluation(raw, QUESTIONS)
        self.assertNotIn("total", ev)
        self.assertEqual(set(ev["panel"][0]), {"role", "against", "good", "score"})
        self.assertEqual(set(ev["answers"][0]),
                         {"no", "question", "scores", "score", "weak", "rewrite", "check", "needs_rewrite"})

    def test_input_not_modified(self):
        raw = mixed()
        before = copy.deepcopy(raw)
        coach.checked_evaluation(raw, QUESTIONS)
        self.assertEqual(raw, before)


class InvalidEvaluationTest(unittest.TestCase):

    def assert_invalid(self, raw, *expected):
        codes = codes_of(raw)
        for code in expected:
            self.assertIn(code, codes)
        with self.assertRaises(coach.EvaluationInvalid) as caught:
            coach.checked_evaluation(raw, QUESTIONS)
        self.assertEqual(caught.exception.codes, codes)
        return codes

    def test_not_object(self):
        for raw in (None, [], "평가"):
            with self.subTest(raw=raw):
                self.assert_invalid(raw, "not_object:evaluation")

    def test_field_missing(self):
        for field in coach.EVAL_FIELDS:
            with self.subTest(field=field):
                raw = mixed()
                del raw[field]
                self.assert_invalid(raw, f"field_missing:{field}")

    def test_field_type(self):
        raw = mixed()
        raw["panel"], raw["answers"], raw["next"], raw["conflict"] = {}, "x", "고칠 것", 3
        self.assert_invalid(raw, "field_type:panel", "field_type:answers", "field_type:next", "text_type:conflict")

    def test_panel_missing_role(self):
        self.assert_invalid(response("evaluation", "missing_role"), "panel_count:1", "panel_role_missing:logician",
                            "panel_role_missing:communicator", "panel_role_missing:recruiter")
        raw = mixed()
        raw["panel"].pop()
        self.assert_invalid(raw, "panel_count:3", "panel_role_missing:recruiter")

    def test_panel_duplicate_role(self):
        raw = mixed()
        raw["panel"][3]["role"] = raw["panel"][0]["role"]
        self.assert_invalid(raw, "panel_role_duplicate:practitioner", "panel_role_missing:recruiter")

    def test_panel_unknown_role(self):
        raw = mixed()
        raw["panel"][2]["role"] = "빠른 피드백"
        self.assert_invalid(raw, "panel_role_unknown:panel[2]", "panel_role_missing:communicator")

    def test_panel_extra_member(self):
        raw = mixed()
        raw["panel"].append(dict(raw["panel"][0]))
        self.assert_invalid(raw, "panel_count:5", "panel_role_duplicate:practitioner")

    def test_panel_score_type(self):
        """범위 밖은 자르지만 (ClampTest), 정수가 아닌 점수는 여전히 실패."""
        for value in (5.0, 10.5, True, "5", None):
            with self.subTest(value=value):
                raw = mixed()
                raw["panel"][0]["score"] = value
                self.assert_invalid(raw, "score_type:practitioner.score")

    def test_panel_score_missing(self):
        raw = mixed()
        del raw["panel"][0]["score"]
        self.assert_invalid(raw, "field_missing:practitioner.score")

    def test_panel_text_missing_or_wrong_type(self):
        raw = mixed()
        del raw["panel"][1]["good"]
        raw["panel"][2]["against"] = None
        self.assert_invalid(raw, "field_missing:logician.good", "text_type:communicator.against")

    def test_criterion_type(self):
        for value in (4.5, 5.0, 7.0, True, False, "5", None):
            with self.subTest(value=value):
                raw = mixed()
                raw["answers"][2]["evidence"] = value
                self.assert_invalid(raw, "score_type:answers[2].evidence")

    def test_structure_errors_not_hidden_by_clamp(self):
        """범위 밖 점수가 함께 있어도 구조 오류는 실패 (자르기는 검증 통과 뒤에만)."""
        raw = mixed()
        raw["answers"][0]["specific"] = 9
        raw["panel"].pop()
        codes = self.assert_invalid(raw, "panel_role_missing:recruiter")
        self.assertFalse([c for c in codes if "specific" in c])

    def test_criterion_missing(self):
        raw = mixed()
        del raw["answers"][2]["evidence"]
        self.assert_invalid(raw, "field_missing:answers[2].evidence")

    def test_answer_text_fields(self):
        raw = mixed()
        del raw["answers"][0]["rewrite"]
        raw["answers"][1]["weak"] = 3
        raw["answers"][2]["check"] = "확인"
        raw["answers"][3]["check"] = ["확인", 1]
        del raw["answers"][4]["check"]
        self.assert_invalid(raw, "field_missing:answers[0].rewrite", "text_type:answers[1].weak",
                            "field_type:answers[2].check", "text_type:answers[3].check[1]",
                            "field_missing:answers[4].check")

    def test_next_item_type(self):
        raw = mixed()
        raw["next"] = ["고칠 것", None]
        self.assert_invalid(raw, "text_type:next[1]")

    def test_zero_based_numbers(self):
        """기존 함수는 순서로 추측했다 → 이제 검증 실패."""
        self.assert_invalid(response("evaluation", "zero_based_numbers"),
                            "answer_no_range:answers[0]=0", "answer_no_missing:5")

    def test_answer_count(self):
        raw = mixed()
        raw["answers"].pop()
        self.assert_invalid(raw, "answer_count:4", "answer_no_missing:5")
        raw = mixed()
        raw["answers"].append(dict(raw["answers"][0]))
        self.assert_invalid(raw, "answer_count:6", "answer_no_duplicate:1")

    def test_answer_number_duplicate_and_missing(self):
        raw = mixed()
        raw["answers"][1]["no"] = 1
        self.assert_invalid(raw, "answer_no_duplicate:1", "answer_no_missing:2")

    def test_answer_number_type(self):
        for value in ("1", 1.0, True, None):
            with self.subTest(value=value):
                raw = mixed()
                raw["answers"][0]["no"] = value
                self.assert_invalid(raw, "answer_no_type:answers[0]", "answer_no_missing:1")
        raw = mixed()
        del raw["answers"][0]["no"]
        self.assert_invalid(raw, "field_missing:answers[0].no")

    def test_answer_number_range(self):
        raw = mixed()
        raw["answers"][4]["no"] = 6
        self.assert_invalid(raw, "answer_no_range:answers[4]=6", "answer_no_missing:5")

    def test_items_not_objects(self):
        raw = mixed()
        raw["panel"][0] = "위원"
        raw["answers"][0] = None
        self.assert_invalid(raw, "not_object:panel[0]", "not_object:answers[0]")


class ClampTest(unittest.TestCase):
    """범위 밖 정수 점수는 경계값으로 자른다 (CLAUDE.md). 합계 · 평균은 자른 점수로 코드가 계산한다."""

    def out_of_range(self):
        raw = mixed()
        for m, score in zip(raw["panel"], (11, -2, 10, 0)):
            m["score"] = score
        a = next(a for a in raw["answers"] if a["no"] == 1)
        a.update(specific=7, relevance=-1, structure=5, evidence=0)
        return raw

    def test_scores_clamped_and_recalculated(self):
        raw = self.out_of_range()
        self.assertEqual(codes_of(raw), [])                       # 범위 밖은 검증 실패가 아니다
        ev = coach.checked_evaluation(raw, QUESTIONS)
        self.assertEqual([m["score"] for m in ev["panel"]], [10, 0, 10, 0])    # 11 → 10, -2 → 0
        self.assertEqual(ev["panel_average"], 5.0)
        first = ev["answers"][0]
        self.assertEqual(first["scores"], {"specific": 5, "relevance": 0, "structure": 5, "evidence": 0})  # 7 → 5, -1 → 0
        self.assertEqual(first["score"], 10)
        self.assertTrue(first["needs_rewrite"])                   # 10 < 14: 자른 점수로 판단
        totals = coach.total_scores(ev, {})
        self.assertEqual(totals, coach.total_scores(coach.summarize_evaluation(raw, QUESTIONS), {}))

    def test_large_values(self):
        raw = mixed()
        raw["panel"][0]["score"] = 10 ** 12
        raw["answers"][0]["specific"] = -10 ** 12
        ev = coach.checked_evaluation(raw, QUESTIONS)
        self.assertEqual(ev["panel"][0]["score"], 10)
        self.assertEqual(ev["answers"][0]["scores"]["specific"], 0)

    def test_same_as_legacy_clamp(self):
        """구조가 맞는 응답에서는 자른 결과가 기존 summarize_evaluation 과 같다."""
        raw = self.out_of_range()
        self.assertEqual(coach.checked_evaluation(raw, QUESTIONS), coach.summarize_evaluation(raw, QUESTIONS))

    def test_input_not_modified(self):
        raw = self.out_of_range()
        before = copy.deepcopy(raw)
        coach.checked_evaluation(raw, QUESTIONS)
        self.assertEqual(raw, before)                             # 원본의 11 · -2 · 7 · -1 이 그대로

    def test_retry_same_policy(self):
        raw = response("retry", "out_of_range")                   # specific 7, relevance -1, structure 5, evidence 5
        before = copy.deepcopy(raw)
        self.assertEqual(coach.validate_retry(raw), [])
        result = coach.checked_retry(raw)
        self.assertEqual(result["scores"], {"specific": 5, "relevance": 0, "structure": 5, "evidence": 5})
        self.assertEqual(result["score"], 15)
        self.assertEqual(result, coach.summarize_retry(raw))
        self.assertEqual(raw, before)


class CodeFormatTest(unittest.TestCase):
    """문제 코드는 오류 기록 규칙(error_log.CODE)에 맞고, 답변 · AI 글 · 한글이 들어가지 않는다."""

    def broken(self):
        raw = mixed()
        raw["panel"][0]["role"] = "김예시"
        raw["panel"][1]["score"] = 10 ** 12
        raw["panel"][2]["good"] = ["결제 이탈"]
        raw["answers"][0]["no"] = -10 ** 9
        raw["answers"][1]["specific"] = "다섯"
        raw["answers"][2]["check"] = [{"글": "비밀"}]
        raw["next"] = [None]
        return raw

    def test_codes_are_safe(self):
        codes = codes_of(self.broken()) + coach.validate_retry({"specific": "칠", "relevance": 10 ** 9})
        self.assertTrue(codes)
        for code in codes:
            with self.subTest(code=code):
                self.assertRegex(code, error_log.CODE)
                self.assertIsNone(error_log.SECRET.search(code))
                self.assertFalse(any("가" <= ch <= "힣" for ch in code))

    def test_codes_survive_error_log(self):
        codes = codes_of(self.broken())
        event = error_log.build_event("eval_validation", "evaluation", session_id="abcdef12",
                                      codes=codes, meta={"item_count": len(codes)})
        self.assertEqual(event["codes"], codes[:error_log.MAX_CODES])
        self.assertEqual(event["dropped"], max(0, len(codes) - error_log.MAX_CODES))


class RetryValidationTest(unittest.TestCase):

    def test_valid_cases(self):
        for case in ("improved", "same", "lower", "perfect"):
            with self.subTest(case=case):
                raw = response("retry", case)
                self.assertEqual(coach.validate_retry(raw), [])
                self.assertEqual(coach.checked_retry(raw), coach.summarize_retry(raw))

    def test_type_error_raises(self):
        raw = dict(response("retry", "improved"), specific="4", relevance=9.0)
        with self.assertRaises(coach.EvaluationInvalid) as caught:
            coach.checked_retry(raw)
        self.assertEqual(caught.exception.codes, ["score_type:specific", "score_type:relevance"])

    def test_types_and_missing(self):
        base = response("retry", "improved")
        cases = [("specific", 4.0, "score_type:specific"), ("specific", True, "score_type:specific"),
                 ("specific", "4", "score_type:specific"), ("specific", 7.0, "score_type:specific"),
                 ("weak", None, "text_type:weak")]
        for field, value, code in cases:
            with self.subTest(field=field, value=value):
                raw = dict(base, **{field: value})
                self.assertEqual(coach.validate_retry(raw), [code])
        for field in ("evidence", "weak"):
            raw = dict(base)
            del raw[field]
            self.assertEqual(coach.validate_retry(raw), [f"field_missing:{field}"])
        self.assertEqual(coach.validate_retry(None), ["not_object:retry"])

    def test_empty_weak_and_extra_fields(self):
        raw = dict(response("retry", "improved"), weak="", score=99, answer="x")
        result = coach.checked_retry(raw)
        self.assertEqual(result, {"scores": {"specific": 4, "relevance": 4, "structure": 4, "evidence": 4},
                                  "score": 16, "weak": ""})


if __name__ == "__main__":
    unittest.main()
