# MVP1 IA · 데이터 구조 테스트: 회사(또는 '기타') → 직군 → 회차 기록, Markdown v2 통합 저장 · v1/v2 복원, GNB · LNB 화면.
# coach 의 보관 함수 + Streamlit AppTest + 가짜 AI. 외부 API 호출 없음. 기준 샘플(tests/fixtures/v1)은 읽기만 한다.
# 실행: d10-interview 폴더에서  python -m unittest discover tests
import json
import random
import unittest
from datetime import date
from pathlib import Path

import coach
from fake_llm import response, sequence
from make_v1_samples import data_of
from test_app_flow import AppFlowCase, LNB_EVAL, LNB_RECORDS, LNB_RETRY

V1 = Path(__file__).parent / "fixtures" / "v1"
BANK = coach.load_questions()
DAY = date(2026, 11, 2)


def v1_text(name="v1_with_retry", folder="supported") -> str:
    return (V1 / folder / f"{name}.md").read_text(encoding="utf-8")


def load_v1(name="v1_with_retry", folder="supported") -> dict:
    [(record, _)] = coach.parse_store_file(v1_text(name, folder), BANK)["rounds"]
    return record


def interview_record(rounds, company, job="디자인", field=coach.DEFAULT_FIELD, evaluated=True) -> dict:
    """면접을 마친 회차 레코드 (평가는 가짜 AI 응답 'mixed')."""
    questions = coach.pick_questions(BANK, job, field)
    record = coach.new_round(rounds, company_name=company, company_desc="", job=job, field=field, question_mode="new",
                             nickname="테스터", experience="", questions=questions, day=DAY)
    record["messages"] = [{"role": "assistant", "content": f"질문 {i + 1}", "q": i, "kind": "question"} for i in range(5)]
    record["messages"] += [{"role": "user", "content": f"답 {i}", "q": i} for i in range(5)]
    record.update(stage="done", q_index=5)
    if evaluated:
        record["evaluation"] = coach.checked_evaluation(response("evaluation", "mixed"), questions)
    rounds.append(record)
    return record


class QuestionBankIdTest(unittest.TestCase):

    def test_every_question_has_permanent_id(self):
        ids = list(BANK["질문 ID"])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(i.startswith("Q") and len(i) == 5 for i in ids))
        self.assertEqual(coach.question_row(BANK.iloc[0])["question_id"], "Q0001")

    def test_questions_carry_id_into_round(self):
        record = load_v1()
        self.assertTrue(all(q["question_id"] for q in record["questions"]))


class CompanyGroupTest(unittest.TestCase):

    def test_company_key_and_other_group(self):
        self.assertEqual(coach.company_key("  A회사 "), "A회사")
        self.assertEqual(coach.company_key("a회사"), "a회사")          # 대소문자 · 중간 공백은 그대로
        self.assertIsNone(coach.company_key("   "))
        self.assertEqual(coach.group_name({"company_name": ""}), coach.OTHER_GROUP)
        real = {"company_name": "기타", "company_key": "기타"}            # 실제 회사명이 '기타'
        self.assertNotEqual(real["company_key"], None)

    def test_round_numbers_per_company_and_job(self):
        rounds = []
        a1 = interview_record(rounds, "A")
        b1 = interview_record(rounds, "B")
        a2 = interview_record(rounds, "A")
        dev = interview_record(rounds, "A", job="개발")
        none1 = interview_record(rounds, "")
        self.assertEqual([r["round_number"] for r in (a1, b1, a2, dev, none1)], [1, 1, 2, 1, 1])
        self.assertIs(coach.previous_evaluated(rounds, a2), a1)
        self.assertIsNone(coach.previous_evaluated(rounds, b1))       # 다른 회사는 이전 회차가 아니다
        self.assertIsNone(coach.previous_evaluated(rounds, dev))      # 다른 직군도 아니다

    def test_random_past_questions(self):
        common = [q for q in (coach.question_row(r) for _, r in BANK.iterrows()) if q["field"] == coach.DEFAULT_FIELD][:6]
        field = [q for q in (coach.question_row(r) for _, r in BANK.iterrows()) if q["field"] == "헬스케어"][:3]
        self.assertTrue(coach.random_past_ready("common", common, []))
        self.assertFalse(coach.random_past_ready("common", common[:4], []))
        self.assertTrue(coach.random_past_ready("field", common[:2], field))
        picked = coach.random_past_questions(common[:2], field, "field", random.Random(1))
        self.assertEqual(len(picked), coach.TOTAL_QUESTIONS)
        self.assertEqual(sum(q["field"] == "헬스케어" for q in picked), 3)


