# Markdown v1 리포트 복원 기준 테스트 (P0-01). AI 호출 없음.
# 샘플 · 기준값은 make_v1_samples.py 가 '변경 전 코드' 로 만든 파일이다 (fixtures/v1).
# 실행: d10-interview 폴더에서  python -m unittest discover tests
import json
import unittest
from pathlib import Path

import coach
from prompts import PERSONAS
from make_v1_samples import DAY, UPDATED_AT, data_of, summary

FIXTURES = Path(__file__).parent / "fixtures" / "v1"
SUPPORTED = ["v1_no_retry", "v1_with_retry"]
PARTIAL = ["v1_legacy_no_session", "v1_session_without_evaluation", "v1_job_without_persona"]


def read(folder: str, name: str) -> str:
    return (FIXTURES / folder / name).read_text(encoding="utf-8")


def expected(name: str) -> dict:
    return json.loads((FIXTURES / "expected" / f"{name}.json").read_text(encoding="utf-8"))


def normalized(value) -> dict:
    """기준값(JSON 파일)과 같은 모양으로 맞춘다 (사전 키는 글자, 튜플은 목록)."""
    return json.loads(json.dumps(value, ensure_ascii=False))


class V1BaselineTest(unittest.TestCase):
    """정상 · 부분 복원 샘플: parse_report 결과와 다시 계산한 점수가 기준값과 같다."""

    def test_matches_baseline(self):
        for folder, names in (("supported", SUPPORTED), ("partial", PARTIAL)):
            for name in names:
                with self.subTest(name=name):
                    parsed = coach.parse_report(read(folder, f"{name}.md"))
                    self.assertEqual(normalized(summary(parsed, parsed["profile"]["job"])), expected(name))


class V1SupportedTest(unittest.TestCase):
    """정상 복원: 면접 없이 이어 하기까지 되는 v1."""

    def rebuild(self, name: str) -> tuple[dict, dict]:
        parsed = coach.parse_report(read("supported", f"{name}.md"))
        questions = coach.match_questions(coach.load_questions(), parsed["profile"]["job"], parsed["questions"])
        self.assertIsNotNone(questions)
        return parsed, coach.rebuild_session(parsed["session"], questions)

    def test_no_retry(self):
        parsed, s = self.rebuild("v1_no_retry")
        self.assertEqual(parsed["round"], 1)
        self.assertEqual([a["score"] for a in s["evaluation"]["answers"]], [20] * 5)
        self.assertEqual(coach.total_scores(s["evaluation"], s["retries"])["latest"], 100)
        self.assertEqual((s["retries"], s["retry_history"], s["retry_counts"]), ({}, {}, {}))

    def test_with_retry(self):
        parsed, s = self.rebuild("v1_with_retry")
        self.assertEqual(parsed["round"], 2)
        self.assertEqual([a["score"] for a in s["evaluation"]["answers"]], [20, 8, 11, 20, 20])  # 최초 점수는 그대로
        totals = coach.total_scores(s["evaluation"], s["retries"])
        self.assertEqual((totals["first"], totals["latest"]), (79, 86))
        self.assertEqual({no: r["score"] for no, r in s["retries"].items()}, {2: 15})  # 처음보다 높은 최고 점수만 반영
        self.assertEqual({no: [a["score"] for a in h] for no, h in s["retry_history"].items()}, {2: [8, 15], 3: [8]})
        self.assertEqual(s["retry_counts"], {2: 2, 3: 1})
        self.assertEqual([c["no"] for c in s["clue_set"]], [2, 3])
        self.assertEqual(len(parsed["precheck"]), 2)
        self.assertEqual(len(parsed["session"]["practice"]), 1)
        self.assertEqual(len(parsed["session"]["past_hidden"]), 1)

    def test_first_answers_kept(self):
        for name in SUPPORTED:
            with self.subTest(name=name):
                _, s = self.rebuild(name)
                answers = [coach.answer_text(s["messages"], i) for i in range(coach.TOTAL_QUESTIONS)]
                self.assertTrue(all(a.strip() for a in answers))

    def test_resave_is_identical(self):
        """복원한 상태로 다시 저장해도 리포트 글자가 그대로다 (앱의 build_current_report 와 같은 인자)."""
        for name in SUPPORTED:
            with self.subTest(name=name):
                text = read("supported", f"{name}.md")
                parsed, s = self.rebuild(name)
                questions = coach.match_questions(coach.load_questions(), parsed["profile"]["job"], parsed["questions"])
                again = coach.build_report(
                    parsed["profile"], questions, s["evaluation"], s["retries"], s["messages"],
                    s["last_suggest"], s["last_question"], None, parsed["round"],
                    coach.load_precheck(), parsed["precheck"], UPDATED_AT, DAY,
                    retry_counts=s["retry_counts"], understanding=s["understanding"], retry_history=s["retry_history"],
                    clue_set=s["clue_set"], clue_round=s["clue_round"], memo=None, verdict_open=False,
                    practice=parsed["session"].get("practice") or [], past_hidden=parsed["session"].get("past_hidden") or [],
                )
                # E-5: 기존 칸 값은 모두 같고, 더한 칸(revision · 재도전 attempt_id)만 늘어난다. 사람이 읽는 본문은 그대로
                new = data_of(again)
                self.assertEqual(new.pop("revision"), coach.REPORT_DATA_REVISION)
                for no, attempts in new["session"]["retry_history"].items():
                    ids = [a.pop("attempt_id") for a in attempts]
                    self.assertEqual(ids, [f"q{no}-a{n}" for n in range(1, len(ids) + 1)])  # v1 은 순서로 ID
                self.assertEqual(new, data_of(text))
                body = coach.REPORT_DATA_RE.sub("", again)
                self.assertEqual(body, coach.REPORT_DATA_RE.sub("", text))


