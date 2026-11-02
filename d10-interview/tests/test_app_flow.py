# 면접 화면 흐름 테스트 (P0-04). Streamlit AppTest + 가짜 AI(fake_llm.FakeAskJson). 외부 API 호출 없음.
# app.py 는 고치지 않는다: 실행 전에 llm.ask_json 을 가짜로 바꿔 끼운다 (app.py 가 'from llm import ask_json' 으로 읽음).
# 대화 상자 안 버튼 · 파일 내려받기 · 브라우저 스크립트 · 화면 모양은 여기서 보지 않는다 (수동 점검).
# 실행: d10-interview 폴더에서  python -m unittest discover tests   (이 파일만: python -m unittest tests/test_app_flow.py)
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
PROFILE = {"f_name": "김예시", "f_company": "클래스로", "f_company_desc": "IT, 헬스케어 진단 서비스",
           "f_experience": "대학 팀 프로젝트에서 중고 거래 앱의 UX/UI 디자인을 맡아 사용자 인터뷰로 결제 이탈 원인을 찾았습니다."}


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

    def start_interview(self, persona: str | None = None):
        """타이틀 → 새 면접 → (면접관 타입) → 지원 정보 → 브리핑 → 면접 시작."""
        self.at.button(key="title_new").click().run()
        if persona:
            [b for b in self.at.get("button_group") if b.key == "persona_switch"][0].set_value(persona).run()
        for key, value in PROFILE.items():
            (self.at.text_area if key == "f_experience" else self.at.text_input)(key=key).input(value)
        self.click("면접 시작하기")
        self.assertEqual(self.ss["stage"], "briefing")
        self.click("면접을 시작하겠습니다")
        self.assertEqual(self.ss["stage"], "interview")

    def answer(self, text: str):
        self.at.chat_input[0].set_value(text).run()
        self.no_exception()

    def chat_text(self) -> str:
        return "\n".join(m.markdown[0].value for m in self.at.chat_message if m.markdown)

    def metric(self, label: str) -> str:
        return [m.value for m in self.at.metric if m.label == label][0]

    def retry(self, answer: str):
        no = self.at.selectbox(key="retry_no").value
        self.at.text_area(key=f"retry_answer_{no}").input(answer)
        self.click("다시 채점")
        return no


