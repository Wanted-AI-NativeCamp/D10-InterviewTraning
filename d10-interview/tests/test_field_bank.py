# 질문 은행 산업 분야 질문 검사: 4개 직군 분야 목록 · 분야마다 직무 · 경험 · 상황 · ID · 질문 중복 · 공통 2 + 분야 3 구성.
# AI 호출 없음. 실행: d10-interview 폴더에서  python -m unittest discover tests
import unittest

import coach
from prompts import FIELDS
from fake_llm import sequence
from test_app_flow import AppFlowCase

BANK = coach.load_questions()
COLUMNS = ["직군", "분야", "유형", "질문", "보는 점", "만점 예시", "회사 키워드", "질문 ID"]
# 직군 → 분야별 면접에서 고를 수 있는 산업 분야 (디자인은 기존 8개 그대로)
JOB_FIELDS = {
    "디자인": ["헬스케어", "핀테크 · 금융", "커머스", "에듀테크", "모빌리티 · 여행", "콘텐츠 · 미디어", "B2B · SaaS", "게임"],
    "개발": ["핀테크 · 금융", "커머스", "헬스케어", "B2B · SaaS", "게임", "모빌리티 · 여행"],
    "PO": ["커머스", "핀테크 · 금융", "에듀테크", "헬스케어", "B2B · SaaS", "모빌리티 · 여행"],
    "마케팅": ["커머스", "콘텐츠 · 미디어", "게임", "에듀테크", "핀테크 · 금융", "헬스케어"],
}


def fields_of(job: str) -> set[str]:
    return set(BANK[(BANK["직군"] == job) & (BANK["분야"] != coach.DEFAULT_FIELD)]["분야"])


class FieldBankTest(unittest.TestCase):

    def test_schema_and_unique(self):
        self.assertEqual(list(BANK.columns)[:len(COLUMNS)], COLUMNS)
        self.assertFalse(BANK["질문 ID"].duplicated().any())
        self.assertFalse(BANK["질문"].duplicated().any())
        self.assertTrue(BANK["질문 ID"].str.fullmatch(r"Q\d{4}").all())
        self.assertFalse(BANK[["직군", "분야", "유형", "질문", "보는 점"]].isna().any().any())

    def test_job_fields(self):
        for job, fields in JOB_FIELDS.items():
            self.assertEqual(fields_of(job), set(fields), job)
            self.assertTrue(set(fields) <= set(FIELDS), job)  # 분야 설명(AI 맥락)이 있는 분야만

    def test_new_jobs_five_per_field(self):
        """개발 · PO · 마케팅: 분야마다 5문항 (직무 2 · 상황 2 · 경험 1), 모두 90문항."""
        total = 0
        for job in ("개발", "PO", "마케팅"):
            for field in JOB_FIELDS[job]:
                rows = BANK[(BANK["직군"] == job) & (BANK["분야"] == field)]
                self.assertEqual(sorted(rows["유형"]), ["경험", "상황", "상황", "직무", "직무"], (job, field))
                total += len(rows)
        self.assertEqual(total, 90)

    def test_field_interview_common2_field3(self):
        """분야별 면접: 자기소개 · 공통 질문 2개 + 고른 분야 직무 · 경험 · 상황 3개."""
        for job, fields in JOB_FIELDS.items():
            for field in fields:
                questions = coach.pick_questions(BANK, job, field)
                self.assertEqual(len(questions), coach.TOTAL_QUESTIONS)
                self.assertEqual([q["field"] for q in questions[2:]], [field] * 3, (job, field))
                self.assertEqual([q["type"] for q in questions[2:]], ["직무", "경험", "상황"], (job, field))
                self.assertTrue(all(q["question_id"] for q in questions))

    def test_common_interview_unchanged(self):
        """공통 면접은 4개 직군 모두 분야 질문 없이 공통 질문만."""
        for job in JOB_FIELDS:
            questions = coach.pick_questions(BANK, job)
            self.assertEqual({q["field"] for q in questions}, {coach.DEFAULT_FIELD}, job)


class FieldSetupScreenTest(AppFlowCase):
    """면접 정보 설정: 4개 직군 모두 공통 / 분야별 면접을 고를 수 있고, 분야별 면접은 공통 2 + 분야 3 으로 시작한다."""

    def test_four_jobs_field_interview(self):
        self.open_app({})
        self.setup()
        for job, fields in JOB_FIELDS.items():
            self.at.button_group(key="f_job").set_value(job).run()
            self.no_exception()
            self.assertEqual(list(self.at.radio(key="f_type").options), ["공통 면접", "분야별 면접"], job)
            self.at.radio(key="f_type").set_value("field").run()
            self.assertEqual(set(self.at.button_group(key="f_field").options), set(fields), job)
        self.at.button_group(key="f_job").set_value("PO").run()
        self.at.radio(key="f_type").set_value("field").run()
        self.at.button_group(key="f_field").set_value("에듀테크").run()
        self.at.button(key="setup_start").click().run()
        self.no_exception()
        record = self.ss["store_rounds"][-1]
        self.assertEqual((record["job"], record["field"]), ("PO", "에듀테크"))
        self.assertEqual([q.get("field") for q in record["questions"]][2:], ["에듀테크"] * 3)
        self.assertEqual(self.fake.calls, [])

    def start_field(self, job: str, field: str):
        self.setup()
        self.at.button_group(key="f_job").set_value(job).run()
        self.at.radio(key="f_type").set_value("field").run()
        self.at.button_group(key="f_field").set_value(field).run()
        self.at.button(key="setup_start").click().run()
        self.no_exception()

    def test_repeat_field_round_reuses_field_and_notices(self):
        """같은 회사 · 직군 · 분야 2회차: 분야당 경험 질문이 1개라 지난 분야 질문을 다시 쓰고 (공통으로 바꾸지 않음) 안내한다."""
        self.open_app({"interviewer": sequence("probe_one_follow_up") * 2})
        self.start_field("PO", "커머스")
        self.finish()
        first = self.ss["store_rounds"][-1]["questions"]
        self.start_field("PO", "커머스")
        second = self.ss["store_rounds"][-1]["questions"]
        self.assertEqual([q.get("field") for q in second][2:], ["커머스"] * 3)
        self.assertEqual(len({q["question"] for q in second}), 5)                  # 회차 안 중복 없음
        self.assertEqual(second[3]["question"], first[3]["question"])            # 경험 자리: 하나뿐인 분야 질문 다시
        self.assertTrue(any("다시 넣었어요" in i.value for i in self.at.info))


if __name__ == "__main__":
    unittest.main()
