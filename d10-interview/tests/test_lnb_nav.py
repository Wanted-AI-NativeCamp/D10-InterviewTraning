# 면접 상세 LNB 이동: 평가 기록 → 면접 기록 → 재도전 순서, [평가 확인하기] → 이 회차 평가 기록,
# 면접 기록 탭 구조 (표 → 회차 → 핵심 정보 → 맨 아래 대화 기록 접힘), LNB 위젯 키를 그린 뒤 바꾸는 오류가 다시 나지 않는지.
# AI 호출 없음 (가짜 AI). 실행: d10-interview 폴더에서  python -m unittest discover tests
import unittest
from datetime import date

import coach
from fake_llm import response, sequence
from test_app_flow import AppFlowCase, LNB_EVAL, LNB_RECORDS, LNB_RETRY

BANK = coach.load_questions()


def done_round(rounds: list, company: str, evaluated: bool) -> dict:
    """질문 5개를 마친 회차 (평가는 가짜 AI 응답 'mixed')."""
    questions = coach.pick_questions(BANK, "디자인")
    record = coach.new_round(rounds, company_name=company, company_desc="", job="디자인", field=coach.DEFAULT_FIELD,
                             question_mode="new", nickname="테스터", experience="", questions=questions, day=date(2026, 11, 2))
    record["messages"] = [{"role": "assistant", "content": f"질문 {i + 1}", "q": i, "kind": "question"} for i in range(5)]
    record["messages"] += [{"role": "user", "content": f"답 {i}", "q": i} for i in range(5)]
    record.update(stage="done", q_index=5)
    if evaluated:
        record["evaluation"] = coach.checked_evaluation(response("evaluation", "mixed"), questions)
    rounds.append(record)
    return record


