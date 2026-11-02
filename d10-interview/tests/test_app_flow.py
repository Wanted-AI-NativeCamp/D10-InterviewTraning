# 면접 화면 흐름 테스트 (P0-04 · MVP1 IA). Streamlit AppTest + 가짜 AI(fake_llm.FakeAskJson). 외부 API 호출 없음.
# app.py 는 고치지 않는다: 실행 전에 llm.ask_json 을 가짜로 바꿔 끼운다 (app.py 가 'from llm import ask_json' 으로 읽음).
# 대화 상자 안 버튼 · 파일 내려받기 · 브라우저 스크립트 · 화면 모양은 여기서 보지 않는다 (수동 점검).
# 화면 흐름 (IA): 시작 화면 → [+ 새 면접 시작] → 면접 정보 설정 → 5문항 → [평가 받기] → [평가 확인하기] → 그 회차 평가 기록
# 실행: d10-interview 폴더에서  python -m unittest discover tests
import os
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

import coach
import llm
from llm import LLMError
from fake_llm import FakeAskJson, response, sequence

APP = str(Path(__file__).resolve().parents[1] / "app.py")
V1 = Path(__file__).parent / "fixtures" / "v1" / "supported"
TIMEOUT = 60  # 첫 실행은 pandas · altair 를 불러오느라 몇 초 걸린다
COMPANY = "클래스로"
LNB_RECORDS = ":material/history: 면접 기록 (전체)"
LNB_EVAL = ":material/bar_chart: 평가 기록 (회차별)"
LNB_RETRY = ":material/replay: 재도전 (전체)"


class AppFlowCase(unittest.TestCase):
    """테스트마다 가짜 AI 를 끼우고, 끝나면 원래 ask_json 과 API 키를 되돌린다.
    API 키를 빈 값으로 두어 혹시 진짜 ask_json 이 불려도 외부로 나가지 않고 실패하게 한다."""

    def setUp(self):
        self.real_ask_json = llm.ask_json
        self.real_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = ""

    def tearDown(self):
        llm.ask_json = self.real_ask_json
        if self.real_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self.real_key

    def open_app(self, script: dict) -> AppTest:
        self.fake = FakeAskJson(script)
        llm.ask_json = self.fake
        self.at = AppTest.from_file(APP, default_timeout=TIMEOUT)
        self.at.run()
        self.no_exception()
        return self.at

    @property
    def ss(self):
        return self.at.session_state

    def no_exception(self):
        self.assertEqual([e.value for e in self.at.exception], [])

    def click(self, label: str):
        matches = [b for b in self.at.button if label in b.label]
        self.assertTrue(matches, f"'{label}' 버튼이 없어요: {[b.label for b in self.at.button]}")
        matches[0].click().run()
        self.no_exception()

    def setup(self, company: str = COMPANY, experience: str = ""):
        """[+ 새 면접 시작] → 면접 정보 설정 (회사 · 내 경험은 선택)."""
        self.at.button(key="gnb_new" if self.ss["page"] != "start" else "title_new").click().run()
        self.assertEqual(self.ss["page"], "setup")
        self.at.text_input(key="f_company").input(company).run()
        if experience:
            self.at.text_area(key="f_experience").input(experience).run()

    def start_interview(self, company: str = COMPANY):
        self.setup(company)
        self.at.button(key="setup_start").click().run()
        self.no_exception()
        self.assertEqual((self.ss["page"], self.ss["stage"]), ("interview", "interview"))

    def answer(self, text: str):
        self.at.chat_input[0].set_value(text).run()
        self.no_exception()

    def finish(self):
        for i in range(6):
            self.answer(f"답 {i}")
        self.assertEqual(self.ss["stage"], "done")

    def chat_text(self) -> str:
        return "\n".join(m.markdown[0].value for m in self.at.chat_message if m.markdown)

    def metric(self, label: str) -> str:
        return [m.value for m in self.at.metric if m.label == label][0]

    def lnb(self, label: str):
        self.at.segmented_control(key="lnb").set_value(label).run()
        self.no_exception()

    def retry(self, answer: str):
        if self.ss.get("lnb") != LNB_RETRY or self.ss["page"] != "coaching":
            self.lnb(LNB_RETRY)
        no = self.at.selectbox(key="retry_no").value
        self.at.text_area(key=f"retry_answer_{no}").input(answer)
        self.click("다시 채점")
        return no


