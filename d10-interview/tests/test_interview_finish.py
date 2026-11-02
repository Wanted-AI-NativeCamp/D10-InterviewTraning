# 면접 완료 → 평가 받기 흐름: 마지막 질문 안내 · 완료 안내 · 완료 직후 한 번만 아래로 내림 · 평가 중복 요청 방지.
# 스크롤 위치 자체는 AppTest 로 볼 수 없어 브라우저로 따로 확인한다 (수동 점검: 마지막 답 뒤 완료 안내가 화면 안).
# AI 호출 없음 (가짜 AI). 실행: d10-interview 폴더에서  python -m unittest discover tests
import unittest

from fake_llm import response, sequence
from llm import LLMError
from test_app_flow import AppFlowCase


class InterviewFinishTest(AppFlowCase):

    def answer_until_last(self):
        self.start_interview()
        for i in range(5):  # 첫 답 뒤 꼬리 질문 1개 → 다섯 번 답하면 5번째 질문
            self.answer(f"답 {i}")

    def test_last_question_placeholder(self):
        self.open_app({"interviewer": sequence("probe_one_follow_up")})
        self.start_interview()
        self.assertNotIn("마지막 질문", self.at.chat_input[0].placeholder)
        for i in range(5):
            self.answer(f"답 {i}")
        self.assertEqual(self.ss["q_index"], 4)
        self.assertIn("마지막 질문이에요", self.at.chat_input[0].placeholder)

    def test_finish_shows_done_and_scrolls_once(self):
        self.open_app({"interviewer": sequence("probe_one_follow_up")})
        self.answer_until_last()
        self.answer("마지막 답")
        self.assertEqual(self.ss["stage"], "done")
        self.assertEqual(len(self.at.chat_input), 0)
        text = " ".join(m.value for m in self.at.markdown)
        self.assertIn("질문 5개를 모두 마쳤어요", text)
        self.assertEqual(sum(1 for m in self.ss["messages"] if m.get("content") == "마지막 답"), 1)  # 마지막 답은 한 번만
        self.assertNotIn("finish_scroll", self.ss)  # 완료 직후 한 번 내리고 지운다 (다시 그려도 또 내리지 않음)
        self.assertTrue([b for b in self.at.button if b.key == "eval_request"])

    def test_evaluation_requested_once(self):
        """[평가 받기] 한 번에 평가 호출 한 번. 평가 중 깃발은 남지 않고, 다시 그려도 또 부르지 않는다."""
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")] * 2})
        self.answer_until_last()
        self.answer("마지막 답")
        self.click("평가 받기")
        self.at.run()
        self.no_exception()
        self.assertEqual(sum(1 for c in self.fake.calls if c["name"] == "evaluation"), 1)
        self.assertNotIn("eval_running", self.ss)
        keys = [b.key for b in self.at.button]
        self.assertIn("eval_check", keys)
        self.assertNotIn("eval_request", keys)

    def test_evaluation_failure_shows_button_again_without_repeat(self):
        """평가가 실패하면 오류 한 줄 + [평가 받기] 가 다시 보이고, 화면을 다시 그려도 저절로 다시 부르지 않는다."""
        err = LLMError("AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요.", "api_server", 503, "InternalServerError")
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [err]})
        self.answer_until_last()
        self.answer("마지막 답")
        self.click("평가 받기")
        self.assertIn("AI 응답을 받지 못했어요", " ".join(e.value for e in self.at.error))
        self.assertTrue([b for b in self.at.button if b.key == "eval_request"])
        self.at.run()
        self.assertEqual(sum(1 for c in self.fake.calls if c["name"] == "evaluation"), 1)


if __name__ == "__main__":
    unittest.main()