class LnbNavigationTest(AppFlowCase):

    def restore(self, rounds: list):
        text = coach.build_store_file(rounds, "테스터", "2026-11-02 12:00", date(2026, 11, 2))
        self.at.button(key="title_resume").click().run()
        self.at.get("file_uploader")[0].upload("기록.md", text.encode("utf-8"), "text/markdown").run()
        self.no_exception()

    def open_list_group(self):
        self.at.button(key="gnb_coaching").click().run()
        [b for b in self.at.button if b.key and b.key.startswith("open_")][0].click().run()
        self.no_exception()

    def test_eval_check_goes_to_this_round_eval(self):
        """5문항 → 평가 받기 → 평가 확인하기 → 이 회차의 평가 기록 (LNB 순서와 상관없이 목적지를 정해서)."""
        self.open_app({"interviewer": sequence("probe_one_follow_up") * 2, "evaluation": [response("evaluation", "mixed")] * 2})
        self.start_interview()
        self.finish()
        self.click("평가 받기")
        self.start_interview()                      # 2회차도 끝내고 평가
        self.finish()
        self.click("평가 받기")
        second = self.ss["active_round_id"]
        self.click("평가 확인하기")
        self.assertEqual((self.ss["page"], self.ss["lnb"], self.ss["eval_round_pick"]), ("coaching", LNB_EVAL, second))
        self.assertEqual(list(self.at.segmented_control(key="lnb").options),
                         [l.split(": ", 1)[1] for l in (LNB_EVAL, LNB_RECORDS, LNB_RETRY)])
        self.assertIn("모의 결과", " ".join(s.value for s in self.at.subheader))
        self.lnb(LNB_RECORDS)                       # 면접 기록으로 바꿔도 같은 회차
        self.assertEqual(self.at.selectbox(key="records_round").value, second)
        self.lnb(LNB_RETRY)
        self.lnb(LNB_EVAL)
        self.assertEqual(self.ss["eval_round_pick"], second)
        first = self.ss["store_rounds"][0]["round_id"]
        self.at.selectbox(key="eval_round_pick").set_value(first).run()   # 평가 기록에서 고른 회차가
        self.lnb(LNB_RECORDS)
        self.assertEqual(self.at.selectbox(key="records_round").value, first)  # 면접 기록에서도 (지난 선택이 남지 않음)
        self.lnb(LNB_EVAL)
        self.assertEqual(self.ss["eval_round_pick"], first)

    def test_records_tab_layout_and_no_eval_button(self):
        """면접 기록 탭: 표 → 확인할 회차 → 핵심 정보 → (전체 종합) → 맨 아래 대화 기록 (접힘). [평가 기록 보기] 없음."""
        rounds = []
        done_round(rounds, "A", evaluated=True)
        done_round(rounds, "A", evaluated=False)
        self.open_app({})
        self.restore(rounds)
        self.open_list_group()
        self.assertEqual(self.ss["lnb"], LNB_RECORDS)  # 목록에서 처음 들어가면 면접 기록
        keys = [b.key for b in self.at.button]
        self.assertNotIn("records_eval", keys)
        self.assertFalse([b for b in self.at.button if "평가 기록 보기" in b.label or "평가 받으러 가기" in b.label])
        [exp] = [e for e in self.at.expander if "전체 면접 대화 기록" in e.label]
        self.assertIs(exp, self.at.expander[-1])     # 탭 맨 아래
        self.assertEqual([m.markdown[0].value for m in exp.chat_message],
                         [m["content"] for m in rounds[1]["messages"]])  # 기록 순서 그대로
        captions = " ".join(c.value for c in self.at.caption)
        self.assertIn("아직 평가 전이에요", captions)  # 고른 회차(2회차)는 평가 전
        self.at.selectbox(key="records_round").set_value(rounds[0]["round_id"]).run()
        self.no_exception()
        self.assertIn("최초 종합", " ".join(c.value for c in self.at.caption))
        self.lnb(LNB_EVAL)                            # 면접 기록에서 고른 회차가 평가 기록에도
        self.assertEqual(self.ss["eval_round_pick"], rounds[0]["round_id"])
        self.assertIn("모의 결과", " ".join(s.value for s in self.at.subheader))
        self.at.selectbox(key="eval_round_pick").set_value(rounds[1]["round_id"]).run()
        self.assertIn("아직 평가 전이에요", " ".join(i.value for i in self.at.info))  # 평가 전 회차 안내
        self.assertEqual(self.fake.calls, [])

    def test_tab_choice_kept_across_pages(self):
        """다른 화면에 다녀와 GNB 면접 코칭 · 면접 데이터 목록으로 다시 들어가도 마지막에 고른 탭 그대로."""
        rounds = []
        done_round(rounds, "A", evaluated=True)
        self.open_app({})
        self.restore(rounds)
        self.open_list_group()
        self.lnb(LNB_RETRY)
        self.at.button(key="gnb_home").click().run()
        self.at.button(key="gnb_coaching").click().run()       # 같은 회사 · 직군 상세로 바로
        self.no_exception()
        self.assertEqual(self.ss["lnb"], LNB_RETRY)
        self.at.button(key="back_to_list").click().run()       # 면접 데이터 목록 → 다시 들어가기
        [b for b in self.at.button if b.key and b.key.startswith("open_")][0].click().run()
        self.no_exception()
        self.assertEqual(self.ss["lnb"], LNB_RETRY)

    def test_go_tab_buttons_after_lnb_drawn(self):
        """LNB 를 그린 뒤 누르는 화면 안 버튼(재도전 · 전체 회차 종합)으로 탭을 바꿔도 위젯 키 오류가 나지 않는다."""
        rounds = []
        done_round(rounds, "A", evaluated=True)
        self.open_app({})
        self.restore(rounds)
        self.open_list_group()
        self.lnb(LNB_EVAL)
        self.click("모의 결과 확인하기")
        self.click("전체 회차 종합 보기")
        self.assertEqual(self.ss["lnb"], LNB_RECORDS)
        self.lnb(LNB_EVAL)
        [b for b in self.at.button if b.key and b.key.startswith("eval_retry_")][0].click().run()
        self.no_exception()
        self.assertEqual(self.ss["lnb"], LNB_RETRY)


if __name__ == "__main__":
    unittest.main()