class InterviewFlowTest(AppFlowCase):

    def test_probe_interview_evaluation_and_retry(self):
        """시작 → 질문 → 꼬리 질문 1개 → 5문항 → [평가 받기] → [평가 확인하기] → 평가 기록 → 재도전 (전체)."""
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")],
                       "retry": [response("retry", "improved")]})
        self.start_interview()
        self.assertIn("질문 1/5", self.at.chat_message[-1].markdown[0].value)

        self.answer("자기소개 답입니다.")
        self.assertEqual((self.ss["q_index"], self.ss["follow_ups"]), (0, 1))  # 같은 질문에서 꼬리 질문
        self.assertIn(response("interviewer", "follow_up")["reply"], self.chat_text())
        self.answer("꼬리 질문 답입니다.")
        self.assertEqual((self.ss["q_index"], self.ss["follow_ups"]), (1, 0))  # 다음 질문
        self.assertIn("질문 2/5", self.at.chat_message[-1].markdown[0].value)
        for i in range(2, 6):
            self.answer(f"{i}번 답입니다.")
        self.assertEqual((self.ss["stage"], self.ss["q_index"]), ("done", coach.TOTAL_QUESTIONS))
        self.assertEqual(sum(m.get("kind") == "question" for m in self.ss["messages"]), coach.TOTAL_QUESTIONS)

        self.click("평가 받기")
        self.assertEqual([a["score"] for a in self.ss["evaluation"]["answers"]], [20, 10, 12, 15, 8])
        self.assertEqual(self.ss["page"], "interview")  # 평가 뒤 임의 화면으로 가지 않는다
        self.click("평가 확인하기")
        # 그 회사 · 직군 · 이 회차의 평가 기록으로 바로 (면접 기록 탭도 같은 회차)
        self.assertEqual((self.ss["page"], self.ss["lnb"]), ("coaching", LNB_EVAL))
        self.assertEqual(self.ss["eval_round_pick"], self.ss["active_round_id"])
        self.assertEqual(self.ss["records_round"], self.ss["active_round_id"])
        self.assertEqual(self.ss["coach_group"], {"key": COMPANY, "job": "디자인"})
        self.assertEqual(self.metric("종합 점수"), "65/100")
        self.assertEqual(len(self.at.tabs), 0)  # 예전 탭 6개 구조가 아니다

        no = self.retry("결론부터 말하면, 인터뷰 5회로 결제 이탈 원인을 찾았습니다.")
        self.assertEqual(no, 5)  # 지금 점수가 가장 낮은 질문이 먼저 골라져 있다
        self.assertEqual({k: [a["score"] for a in v] for k, v in self.ss["retry_history"].items()}, {5: [16]})
        self.assertEqual({k: v["score"] for k, v in self.ss["retries"].items()}, {5: 16})
        self.assertEqual(self.ss["retry_counts"], {5: 1})
        self.assertEqual(self.metric("종합 점수"), "73/100")
        self.assertEqual(self.ss["evaluation"]["answers"][4]["score"], 8)  # 최초 평가는 그대로
        record = self.ss["store_rounds"][0]
        self.assertEqual(record["retries"][5]["score"], 16)  # 회차 레코드에도 반영
        self.assertEqual(self.fake.remaining(), {})

    def test_follow_up_limit(self):
        """꼬리 질문 뒤 AI 가 또 묻자고 해도 다음 질문으로 넘어가고, 그 질문 문장은 보이지 않는다."""
        self.open_app({"interviewer": sequence("probe_follow_up_limit")})
        self.start_interview()
        self.answer("자기소개 답")
        self.answer("꼬리 질문 답")
        self.assertEqual((self.ss["q_index"], self.ss["follow_ups"]), (1, 0))
        self.assertNotIn(response("interviewer", "wants_more")["reply"], self.chat_text())

    def test_single_interviewer_no_choice(self):
        """직군별 대표 면접관 1명 자동 배정: 고르는 칸이 없고, 디자인은 '디자인 팀장' (면접 중 피드백 방식 없음)."""
        self.open_app({})
        self.setup()
        self.assertEqual([b for b in self.at.get("button_group") if b.key == "persona_switch"], [])
        self.assertIn("디자인 팀장", " ".join(m.value for m in self.at.markdown))
        self.assertNotIn("프로덕트 디자인 리드", " ".join(m.value for m in self.at.markdown))

    def test_company_and_experience_optional(self):
        """회사 · 내 경험 없이 시작 → '기타' 그룹 1회차."""
        self.open_app({"interviewer": sequence("probe_one_follow_up")})
        self.start_interview(company="")
        record = self.ss["store_rounds"][0]
        self.assertEqual((record["company_key"], record["company_name"], record["round_number"]), (None, "", 1))
        self.assertEqual(record["experience"], "")

    def test_field_interview_first_round(self):
        """첫 회차부터 분야별 면접: 공통 2 + 분야 3."""
        self.open_app({})
        self.setup()
        self.at.radio(key="f_type").set_value("field").run()
        [b for b in self.at.get("button_group") if b.key == "f_field"][0].set_value("헬스케어").run()
        self.at.button(key="setup_start").click().run()
        self.no_exception()
        fields = [q["field"] for q in self.ss["questions"]]
        self.assertEqual(sum(f != coach.DEFAULT_FIELD for f in fields), 3)
        self.assertEqual(self.ss["store_rounds"][0]["interview_type"], "field")

    def test_evaluation_failure_then_retry(self):
        """평가가 실패하면 한국어 에러 한 줄 · 평가 없음 · 답은 그대로. 다시 누르면 성공."""
        self.open_app({"interviewer": sequence("probe_one_follow_up"),
                       "evaluation": [LLMError("AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요."),
                                      response("evaluation", "perfect")]})
        self.start_interview()
        self.finish()
        messages = list(self.ss["messages"])
        self.click("평가 받기")
        self.assertIsNone(self.ss["evaluation"])
        self.assertIn("AI 응답을 받지 못했어요", " ".join(e.value for e in self.at.error))
        self.assertEqual(self.ss["messages"], messages)
        self.click("평가 받기")
        self.assertEqual(self.metric("종합 점수"), "100/100")

    def test_retry_not_reflected(self):
        """처음과 같은 점수의 재도전은 기록만 남고 종합 점수에 반영되지 않는다."""
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")],
                       "retry": [response("retry", "lower")]})
        self.start_interview()
        self.finish()
        self.click("평가 받기")
        self.click("평가 확인하기")
        no = self.retry("다시 쓴 답")
        self.assertEqual(len(self.ss["retry_history"][no]), 1)
        self.assertEqual(self.ss["retries"], {})
        self.assertEqual(self.metric("종합 점수"), "65/100")