class StoreFileTest(unittest.TestCase):

    def test_v2_round_trip_keeps_everything(self):
        rounds = [load_v1(), load_v1("v1_no_retry")]
        interview_record(rounds, "B")
        interview_record(rounds, "", evaluated=False)                 # 평가 전 회차도 저장
        text = coach.build_store_file(rounds, "테스터", "2026-11-02 12:00", DAY)
        data = data_of(text)
        self.assertEqual(data["version"], 2)
        parsed = coach.parse_store_file(text, BANK)
        again = [r for r, _ in parsed["rounds"]]
        self.assertEqual(coach.store_data(again, "테스터", ""), coach.store_data(rounds, "테스터", ""))
        pending = next(r for r in again if r["company_key"] is None)
        self.assertIsNone(pending["evaluation"])
        self.assertEqual(coach.round_status(pending), "평가 전")

    def test_in_progress_round_not_saved(self):
        rounds = []
        interview_record(rounds, "A")
        running = coach.new_round(rounds, company_name="A", company_desc="", job="디자인", field="공통", question_mode="new",
                                  nickname="", experience="", questions=coach.pick_questions(BANK, "디자인"), day=DAY)
        rounds.append(running)
        self.assertEqual(len(data_of(coach.build_store_file(rounds, "n", "t", DAY))["rounds"]), 1)

    def test_v1_ids_stable_and_reupload_detectable(self):
        self.assertEqual(load_v1()["round_id"], load_v1()["round_id"])
        self.assertNotEqual(load_v1()["round_id"], load_v1("v1_job_without_persona", "partial")["round_id"])

    def test_v1_summary_only_round(self):
        record = load_v1("v1_legacy_no_session", "partial")
        self.assertEqual(record["stage"], "summary")
        self.assertEqual(coach.round_as_report(record)["scores"], [20] * 5)

    def test_unknown_version_and_broken_files_rejected(self):
        for name in ("unknown_version", "broken_json", "no_data"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                coach.parse_store_file(v1_text(name, "unsupported"), BANK)
        broken = data_of(coach.build_store_file([load_v1()], "n", "t", DAY))
        broken["rounds"][0]["job"] = "모르는 직군"
        text = "# x\n" + coach.embed_report_data(broken) + "\n"
        with self.assertRaises(ValueError):
            coach.parse_store_file(text, BANK)

    def test_damaged_evaluation_partial_restore_in_v2(self):
        rounds = [load_v1()]
        data = data_of(coach.build_store_file(rounds, "n", "t", DAY))
        data["rounds"][0]["session"]["evaluation"]["panel"].pop()
        [(record, problems)] = coach.parse_store_file("# x\n" + coach.embed_report_data(data) + "\n", BANK)["rounds"]
        self.assertIsNone(record["evaluation"])
        self.assertEqual(len(record["evaluation_unreadable"]), 1)
        self.assertIn("panel_role_missing:recruiter", problems["evaluation"])

    def test_other_company_practice_not_mixed(self):
        """R4: 저장할 때 연습 대본 · 지운 답은 그 회차 자기 것만 (다른 회사 리포트에서 모아 넣지 않는다)."""
        a = load_v1()
        a["extra"]["practice"] = [{"question": "q", "script": "A회사 대본", "round": 2}]
        rounds = [a]
        b = interview_record(rounds, "B")
        data = data_of(coach.build_store_file(rounds, "n", "t", DAY))
        by_company = {r["company_key"]: r["session"] for r in data["rounds"]}
        self.assertEqual(by_company[a["company_key"]]["practice"][0]["script"], "A회사 대본")
        self.assertEqual(by_company["B"]["practice"], [])

    def test_fingerprint_changes_with_data(self):
        rounds = [load_v1()]
        before = coach.store_fingerprint(rounds, "n")
        rounds[0]["retry_history"].setdefault(4, []).append(
            {"attempt_id": "q4-a1", "answer": "새 답", **coach.checked_retry(response("retry", "improved"))})
        self.assertNotEqual(coach.store_fingerprint(rounds, "n"), before)


class GnbLnbScreenTest(AppFlowCase):

    def test_start_screen_paths_and_nickname(self):
        self.open_app({})
        self.assertEqual(self.ss["page"], "start")
        self.assertTrue(self.ss["nickname"])
        labels = [b.label for b in self.at.button]
        self.assertTrue(any("새 면접 시작" in l for l in labels))
        self.assertTrue(any("Markdown 복원" in l for l in labels))
        self.at.button(key="title_home").click().run()
        self.assertEqual(self.ss["page"], "home")
        self.at.text_input(key="nickname_input").input("새 닉네임").run()
        self.assertEqual(self.ss["nickname"], "새 닉네임")
        gnb = [b.label for b in self.at.button if b.key and b.key.startswith("gnb_")]
        self.assertEqual(len([l for l in gnb if "홈" in l or "면접 코칭" in l]), 2)  # GNB 1 · 2 (3 · 4 는 2차 MVP)

    def test_restore_v2_and_lnbs(self):
        rounds = [load_v1(), load_v1("v1_no_retry")]
        interview_record(rounds, "B")
        text = coach.build_store_file(rounds, "테스터", "2026-11-02 12:00", DAY)
        self.open_app({})
        self.at.button(key="title_resume").click().run()
        self.at.get("file_uploader")[0].upload("기록.md", text.encode("utf-8"), "text/markdown").run()
        self.no_exception()
        self.assertEqual(len(self.ss["store_rounds"]), 3)
        self.assertFalse(any("마지막 저장 뒤에 바뀐 기록" in c.value for c in self.at.caption))  # 올린 파일 그대로라 저장된 상태
        self.click("면접 기록 보기")
        names = [b.label for b in self.at.button if b.key and b.key.startswith("open_")]
        self.assertEqual(len(names), 2)  # 클래스로(예시) · 디자인 / B · 디자인
        [b for b in self.at.button if b.key and b.key.startswith("open_") and "2회차" in b.label][0].click().run()
        self.no_exception()
        self.assertEqual(self.ss["lnb"], LNB_RECORDS)
        self.assertIn("회차별 면접 기록", [s.value.split(" ", 1)[-1] for s in self.at.subheader][0])
        self.lnb(LNB_EVAL)
        self.assertEqual(self.ss["round"], 2)                 # 가장 최근 평가 회차
        self.assertIn("모의 결과", " ".join(s.value for s in self.at.subheader))
        self.lnb(LNB_RETRY)
        self.assertIn("전체 답변별 점수", " ".join(s.value for s in self.at.subheader))
        self.assertEqual(self.fake.calls, [])

    def test_reupload_same_file_skipped(self):
        self.open_app({})
        self.at.button(key="title_resume").click().run()
        uploader = self.at.get("file_uploader")[0]
        uploader.upload("a.md", v1_text().encode("utf-8"), "text/markdown").run()
        self.at.get("file_uploader")[0].upload("b.md", v1_text().encode("utf-8"), "text/markdown").run()
        self.no_exception()
        self.assertEqual(len(self.ss["store_rounds"]), 1)
        self.assertIn("건너뛰었어요", " ".join(s.value for s in self.at.success))
        self.assertIn("b.md · 예전 면접리포트(v1) · 새로 불러온 회차는 없어요.", " ".join(s.value for s in self.at.success))

    def test_reupload_only_skipped_still_opens_records(self):
        """같은 파일만 다시 올려 새 회차가 0개여도, 건너뛴 회차는 보관함에 있으니 [면접 기록 보기] 가 보인다."""
        self.open_app({})
        self.ss["store_rounds"].append(load_v1())               # 앞서 복원해 둔 회차 (파일 칸은 비운 상태)
        self.at.button(key="title_resume").click().run()
        self.at.get("file_uploader")[0].upload("a.md", v1_text().encode("utf-8"), "text/markdown").run()
        self.no_exception()
        self.assertEqual(len(self.ss["store_rounds"]), 1)       # 중복 생성 없음
        self.assertIn("이미 있던 회차 1개는 다시 만들지 않고 건너뛰었어요.", " ".join(s.value for s in self.at.success))
        self.click("면접 기록 보기")
        self.assertEqual(self.ss["page"], "coaching")
        self.assertEqual(self.fake.calls, [])

    def test_unsaved_indicator_after_interview(self):
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")]})
        self.start_interview()
        self.finish()
        self.assertTrue(any("마지막 저장 뒤에 바뀐 기록" in c.value for c in self.at.caption))

    def test_restart_discards_running_round(self):
        self.open_app({"interviewer": sequence("probe_one_follow_up")})
        self.start_interview()
        self.answer("답 하나")
        self.at.button(key="nav_restart").click().run()
        self.no_exception()
        # 확인 창: 진행 중 회차의 답이 사라진다고 먼저 알린다 (창 안 버튼은 AppTest 가 누르지 못해 수동 점검 M-IA-5)
        self.assertIn("지금 면접의 답이 사라지고", " ".join(w.value for w in self.at.warning))
        self.assertTrue([b for b in self.at.button if b.key == "restart_go"])
        self.assertEqual(len(self.ss["store_rounds"]), 1)  # 누르기 전에는 그대로

    def test_leaving_interview_keeps_round(self):
        """면접 중 홈으로 가도 회차는 세션에 남고, 홈에서 이어서 할 수 있다."""
        self.open_app({"interviewer": sequence("probe_one_follow_up")})
        self.start_interview()
        self.answer("답 하나")
        self.at.button(key="gnb_home").click().run()
        rid = self.ss["store_rounds"][0]["round_id"]
        self.at.button(key=f"home_resume_{rid}").click().run()
        self.no_exception()
        self.assertEqual((self.ss["page"], self.ss["follow_ups"]), ("interview", 1))
        self.assertIn("답 하나", self.chat_text())

    def test_retry_compared_with_previous_best(self):
        """재도전 결과는 같은 회차 · 질문의 이전 최고 점수와 비교한다 (최초 8 → 16 → 다음 재도전은 16 과 비교)."""
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")],
                       "retry": [response("retry", "improved"), response("retry", "same")]})
        self.start_interview()
        self.finish()
        self.click("평가 받기")
        self.click("평가 확인하기")
        self.retry("첫 재도전 답")
        self.assertIn("최초 답 (8점)", " ".join(c.value for c in self.at.caption))
        self.retry("두 번째 재도전 답")
        captions = " ".join(c.value for c in self.at.caption)
        self.assertIn("이전 최고 점수 (1번째 재도전 · 16점)", captions)
        after = [m for m in self.at.metric if m.label == "후 점수"][0]
        self.assertEqual((after.value, after.delta), ("10/20", "-6"))

    def test_no_memo_or_extra_tabs(self):
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")]})
        self.start_interview()
        self.finish()
        self.click("평가 받기")
        self.click("평가 확인하기")
        text = " ".join(b.label for b in self.at.button) + " ".join(str(o) for o in self.at.segmented_control(key="lnb").options)
        for removed in ("암기", "점검하기", "단계 중", "리포트 저장하기"):
            self.assertNotIn(removed, text)
        self.assertEqual(list(self.at.segmented_control(key="lnb").options),
                         [l.split(": ", 1)[1] for l in (LNB_EVAL, LNB_RECORDS, LNB_RETRY)])  # 평가 기록이 먼저


if __name__ == "__main__":
    unittest.main()
