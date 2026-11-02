# 평가 위원회 입력(coach.format_record): 질문별 '보는 점'을 함께 넘기고, 옛 기록처럼 보는 점이 없어도 그대로 동작.
# AI 호출 없음 (가짜 AI). 실행: d10-interview 폴더에서  python -m unittest discover tests
import unittest

import coach
from fake_llm import response, sequence
from test_app_flow import AppFlowCase

QUESTIONS = [
    {"type": "공통", "question": "1분 자기소개를 해 주세요.", "point": "핵심 경험 · 직무 연결"},
    {"type": "직무", "question": "전환율이 떨어지면 무엇을 보나요?", "point": "퍼널 이해 · 지표 해석"},
]
MESSAGES = [
    {"role": "assistant", "content": "1분 자기소개를 해 주세요.", "q": 0, "kind": "question"},
    {"role": "user", "content": "답 하나", "q": 0},
    {"role": "assistant", "content": "전환율이 떨어지면 무엇을 보나요?", "q": 1, "kind": "question"},
    {"role": "user", "content": "답 둘", "q": 1},
    {"role": "assistant", "content": "어떤 지표부터요?", "q": 1},
    {"role": "user", "content": "꼬리 답", "q": 1},
]


class FormatRecordTest(unittest.TestCase):

    def test_point_under_each_question(self):
        text = coach.format_record(QUESTIONS, MESSAGES)
        blocks = text.split("\n\n")
        self.assertEqual(blocks[0].splitlines(),
                         ["[질문 1 · 공통] 1분 자기소개를 해 주세요.", "[보는 점] 핵심 경험 · 직무 연결", "[지원자] 답 하나"])
        self.assertEqual(blocks[1].splitlines(),
                         ["[질문 2 · 직무] 전환율이 떨어지면 무엇을 보나요?", "[보는 점] 퍼널 이해 · 지표 해석",
                          "[지원자] 답 둘", "[면접관] 어떤 지표부터요?", "[지원자] 꼬리 답"])  # 답 · 꼬리 질문 순서 그대로

    def test_old_record_without_point(self):
        """옛 기록(보는 점 없음 · 빈칸 · None)은 보는 점 줄 없이 이전과 같은 글."""
        old = [{"type": q["type"], "question": q["question"]} for q in QUESTIONS]
        old[1]["point"] = None
        text = coach.format_record(old, MESSAGES)
        self.assertNotIn("[보는 점]", text)
        self.assertEqual(text.split("\n\n")[0].splitlines()[:2], ["[질문 1 · 공통] 1분 자기소개를 해 주세요.", "[지원자] 답 하나"])
        blank = [dict(q, point="  ") for q in QUESTIONS]
        self.assertNotIn("[보는 점]", coach.format_record(blank, MESSAGES))


class EvaluationInputTest(AppFlowCase):

    def test_evaluation_input_has_points(self):
        """실제 화면 흐름: 면접 5문항 → 평가 받기. 평가 위원회 입력에 질문 5개의 보는 점이 모두 들어간다."""
        self.open_app({"interviewer": sequence("probe_one_follow_up"), "evaluation": [response("evaluation", "mixed")]})
        self.start_interview()
        self.finish()
        self.click("평가 받기")
        [call] = [c for c in self.fake.calls if c["name"] == "evaluation"]
        questions = self.ss["store_rounds"][-1]["questions"]
        self.assertEqual(call["user_input"].count("[보는 점]"), 5)
        for q in questions:
            self.assertIn(f"[보는 점] {q['point']}", call["user_input"])
        self.assertIn("4명의 눈", call["instructions"])  # 평가 지시문(위원 4명 · 기준)은 그대로


if __name__ == "__main__":
    unittest.main()