class CompanyRoundTest(AppFlowCase):

    def interview(self, company: str):
        self.start_interview(company)
        self.finish()
        self.click("평가 받기")

    def test_rounds_counted_per_company_and_job(self):
        """회차 번호는 회사(또는 '기타') + 직군별로 누적한다. 다른 회사 기록은 이전 회차가 아니다."""
        evals = [response("evaluation", "mixed") for _ in range(3)]
        self.open_app({"interviewer": sequence("probe_one_follow_up") * 3, "evaluation": evals})
        self.interview("A회사")
        self.interview("B회사")
        self.assertEqual(self.ss["round"], 1)            # B회사 첫 면접은 1회차
        self.assertIsNone(self.ss["previous"])            # A회사 기록과 비교하지 않는다
        self.interview(" A회사 ")                          # 앞뒤 공백만 다르면 같은 회사
        self.assertEqual(self.ss["round"], 2)
        self.assertEqual(self.ss["previous"]["round"], 1)
        numbers = sorted((r["company_key"], r["round_number"]) for r in self.ss["store_rounds"])
        self.assertEqual(numbers, [("A회사", 1), ("A회사", 2), ("B회사", 1)])

    def test_question_modes_only_after_first_round(self):
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")]})
        self.setup()
        self.assertNotIn("질문 출제 방식", [r.label for r in self.at.radio])  # 첫 회차는 숨김
        self.at.button(key="setup_start").click().run()
        self.finish()
        self.setup()
        self.assertIn("질문 출제 방식", [r.label for r in self.at.radio])


class ResumeFlowTest(AppFlowCase):

    def upload(self, name: str):
        self.at.button(key="title_resume").click().run()
        self.assertEqual(self.ss["page"], "restore")
        self.at.get("file_uploader")[0].upload(f"261102-클래스로-디자인-{name}.md", (V1 / f"{name}.md").read_bytes(),
                                               "text/markdown").run()
        self.no_exception()

    def open_records(self):
        self.click("면접 기록 보기")
        self.assertEqual(self.ss["page"], "coaching")
        [b for b in self.at.button if b.key and b.key.startswith("open_")][0].click().run()
        self.no_exception()

    def test_restore_v1_and_continue(self):
        """v1 리포트 복원: 같은 회차 · 재도전 기록 · 최고 점수 그대로 (AI 호출 없음), 평가 기록에서 바로 이어 간다."""
        self.open_app({})
        self.upload("v1_with_retry")
        self.open_records()
        self.lnb(LNB_EVAL)
        self.assertEqual((self.ss["stage"], self.ss["round"]), ("done", 2))
        self.assertEqual({k: v["score"] for k, v in self.ss["retries"].items()}, {2: 15})
        self.assertEqual(self.ss["retry_counts"], {2: 2, 3: 1})
        self.assertEqual(self.metric("종합 점수"), "86/100")
        self.assertEqual(self.fake.calls, [])

    def test_next_round_same_questions(self):
        """복원한 회사 · 직군으로 새 회차: 2회차 · '똑같은 질문 → 이전 회차 선택' 이면 질문이 같다."""
        self.open_app({})
        self.upload("v1_no_retry")
        record = self.ss["store_rounds"][0]
        self.setup(company=record["company_name"])
        self.at.radio(key="f_mode").set_value("same").run()
        self.at.button(key="setup_start").click().run()
        self.no_exception()
        self.assertEqual((self.ss["stage"], self.ss["round"]), ("interview", 2))
        self.assertEqual([q["question"] for q in self.ss["questions"]], [q["question"] for q in record["questions"]])


if __name__ == "__main__":
    unittest.main()