class V1PartialTest(unittest.TestCase):
    """부분 복원: 파일은 읽히지만 '면접 없이 이어 하기' 는 안 되는 v1."""

    def test_legacy_without_session(self):
        parsed = coach.parse_report(read("partial", "v1_legacy_no_session.md"))
        self.assertIsNone(parsed["session"])
        self.assertIsNone(parsed["total_latest"])
        self.assertEqual((parsed["criteria_version"], parsed["precheck"]), ("", {}))
        self.assertEqual(len(parsed["questions"]), coach.TOTAL_QUESTIONS)  # 다음 회차 '같은 질문' 에는 쓸 수 있다

    def test_session_without_evaluation(self):
        parsed = coach.parse_report(read("partial", "v1_session_without_evaluation.md"))
        self.assertIsNone(parsed["session"])
        self.assertEqual(parsed["scores"], [20] * 5)

    def test_job_without_persona(self):
        parsed = coach.parse_report(read("partial", "v1_job_without_persona.md"))
        self.assertEqual(parsed["profile"]["job"], "개발")
        self.assertFalse(PERSONAS["개발"])  # 앱은 이 직군 리포트를 올리기에서 막는다
        self.assertIsNone(coach.match_questions(coach.load_questions(), "개발", parsed["questions"]))


class V1UnsupportedTest(unittest.TestCase):
    """복원 실패: parse_report 가 한국어 한 줄 ValueError 를 낸다."""

    CASES = {
        "no_data.md": "이어 하기 데이터가 없어요",
        "broken_json.md": "깨져 있어요",
        "truncated_json.md": "이어 하기 데이터가 없어요",  # 닫는 } 가 없으면 숨은 데이터를 아예 못 찾는다 (REPORT_DATA_RE)
        "unknown_version.md": "지원하지 않는 리포트 형식",
        "unknown_job.md": "직군을 알 수 없어요",
        "bad_profile.md": "'name' 값을 읽지 못했어요",
    }

    def test_rejected(self):
        for name, message in self.CASES.items():
            with self.subTest(name=name):
                with self.assertRaises(ValueError) as caught:
                    coach.parse_report(read("unsupported", name))
                self.assertIn(message, str(caught.exception))

    def test_every_sample_has_a_case(self):
        self.assertEqual(sorted(p.name for p in (FIXTURES / "unsupported").glob("*.md")), sorted(self.CASES))


if __name__ == "__main__":
    unittest.main()