class InterviewFlowTest(AppFlowCase):

    def test_probe_interview_evaluation_and_retry(self):
        """일반형(디자인 팀장): 시작 → 질문 → 꼬리 질문 1개 → 5문항 → 평가 → 재도전 반영."""
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

        self.click("위원 4명에게 평가받기")
        self.assertEqual([a["score"] for a in self.ss["evaluation"]["answers"]], [20, 10, 12, 15, 8])
        self.assertEqual(self.metric("종합 점수"), "65/100")
        self.assertEqual(len(self.at.tabs), 6)

        no = self.retry("결론부터 말하면, 인터뷰 5회로 결제 이탈 원인을 찾았습니다.")
        self.assertEqual(no, 5)  # 지금 점수가 가장 낮은 질문이 먼저 골라져 있다
        self.assertEqual({k: [a["score"] for a in v] for k, v in self.ss["retry_history"].items()}, {5: [16]})
        self.assertEqual({k: v["score"] for k, v in self.ss["retries"].items()}, {5: 16})
        self.assertEqual(self.ss["retry_counts"], {5: 1})
        self.assertEqual(self.metric("종합 점수"), "73/100")
        self.assertEqual(self.ss["evaluation"]["answers"][4]["score"], 8)  # 최초 평가는 그대로
        self.assertEqual(self.fake.remaining(), {})

    def test_follow_up_limit(self):
        """꼬리 질문 뒤 AI 가 또 묻자고 해도 다음 질문으로 넘어가고, 그 질문 문장은 보이지 않는다."""
        self.open_app({"interviewer": sequence("probe_follow_up_limit")})
        self.start_interview()
        self.answer("자기소개 답")
        self.answer("꼬리 질문 답")
        self.assertEqual((self.ss["q_index"], self.ss["follow_ups"]), (1, 0))
        self.assertNotIn(response("interviewer", "wants_more")["reply"], self.chat_text())

    def test_feedback_persona(self):
        """피드백형(프로덕트 디자인 리드): 질문마다 꼬리 질문 1개 + 피드백, 10번 호출로 5문항."""
        self.open_app({"interviewer": sequence("feedback_every_question")})
        self.start_interview("프로덕트 디자인 리드")
        self.assertEqual(self.ss["profile"]["persona_type"], "프로덕트 디자인 리드")
        for i in range(10):
            self.answer(f"답 {i}")
        self.assertEqual(self.ss["stage"], "done")
        self.assertEqual(sum(c["name"] == "interviewer" for c in self.fake.calls), 10)
        self.assertIn(response("interviewer", "feedback_review_flag_true")["reply"], self.chat_text())

    def test_evaluation_failure_then_retry(self):
        """평가가 실패하면 한국어 에러 한 줄 · 평가 없음 · 답은 그대로. 다시 누르면 성공."""
        self.open_app({"interviewer": sequence("probe_one_follow_up"),
                       "evaluation": [LLMError("AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요."),
                                      response("evaluation", "perfect")]})
        self.start_interview()
        for i in range(6):
            self.answer(f"답 {i}")
        messages = list(self.ss["messages"])
        self.click("위원 4명에게 평가받기")
        self.assertIsNone(self.ss["evaluation"])
        self.assertIn("AI 응답을 받지 못했어요", " ".join(e.value for e in self.at.error))
        self.assertEqual(self.ss["messages"], messages)
        self.click("위원 4명에게 평가받기")
        self.assertEqual(self.metric("종합 점수"), "100/100")

    def test_retry_not_reflected(self):
        """처음과 같은 점수의 재도전은 기록만 남고 종합 점수에 반영되지 않는다."""
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")],
                       "retry": [response("retry", "lower")]})
        self.start_interview()
        for i in range(6):
            self.answer(f"답 {i}")
        self.click("위원 4명에게 평가받기")
        no = self.retry("다시 쓴 답")
        self.assertEqual(len(self.ss["retry_history"][no]), 1)
        self.assertEqual(self.ss["retries"], {})
        self.assertEqual(self.metric("종합 점수"), "65/100")


class ResumeFlowTest(AppFlowCase):

    def upload(self, name: str):
        self.at.button(key="title_resume").click().run()
        self.at.get("file_uploader")[0].upload(f"261102-클래스로-디자인-{name}.md", (V1 / f"{name}.md").read_bytes(),
                                               "text/markdown").run()
        self.no_exception()

    def test_resume_v1_without_interview(self):
        """v1 리포트를 올려 '면접 없이 이어 하기': 같은 회차 · 재도전 기록 · 횟수 그대로 (AI 호출 없음)."""
        self.open_app({})
        self.upload("v1_with_retry")
        self.assertEqual(self.ss["previous"]["round"], 2)
        [c for c in self.at.checkbox if c.key == "resume_skip"][0].check().run()
        self.click("지난 결과로 이어서 하기")
        self.assertEqual((self.ss["stage"], self.ss["round"]), ("done", 2))
        self.assertEqual({k: v["score"] for k, v in self.ss["retries"].items()}, {2: 15})
        self.assertEqual(self.ss["retry_counts"], {2: 2, 3: 1})
        self.assertEqual(self.metric("종합 점수"), "86/100")
        self.assertEqual(self.fake.calls, [])

    def test_next_round_from_v1(self):
        """v1 리포트로 다음 회차: 지원 정보가 채워지고, 기본 '같은 질문' 으로 2회차를 시작한다."""
        self.open_app({})
        self.upload("v1_no_retry")
        self.assertEqual(self.at.text_input(key="f_company").value, self.ss["previous"]["profile"]["company"])
        self.click("면접 시작하기")
        self.assertEqual((self.ss["stage"], self.ss["round"]), ("briefing", 2))
        self.assertEqual([q["question"] for q in self.ss["questions"]], self.ss["previous"]["questions"])


if __name__ == "__main__":
    unittest.main()
