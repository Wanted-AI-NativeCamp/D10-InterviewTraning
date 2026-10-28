# Streamlit 화면만. 프롬프트는 prompts.py, AI 호출은 llm.py, 계산은 coach.py.
import html
import math
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
import streamlit as st

import coach
from llm import LLMError, ask_json
from prompts import (
    EVAL_SCHEMA,
    FIELDS,
    HIGHLIGHT_SCHEMA,
    INTERVIEWER_SCHEMA,
    LAST_QUESTION_SCHEMA,
    LAST_SUGGEST_INPUT,
    LAST_SUGGEST_SCHEMA,
    PANEL_CRITERIA,
    PERSONAS,
    RETRY_SCHEMA,
    STRATEGY_SCHEMA,
)

st.set_page_config(page_title="AI 면접 코치", page_icon=":material/mic:")


def hover_css() -> str:
    """호버를 한 가지로: 주 버튼은 마우스를 올려도 색이 그대로, 나머지 버튼 · 태그는 글자색 그대로 + 아주 옅은 바탕.
    탭은 호버 때 글자색이 바뀌지 않게. (Streamlit 기본은 버튼 종류마다 하늘색 · 회색 · 진한 색으로 제각각)
    고른 탭은 Streamlit 기본 밑줄 그대로 (채운 바탕은 위쪽 모서리 둥글리기를 보장할 수 없어서 쓰지 않는다).
    코드 칸(리포트 미리보기)의 마크다운 제목은 Streamlit 기본이 빨강(.token.important)이라 강조색으로.
    다크에서는 글자라서 강조색(#4263D6, 바탕 대비 3.2)보다 밝은 같은 계열(config.toml linkColor #9DB0F0)을 쓴다."""
    dark = getattr(st.context.theme, "type", None) == "dark"
    accent = "#4263D6" if dark else "#10256B"  # config.toml 강조색과 같게
    heading = "#9DB0F0" if dark else "#10256B"
    return f"""<style>
[data-testid="stCode"] .token.important, [data-testid="stCode"] .token.title {{ color: {heading} !important; }}
[data-testid="stBaseButton-primary"]:hover:not(:disabled),
[data-testid="stBaseButton-primary"]:focus-visible {{
  background-color: {accent} !important; border-color: {accent} !important; color: #FFFFFF !important; }}
[data-testid^="stBaseButton-"]:not([data-testid="stBaseButton-primary"]):not([data-testid$="Active"]):hover:not(:disabled) {{
  background-color: color-mix(in srgb, currentColor 6%, transparent) !important; color: inherit !important; }}
[data-testid="stTabs"] [role="tab"]:not([aria-selected="true"]):hover {{ color: inherit !important; }}
/* 면접 화면 내 답 말풍선: 오른쪽 여백을 16px → 32px (글이 오른쪽 끝에 붙어 보이지 않게) */
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {{ padding-right: 32px !important; }}
/* 암기 탭 질문 카드: 좁은 화면에서도 < 질문 > 을 한 줄로 (Streamlit 은 640px 아래에서 칸을 세로로 쌓는다) */
/* < 윗줄 > 은 카드 양끝이 아니라 윗줄 글 바로 옆에 30px 띄워 가운데로 모은다 */
.st-key-memo_qcard [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; justify-content: center; gap: 30px !important; }}
.st-key-memo_qcard [data-testid="stColumn"]:nth-child(2) {{ flex: 0 1 auto !important; width: auto !important; }}
.st-key-memo_qcard [data-testid="stColumn"] {{ min-width: 0 !important; }}
.st-key-memo_qcard [data-testid="stColumn"]:first-child, .st-key-memo_qcard [data-testid="stColumn"]:last-child {{
  flex: 0 0 44px !important; width: 44px !important; }}
.st-key-memo_qcard [data-testid="stColumn"]:nth-child(2) [data-testid="stCaptionContainer"] {{ text-align: center; }}
.st-key-memo_qcard h4 {{ text-align: center; word-break: keep-all; }}  /* 한국어는 어절 단위로 줄바꿈 */
</style>"""


st.html(hover_css())

# 남는 도움말 닫기: 버튼을 누르면 Streamlit 이 버튼을 새로 그리는데, 그때 열려 있던 도움말(help)은
# '마우스가 떠났다' 신호를 받지 못해 화면에 남는다 (암기 탭 < > 에서 재현). 마우스가 도움말 버튼에도,
# 도움말 위에도 없는데 보이는 도움말은 숨긴다. 고정 문장만 넣는다 — 사용자 글 · AI 출력 · 키는 넣지 않는다.
# (스크립트 글에 태그 모양 글자가 있으면 Streamlit 정리기가 스크립트를 통째로 지우므로 쓰지 않는다)
TOOLTIP_GUARD_JS = """<script>
(() => {
  if (window.__tooltipGuard) return;
  window.__tooltipGuard = true;
  let x = -1, y = -1, timer = 0;
  // 도움말 버튼 칸은 aria-describedby 로 자기 도움말 id 를 가리킨다: 마우스가 그 버튼이나 그 도움말 위일 때만 보인다
  const check = () => {
    const over = x >= 0 ? document.elementFromPoint(x, y) : null;
    const target = over && over.closest('[data-testid="stTooltipHoverTarget"]');
    const hoveredTip = over && over.closest('[role="tooltip"]');
    const mine = target ? target.getAttribute("aria-describedby") : null;
    document.querySelectorAll('[role="tooltip"]').forEach((tip) => {
      tip.style.display = (tip.id && tip.id === mine) || tip === hoveredTip ? "" : "none";
    });
  };
  const later = (ms) => { clearTimeout(timer); timer = setTimeout(check, ms); };
  document.addEventListener("pointermove", (e) => { x = e.clientX; y = e.clientY; later(250); }, true);
  document.addEventListener("click", () => later(700), true);
  document.addEventListener("scroll", () => later(250), true);
})();
</script>"""
st.html(TOOLTIP_GUARD_JS, unsafe_allow_javascript=True)



def scroll_to_top():
    """페이지 맨 위로 (Streamlit 에 스크롤 기능이 없어서 짧은 스크립트로).
    스크립트는 고정 문장이고 숫자(실행 번호)만 넣는다 — 사용자 글 · AI 출력 · 키는 넣지 않는다.
    실행 번호를 넣어야 같은 자리에 다시 그려져도 스크립트가 새로 돈다."""
    state["scroll_seq"] = state.get("scroll_seq", 0) + 1
    st.html(
        f"""<script>/* {int(state["scroll_seq"])} */
for (const el of [document.scrollingElement, ...document.querySelectorAll('[data-testid="stAppScrollToBottomContainer"], [data-testid="stMain"], [data-testid="stAppViewContainer"]')]) {{
  if (el) el.scrollTo({{ top: 0, behavior: "instant" }});
}}
</script>""",
        unsafe_allow_javascript=True,
    )
DEFAULT_TIMEZONE = "Asia/Seoul"  # 브라우저 시간대를 모를 때
DEV_MOCK = os.getenv("DEV_MOCK", "").strip() == "1"  # 개발용 모의 데이터 버튼 (.env 에만, 배포 Secrets 에는 넣지 않는다)
# Streamlit에는 테마를 코드로 바꾸는 공식 기능이 없어서, 기본 설정 메뉴 위치를 알려 준다.
st.caption(":material/contrast: 다크 · 라이트 모드는 오른쪽 위 ⋮ 메뉴 → Settings 에서 바꿀 수 있어요.")


# 리포트 태그: 처음부터 있는 태그 (기준은 비워 두고 사용자가 채운다). 태그 순서 = 상태창 목록 순서
DEFAULT_TAGS = [{"name": "1지망", "rule": ""}, {"name": "2지망", "rule": ""}]


def reset(job: str | None = None, field: str | None = None):
    """job 을 주면 그 분야 · 직군 모드의 시작 화면으로, 없으면 분야 · 직군 고르기 화면으로.
    불러온 리포트 목록(reports) · 그룹(report_groups · report_group_of) · 태그(report_tags · report_tag_of)는
    지우지 않는다 (상태창에서 회사를 바꿔 가며 쓰고, 정해 둔 태그 기준을 다시 쓰도록)."""
    kept = {key: st.session_state.get(key, default) for key, default in
            (("reports", {}), ("report_groups", []), ("report_group_of", {}),
             ("report_tags", None), ("report_tag_of", {}))}
    if kept["report_tags"] is None:
        kept["report_tags"] = [dict(t) for t in DEFAULT_TAGS]
    st.session_state.clear()
    st.session_state.update(kept)
    st.session_state.stage = "start" if job else "pick"
    if job:
        st.session_state.job = job
        st.session_state.field = field if field in FIELDS else coach.DEFAULT_FIELD


if "stage" not in st.session_state:
    reset()

state = st.session_state
if not (state.stage == "start" and state.get("start_mode") == "resume"):
    state.pop("uploader_ids", None)  # 올리기 칸이 안 그려지면 칸이 비워지므로, 직전 목록도 잊는다

# 아이콘 캐릭터 (원작 그래픽 대신 이모지)
AVATARS = {"assistant": ":material/support_agent:", "user": ":material/person:"}


def call_ai(spinner_text: str, instructions: str, user_input: str, schema: dict, name: str, store) -> bool:
    """AI를 한 번 부르고, 결과를 받자마자 store(결과) 로 저장한다. 실패하면 한국어 한 줄 에러.
    Streamlit 은 응답을 기다리는 동안 다른 버튼을 누르면 실행을 멈추고 다시 시작한다.
    저장을 화면 그리기 뒤로 미루면 받은 결과를 버리고 다시 호출하게 돼서, spinner 안에서 바로 저장한다."""
    try:
        with st.spinner(spinner_text):
            store(ask_json(instructions, user_input, schema, name))
    except LLMError as e:
        st.error(str(e))
        return False
    return True


def question_message(index: int) -> dict:
    question = state.questions[index]
    field = question.get("field", coach.DEFAULT_FIELD)
    tag = f" :material/explore: **{field} 질문**" if field != coach.DEFAULT_FIELD else ""
    text = f"**질문 {index + 1}/{coach.TOTAL_QUESTIONS}.**{tag} {question['question']}"
    return {"role": "assistant", "content": text, "q": index, "kind": "question"}


# 상태창 이동은 두 개만: 홈(분야 · 직군을 다시 고름) · 처음부터 다시(같은 모드로 새 면접).
# '분야 다시 고르기' · '직군 다시 고르기' 는 홈이 고르던 값을 미리 골라 두는 것으로 대신한다
# (ui-ux-pro-max: Forms · Redundant Entry — 이전에 고른 값을 다시 입력하게 하지 않기).
NAV_BUTTONS = [
    (":material/home: 홈으로 돌아가기", "home", "분야 · 직군 고르기 화면으로 가요. 고르던 분야 · 직군이 미리 골라져 있어요."),
    (":material/restart_alt: 처음부터 다시", "restart", "같은 분야 · 직군 모드로 새 면접을 시작해요."),
]


def leave(target: str):
    """상태창 이동. home: 분야 · 직군 고르기 (고르던 값 유지) · restart: 같은 모드로 새 면접."""
    job, field = state.get("job"), state.get("field")
    if target == "restart":
        reset(job, field)
        return
    reset()
    if field:
        state.pick_field = field   # 고르던 분야를 그대로 골라 둔다
    if job:
        state.pick_job_hint = job  # 고르던 직군에 체크 표시


def job_reports() -> dict:
    """불러온 리포트 중 지금 직군 것만 (올린 순서대로)."""
    return {fid: r for fid, r in state.get("reports", {}).items() if r["profile"]["job"] == state.get("job")}


MAX_GROUP_NAME_CHARS = 20
NO_GROUP = "그룹 없음"


def remove_report(fid: str):
    """불러온 목록에서 리포트를 뺀다 (내 컴퓨터의 파일은 그대로). 이어 하던 리포트면 시작 화면 칸도 비운다."""
    state.reports.pop(fid, None)
    state.setdefault("report_group_of", {}).pop(fid, None)
    state.setdefault("report_tag_of", {}).pop(fid, None)
    state.setdefault("report_errors", {}).pop(fid, None)
    if state.get("active_report") == fid:
        state.active_report = None
        if state.stage in ("start", "briefing"):
            state.previous = None  # 면접 중이면 '지난 면접과 비교' 는 그대로 둔다


def set_report_group(fid: str):
    """리포트 관리의 그룹 고르기 칸이 바뀌면 그 값으로 그룹을 바꾼다."""
    group = state[f"group_of_{fid}"]
    if group == NO_GROUP:
        state.report_group_of.pop(fid, None)
    else:
        state.report_group_of[fid] = group


def add_group():
    name = state.get("new_group", "").strip()
    if not name:
        state.group_msg = "그룹 이름을 적어 주세요."
    elif name == NO_GROUP or name in state.report_groups:
        state.group_msg = f"'{name}' 은(는) 이미 있는 이름이에요. 다른 이름을 적어 주세요."
    else:
        state.report_groups.append(name)
        state.new_group = ""
        state.group_msg = None


def remove_group(name: str):
    """그룹만 지운다. 속한 리포트는 '그룹 없음' 으로 옮긴다."""
    state.report_groups.remove(name)
    for fid in [f for f, g in state.report_group_of.items() if g == name]:
        del state.report_group_of[fid]


MAX_TAG_NAME_CHARS = 10
MAX_TAG_RULE_CHARS = 60
NO_TAG = "태그 없음"


def tag_rank(fid: str) -> int:
    """상태창에서 태그 순서대로 (1지망 → 2지망 → … → 태그 없음)."""
    names = [t["name"] for t in state.report_tags]
    tag = state.report_tag_of.get(fid)
    return names.index(tag) if tag in names else len(names)


def set_report_tag(fid: str):
    tag = state[f"tag_of_{fid}"]
    if tag == NO_TAG:
        state.report_tag_of.pop(fid, None)
    else:
        state.report_tag_of[fid] = tag


def set_tag_rule(i: int):
    state.report_tags[i]["rule"] = state[f"tag_rule_{i}"].strip()


def add_tag():
    name = state.get("new_tag", "").strip()
    if not name:
        state.tag_msg = "태그 이름을 적어 주세요."
    elif name == NO_TAG or name in [t["name"] for t in state.report_tags]:
        state.tag_msg = f"'{name}' 은(는) 이미 있는 태그예요. 다른 이름을 적어 주세요."
    else:
        state.report_tags.append({"name": name, "rule": state.get("new_tag_rule", "").strip()})
        state.new_tag, state.new_tag_rule = "", ""
        state.tag_msg = None


def remove_tag(i: int):
    """태그만 지운다. 그 태그가 붙은 리포트는 '태그 없음' 으로."""
    name = state.report_tags.pop(i)["name"]
    for fid in [f for f, t in state.report_tag_of.items() if t == name]:
        del state.report_tag_of[fid]
    for key in [k for k in state if str(k).startswith("tag_rule_")]:
        del state[key]  # 번호가 밀리므로 기준 칸 값을 새로 채운다


def activate_report(fid: str):
    """불러온 리포트 하나를 '이어 할 회차' 로 정하고 시작 화면 칸을 채운다."""
    report = state.reports[fid]
    state.active_report = fid
    state.previous = report
    state.start_mode = "resume"
    state.field = report["profile"]["field"]  # 이어 하는 리포트의 분야로 맞춘다
    for field in ("name", "company", "company_desc", "experience"):
        state[f"f_{field}"] = report["profile"][field]
    # 경험 칸 글자 수 상한에 맞춘다 (상한보다 긴 값을 넣으면 칸이 에러를 낸다)
    state.f_experience = state.f_experience[: coach.MAX_EXPERIENCE_CHARS]


def resume_without_interview(previous: dict, name, job, company, company_desc, experience, notice: str | None = None):
    """면접을 다시 하지 않고 리포트의 결과로 같은 회차를 이어 간다 (면접이 끝난 상태로 시작).
    시작 화면에서 부르므로 시작 화면 코드보다 위에 둔다. 개발용 모의 데이터도 이 길로 연다."""
    try:
        questions = coach.match_questions(coach.load_questions(), job, previous["questions"])
    except (OSError, ValueError, KeyError):
        st.error("질문 은행(data/questions.csv)을 읽지 못했어요.")
        return
    if questions is None:
        st.warning("지난 질문 중 질문 은행에 없는 질문이 있어서 이어 할 수 없어요. 체크를 풀고 새 면접으로 시작해 주세요.")
        return
    session = coach.rebuild_session(previous["session"], questions)
    state.profile = {
        "name": name, "field": state.get("field", coach.DEFAULT_FIELD), "job": job,
        "company": company, "company_desc": company_desc, "experience": experience,
    }
    state.questions = questions
    state.round = previous["round"]   # 같은 회차를 이어 간다
    state.previous = None             # 같은 회차라 '지난 면접과 비교' 는 하지 않는다
    restore_precheck(previous["precheck"])
    state.q_index = coach.TOTAL_QUESTIONS
    state.follow_ups = 0
    for key in ("messages", "evaluation", "retries", "retry_history", "retry_counts", "last_suggest", "last_question", "understanding"):
        state[key] = session[key]
    state.highlights, state.strategies = {}, {}
    state.memo_edits, state.memo_reviews = {}, {}  # 검토 내역은 retry_history 의 몇 번째인지라 새 기록과 맞지 않는다
    # 실마리: 리포트에 저장돼 있으면 그 회차 · 목록에서 이어 간다 (없으면 1회차 · 새로 찾기)
    state.pop("clue_set", None)
    if session["clue_set"] is not None:
        state.clue_set = session["clue_set"]
    state.clue_round = session["clue_round"]
    state.verdict_open = False
    state.same_questions = True
    state.open_eval = True            # 평가 탭부터 보여 준다
    state.notice = notice or f"{previous['round']}회차 결과를 불러왔어요. 면접 없이 평가 · 재도전 · 암기 · 리포트를 이어서 할 수 있어요."
    state.stage = "done"
    st.rerun()


def restore_precheck(saved: dict):
    """지난 회차 리포트의 체크 · 메모를 지금 체크리스트에 채운다 (항목 글자로 맞춘다).
    시작 화면에서 부르므로 시작 화면 코드보다 위에 둔다."""
    try:
        items = coach.load_precheck()
    except (OSError, KeyError, ValueError):
        return
    for i, item in enumerate(items):
        if item["item"] in saved:
            value = saved[item["item"]]
            state[f"pre_found_{i}"] = value["found"]
            state[f"pre_missing_{i}"] = value["missing"]
            state[f"pre_memo_{i}"] = value["memo"][: coach.MAX_MEMO_CHARS]  # 메모 칸 글자 수 상한에 맞춤


# ── 사이드바 상태창 ──────────────────────────────────────────
with st.sidebar:
    st.header("상태창")
    if state.get("job"):
        st.markdown(
            f"**{state.get('field', coach.DEFAULT_FIELD)} · {state.job} 직군 모드**"
            + (f" · {state.round}회차" if state.get("round") else "")
        )
    if state.stage == "pick":
        st.caption("분야와 직군을 고르면 그 모드로 시작해요.")
    elif state.stage == "start":
        st.caption("면접을 시작하면 진행 상황이 보여요.")
    elif state.stage == "briefing":
        st.caption("브리핑을 확인하고 면접을 시작해 주세요.")
    else:
        answered = state.q_index
        current = min(answered + 1, coach.TOTAL_QUESTIONS)
        st.progress(answered / coach.TOTAL_QUESTIONS, text=f"질문 {current}/{coach.TOTAL_QUESTIONS}")
        st.metric("면접관이 본 이해도", "-" if state.understanding is None else f"{state.understanding}/100")
        if state.get("evaluation"):
            ev = state.evaluation
            totals = coach.total_scores(ev, state.get("retries", {}))
            st.metric(
                "종합 점수", f"{totals['latest']}/{coach.TOTAL_MAX}",
                delta=totals["diff"] or None, help="재도전한 질문은 재도전 점수로 바꿔 넣은 합이에요.",
            )
            st.metric("위원 평균", f"{ev['panel_average']:.1f}/{coach.PANEL_MAX}")
    # 불러온 리포트: 누르면 그 회사로 바꾼다. 면접 중이면 기록이 사라지니 한 번 더 확인한다.
    loaded = job_reports() if state.stage != "pick" else {}
    if loaded:
        st.divider()
        st.markdown("**:material/folder_open: 불러온 리포트**")
        groups = state.setdefault("report_groups", [])
        group_of = state.setdefault("report_group_of", {})
        tags = state.setdefault("report_tags", [dict(t) for t in DEFAULT_TAGS])
        tag_of = state.setdefault("report_tag_of", {})
        tag_rules = {t["name"]: t["rule"] for t in tags}
        loaded = dict(sorted(loaded.items(), key=lambda item: tag_rank(item[0])))  # 1지망 → 2지망 → … 순서

        def report_label(fid: str) -> str:
            report = loaded[fid]
            return f"{report['profile']['company']} · {report['round']}회차 ({report['date'][5:]})"

        def report_button(fid: str):
            active = state.get("active_report") == fid
            tag = tag_of.get(fid) if tag_of.get(fid) in tag_rules else None
            label = (":material/check: " if active else "") + (f"`{tag}` " if tag else "") + report_label(fid)
            tip = (f"{tag} 기준: {tag_rules[tag]}" if tag_rules[tag] else f"{tag} · 기준은 '리포트 관리' 에서 적을 수 있어요") if tag else None
            if st.button(label, key=f"report_{fid}", width="stretch", type="primary" if active else "secondary", help=tip):
                if state.stage in ("start", "briefing"):
                    activate_report(fid)
                    state.stage = "start"
                    st.rerun()
                elif not active:
                    state.switch_pending = fid
                    st.rerun()

        # 그룹 없는 리포트 먼저, 그다음 그룹마다 접기 칸 (이어 하는 리포트가 든 그룹은 펼쳐 둔다)
        for fid in loaded:
            if group_of.get(fid) not in groups:
                report_button(fid)
        for group in groups:
            members = [fid for fid in loaded if group_of.get(fid) == group]
            with st.expander(f":material/folder: {group} ({len(members)})",
                             expanded=state.get("active_report") in members):
                if not members:
                    st.caption("비어 있어요. '리포트 관리' 에서 리포트를 넣어 주세요.")
                for fid in members:
                    report_button(fid)

        with st.popover(":material/tune: 리포트 관리", width="stretch"):
            st.markdown("**그룹 만들기**")
            st.text_input("새 그룹 이름", key="new_group", max_chars=MAX_GROUP_NAME_CHARS,
                          placeholder="예: 1지망 · 핀테크")
            st.button(":material/create_new_folder: 그룹 만들기", on_click=add_group, width="stretch")
            if state.get("group_msg"):
                st.info(state.group_msg)
            st.markdown("**태그 설정**")
            st.caption("1지망 · 2지망처럼 기준을 한 번 적어 두면, 리포트마다 태그만 골라 바로 다시 쓸 수 있어요. "
                       "상태창 목록은 태그 순서대로 보여요.")
            for i, tag in enumerate(tags):
                state.setdefault(f"tag_rule_{i}", tag["rule"])
                rule_col, del_col = st.columns([4, 1], vertical_alignment="bottom")
                rule_col.text_input(f"`{tag['name']}` 기준", key=f"tag_rule_{i}", max_chars=MAX_TAG_RULE_CHARS,
                                    placeholder="예: 연봉 4천 이상 · 핀테크 · 서울", on_change=set_tag_rule, args=(i,))
                del_col.button(":material/delete:", key=f"del_tag_{i}", help=f"'{tag['name']}' 태그 지우기 "
                               "(붙어 있던 리포트는 '태그 없음' 으로)", on_click=remove_tag, args=(i,))
            name_col, new_rule_col = st.columns([2, 3])
            name_col.text_input("새 태그", key="new_tag", max_chars=MAX_TAG_NAME_CHARS, placeholder="예: 3지망")
            new_rule_col.text_input("기준", key="new_tag_rule", max_chars=MAX_TAG_RULE_CHARS, placeholder="예: 경험 쌓기용")
            st.button(":material/new_label: 태그 추가", on_click=add_tag, width="stretch")
            if state.get("tag_msg"):
                st.info(state.tag_msg)
            st.markdown("**리포트마다 태그 · 그룹 · 삭제**")
            options = [NO_GROUP, *groups]
            tag_options = [NO_TAG, *tag_rules]
            for fid in loaded:
                key, tag_key = f"group_of_{fid}", f"tag_of_{fid}"
                state[key] = group_of.get(fid) if group_of.get(fid) in groups else NO_GROUP  # 지운 그룹은 '그룹 없음'
                state[tag_key] = tag_of.get(fid) if tag_of.get(fid) in tag_rules else NO_TAG  # 지운 태그는 '태그 없음'
                st.markdown(f"**{report_label(fid)}**")
                tag_col, group_col, del_col = st.columns([2, 2, 1], vertical_alignment="bottom")
                tag_col.selectbox("태그", tag_options, key=tag_key, on_change=set_report_tag, args=(fid,))
                group_col.selectbox("그룹", options, key=key, on_change=set_report_group, args=(fid,))
                if del_col.button(":material/delete:", key=f"del_report_{fid}", help="목록에서 빼기"):
                    state.delete_pending = fid
                    st.rerun()
            if groups:
                st.markdown("**그룹 지우기**")
                st.caption("그룹만 지워요. 속한 리포트는 '그룹 없음' 으로 옮겨져요.")
                for group in groups:
                    st.button(f":material/folder_delete: '{group}' 그룹 지우기", key=f"del_group_{group}",
                              on_click=remove_group, args=(group,), width="stretch")
            st.caption(":material/info: 목록 · 그룹 · 태그는 이 화면에만 있어요. 새로고침하면 사라지니, "
                       "리포트 파일은 내 컴퓨터에 보관해 주세요.")

        doomed = state.get("delete_pending")
        if doomed in loaded:
            st.warning(f"'{report_label(doomed)}' 리포트를 목록에서 뺄까요? 내 컴퓨터의 파일은 지워지지 않아요.")
            yes_col, no_col = st.columns(2)
            if yes_col.button("빼기", type="primary", width="stretch"):
                state.setdefault("report_dismissed", set()).add(doomed)  # 올리기 칸에 남아 있어도 다시 넣지 않는다
                remove_report(doomed)
                state.delete_pending = None
                st.rerun()
            if no_col.button("취소", key="cancel_delete", width="stretch"):
                state.delete_pending = None
                st.rerun()
        pending = state.get("switch_pending")
        if pending in loaded:
            company = loaded[pending]["profile"]["company"]
            st.warning(f"'{company}' 로 바꾸면 지금 면접 기록이 사라져요. :material/description: 리포트를 받아 두었나요?")
            yes_col, no_col = st.columns(2)
            if yes_col.button("바꾸기", type="primary", width="stretch"):
                reset(state.job, state.get("field"))
                activate_report(pending)
                st.rerun()
            if no_col.button("취소", width="stretch"):
                state.switch_pending = None
                st.rerun()
        st.divider()

    # 이동 버튼. 면접 중 · 끝난 뒤에는 기록이 사라지니 한 번 더 확인한다.
    if state.stage != "pick":
        for label, target, tip in NAV_BUTTONS:
            if st.button(label, key=f"nav_{target}", width="stretch", help=tip):
                if state.stage in ("interview", "done"):
                    state.leave_pending = target
                else:
                    leave(target)
                st.rerun()
        target = state.get("leave_pending")
        if target:
            st.warning("지금 면접 기록이 사라져요. :material/description: 리포트를 받아 두었나요?")
            go_col, stay_col = st.columns(2)
            if go_col.button("이동하기", type="primary", width="stretch"):
                leave(target)
                st.rerun()
            if stay_col.button("머무르기", width="stretch"):
                state.leave_pending = None
                st.rerun()


# ── 분야 · 직군 고르기 ──────────────────────────────────────
if state.stage == "pick":
    st.title("AI 면접 코치")
    st.write("신입 모의면접이에요. 먼저 지원할 **분야**와 **직군**을 골라 주세요.")
    if state.get("pick_field") not in FIELDS:
        state.pick_field = coach.DEFAULT_FIELD
    field = st.pills("① 분야", list(FIELDS), key="pick_field", required=True)
    st.caption(f"{field} · {FIELDS[field]}. 면접관과 평가 위원회가 이 분야를 고려해요.")
    st.markdown("**② 직군**")
    hint = state.get("pick_job_hint")
    for column, job in zip(st.columns(len(coach.JOBS)), coach.JOBS):
        if column.button((":material/check: " if job == hint else "") + job, key=f"pick_job_{job}", width="stretch",
                         type="primary" if PERSONAS[job] else "secondary"):
            if PERSONAS[job]:
                reset(job, field)
                st.rerun()
            else:
                st.info(f"'{job}' 직군 모드는 준비 중이에요. 면접관 페르소나가 아직 없어요.")
    st.stop()


# ── 시작 화면 ───────────────────────────────────────────────
if state.stage == "start":
    job = state.job
    field = state.get("field", coach.DEFAULT_FIELD)
    st.title(f"{field} · {job} 직군 모드")
    st.write("신입 모의면접이에요. 질문 5개와 꼬리 질문으로 진행해요.")

    # 두 갈래 시작: 새 면접 / 이전 면접 이어하기
    mode = state.get("start_mode")
    new_col, resume_col = st.columns(2)
    if new_col.button("🆕 새 면접 시작하기", width="stretch", type="primary" if mode == "new" else "secondary"):
        if mode != "new":
            for key in ("previous", "active_report", "f_name", "f_company", "f_company_desc", "f_experience"):
                state.pop(key, None)  # 이어하기에서 채운 값을 비우고 새로 시작 (불러온 목록은 남긴다)
        state.start_mode = "new"
        st.rerun()
    if resume_col.button(":material/folder_open: 이전 면접 이어하기", width="stretch", type="primary" if mode == "resume" else "secondary"):
        state.start_mode = "resume"
        if not state.get("previous") and job_reports():
            activate_report(list(job_reports())[-1])  # 이미 불러온 리포트가 있으면 마지막 것으로
        st.rerun()
    # 개발용: .env 에 DEV_MOCK=1 일 때만. AI를 부르지 않고 만점 모의 면접이 끝난 상태로 연다.
    if DEV_MOCK and job == "디자인":
        if st.button(":material/science: 모의 데이터로 열기 (개발용 · 만점)", help="data/mock_perfect.json · 위원 평균 10점 · 종합 100점"):
            try:
                mock = coach.load_mock()
            except (OSError, ValueError, KeyError) as e:
                st.error(f"모의 데이터를 읽지 못했어요. {e}")
            else:
                p = mock["profile"]
                state.field = p["field"]
                resume_without_interview(mock, p["name"], job, p["company"], p["company_desc"], p["experience"],
                                         notice="개발용 모의 데이터(만점)를 열었어요. 글은 모두 예시예요.")
    if not mode:
        st.caption("처음이면 '새 면접 시작하기', 지난 회차 면접리포트.md 가 있으면 '이전 면접 이어하기' 를 눌러 주세요.")
        st.stop()

    skipping = bool(state.get("previous")) and bool(state.get("resume_skip"))
    if skipping:
        st.caption(f"이어서 할 회차: **{state.previous['round']}회차** (면접 없이)")
    else:
        st.caption(f"이번 면접: **{coach.next_round(state.get('previous'))}회차**")

    if mode == "resume":
        files = st.file_uploader(
            "이어서 할 면접리포트.md 를 올려 주세요. 회사마다 하나씩, 여러 개 올릴 수 있어요.",
            type=["md"],
            accept_multiple_files=True,
            help="파일 하나에는 그 회차 데이터만 들어 있어요. 올린 리포트는 왼쪽 상태창에서 바꿔 가며 쓸 수 있어요.",
        )
        errors = state.setdefault("report_errors", {})
        # 올리기 칸에서 X 로 지운 파일은 불러온 목록에서도 뺀다.
        # (칸이 화면에 없던 동안에는 비교할 직전 목록이 없어서 아무것도 빼지 않는다)
        now_ids = [f.file_id for f in files or []]
        removed = [fid for fid in state.get("uploader_ids", []) if fid not in now_ids]
        state.uploader_ids = now_ids
        if removed:
            for fid in removed:
                remove_report(fid)
            st.rerun()
        newest = None
        for f in files or []:
            if f.file_id in state.reports or f.file_id in errors or f.file_id in state.get("report_dismissed", set()):
                continue  # 올린 파일은 한 번만 읽는다 · 상태창에서 뺀 파일은 다시 넣지 않는다
            try:
                data = coach.parse_report(f.getvalue().decode("utf-8", errors="replace"))
            except ValueError as e:
                errors[f.file_id] = f"{f.name}: {e}"
                continue
            if data["profile"]["job"] != job:
                errors[f.file_id] = (
                    f"{f.name}: '{data['profile']['job']}' 직군 리포트예요. "
                    "상태창의 '홈으로 돌아가기' 에서 그 직군을 골라 주세요."
                )
                continue
            state.reports[f.file_id] = {**data, "file_name": f.name}
            newest = f.file_id
        for f in files or []:
            if f.file_id in errors:
                st.warning(errors[f.file_id])
        if newest:
            activate_report(newest)  # 마지막으로 올린 리포트로 이어 한다
            st.rerun()
        if len(job_reports()) > 1:
            st.caption(":material/folder_open: 리포트를 여러 개 불러왔어요. 왼쪽 상태창에서 눌러 회사를 바꿀 수 있어요.")

        previous = state.get("previous")
        if previous:
            st.success(
                f"**{previous['profile']['company']}** {previous['round']}회차({previous['date']}) 면접을 불러왔어요. "
                f"이번 면접은 {coach.next_round(previous)}회차로 기록돼요. 아래 칸을 채웠으니 확인해 주세요."
            )
            if previous["precheck"]:
                st.caption(f"사전 정보 탐색 체크 · 메모 {len(previous['precheck'])}개도 이어서 채워져요.")
            if coach.criteria_changed(previous):
                st.warning("지난 회차와 평가 기준이 달라서 점수 비교가 정확하지 않을 수 있어요.")
            last_col, total_col = st.columns(2)
            last_col.metric("지난 위원 평균", f"{previous['panel_average']:.1f}/{coach.PANEL_MAX}")
            if previous["total_latest"] is not None:
                total_col.metric("지난 최신 종합", f"{previous['total_latest']}/{coach.TOTAL_MAX}")
            if previous["next"]:
                st.markdown("**지난번에 고칠 것으로 받은 것**")
                for item in previous["next"]:
                    st.markdown(f"- {item}")
            # 면접을 다시 하지 않고 지난 결과로 이어 하기 (동의 체크처럼 직접 체크해야 적용)
            if previous.get("session"):
                with st.container(border=True):
                    st.checkbox(
                        f"**(선택) 면접을 다시 하지 않고, {previous['round']}회차 결과로 이어서 연습할게요**",
                        key="resume_skip",
                    )
                    st.caption(
                        f"체크하면 면접 없이 **같은 {previous['round']}회차**의 평가 · 재도전 · 암기 · 점검하기 · 리포트부터 이어서 해요. "
                        f"체크하지 않으면 **{coach.next_round(previous)}회차** 면접을 새로 시작해요."
                    )
            else:
                state.resume_skip = False
                st.caption("이 리포트에는 면접 결과 데이터가 없어서, 면접 없이 이어 하기는 할 수 없어요. (결과 저장 기능 전에 받은 리포트)")
            if not state.get("resume_skip"):
                st.radio(
                    "질문",
                    ["같은 질문으로 다시 (성장 비교)", "새 질문으로"],
                    key="previous_mode",
                    help="같은 질문이면 질문별 점수를 지난번과 비교해 보여 줘요.",
                )
        else:
            st.caption("리포트를 올리면 아래에 지난 회차 내용이 채워져요.")
            st.stop()

    with st.form("start"):
        name = st.text_input("이름", key="f_name")
        company = st.text_input("회사", key="f_company")
        company_desc = st.text_input(
            "회사 설명", key="f_company_desc", help="어떤 서비스를 하는 회사인지 한 줄로 적어 주세요."
        )
        experience = st.text_area(
            "내 경험",
            height=150,
            key="f_experience",
            max_chars=coach.MAX_EXPERIENCE_CHARS,
            help=f"면접관이 참고할 경험을 {coach.MIN_EXPERIENCE_CHARS}~{coach.MAX_EXPERIENCE_CHARS}자로 적어 주세요.",
        )
        started = st.form_submit_button(
            "지난 결과로 이어서 하기" if state.get("previous") and state.get("resume_skip") else "면접 시작하기",
            type="primary",
        )

    if started:
        name, company, experience = name.strip(), company.strip(), experience.strip()
        company_desc = company_desc.strip()
        if not name or not company or not company_desc or not experience:
            st.warning("이름 · 회사 · 회사 설명 · 내 경험을 모두 적어 주세요.")
        elif len(experience) < coach.MIN_EXPERIENCE_CHARS:
            st.warning(f"내 경험을 {coach.MIN_EXPERIENCE_CHARS}자 이상 적어 주세요. (지금 {len(experience)}자)")
        elif state.get("previous") and state.get("resume_skip"):
            resume_without_interview(state.previous, name, job, company, company_desc, experience)
        else:
            previous = state.get("previous")
            same = bool(previous) and state.get("previous_mode", "").startswith("같은 질문")
            try:
                bank = coach.load_questions()
                matched = coach.match_questions(bank, job, previous["questions"]) if same else None
                if same and matched is None:
                    state.notice = "지난 질문 중 질문 은행에 없는 질문이 있어서 새 질문으로 시작했어요."
                questions = matched or coach.pick_questions(bank, job, state.get("field", coach.DEFAULT_FIELD))
            except (OSError, ValueError, KeyError):
                st.error("질문 은행(data/questions.csv)을 읽지 못했어요.")
            else:
                state.profile = {
                    "name": name,
                    "field": state.get("field", coach.DEFAULT_FIELD),
                    "job": job,
                    "company": company,
                    "company_desc": company_desc,
                    "experience": experience,
                }
                state.questions = questions
                state.round = coach.next_round(previous)
                if previous:
                    restore_precheck(previous["precheck"])
                state.q_index = 0
                state.follow_ups = 0
                state.understanding = None
                state.evaluation = None
                state.pop("clue_set", None); state.pop("clue_round", None)  # 새 평가에서 실마리를 다시 찾는다
                state.retries = {}
                state.retry_history = {}
                state.memo_edits, state.memo_reviews = {}, {}  # 고친 대본 · 검토 내역은 질문이 바뀌면 맞지 않는다
                state.last_question = None
                state.last_suggest = None
                state.highlights = {}
                state.strategies = {}
                state.retry_counts = {}
                state.verdict_open = False
                state.messages = [
                    {"role": "assistant", "content": f"{name} 님, 면접을 시작하겠습니다."},
                    question_message(0),
                ]
                state.same_questions = matched is not None
                state.stage = "briefing"
                st.rerun()
    st.stop()


# ── 면접 브리핑 ─────────────────────────────────────────────
if state.stage == "briefing":
    profile = state.profile
    st.title("면접 브리핑")
    with st.container(border=True):
        st.markdown(f"**:material/business: 회사** · {profile['company']} ({profile['company_desc']})")
        st.markdown(f"**:material/explore: 분야** · {coach.field_of(profile)} ({FIELDS[coach.field_of(profile)]})")
        st.markdown(f"**:material/work: 직군** · {profile['job']} 신입 · {state.round}회차")
        st.markdown(f"**{AVATARS['assistant']} 면접관** · {coach.persona_summary(profile['job'])}")
        kinds = " → ".join(
            q["type"] + (" :material/explore:" if q.get("field", coach.DEFAULT_FIELD) != coach.DEFAULT_FIELD else "")
            for q in state.questions
        )
        field_count = sum(1 for q in state.questions if q.get("field", coach.DEFAULT_FIELD) != coach.DEFAULT_FIELD)
        if field_count:
            kinds += f" · :material/explore: {coach.field_of(profile)} 분야 질문 {field_count}개"
        st.markdown(f"**:material/quiz: 질문** · {coach.TOTAL_QUESTIONS}개 ({kinds})")
        if state.get("same_questions"):
            st.caption("지난 회차와 같은 질문이에요. 평가 후 질문별로 점수를 비교해 드려요.")
    st.markdown(
        f"- 질문은 한 번에 하나씩 나와요. 답이 부족하면 면접관이 **꼬리 질문을 최대 {coach.MAX_FOLLOW_UPS}개** 해요.\n"
        f"- 답은 한 번에 **{coach.MAX_ANSWER_CHARS:,}자**까지 쓸 수 있어요.\n"
        "- 면접이 끝나면 위원 4명이 평가하고, 점수가 낮은 질문은 다시 도전할 수 있어요.\n"
        "- 새로고침하면 진행 기록이 사라져요. 평가 뒤 위쪽 :material/description: 리포트 저장하기 버튼에서 면접리포트.md 를 받아 두세요."
    )
    begin_col, back_col = st.columns([2, 1])
    if begin_col.button("면접을 시작하겠습니다.", type="primary", width="stretch"):
        state.stage = "interview"
        st.rerun()
    if back_col.button("설정 수정하기", width="stretch"):
        for field in ("name", "company", "company_desc", "experience"):
            state[f"f_{field}"] = profile[field]  # 입력한 값을 그대로 다시 채운다
        state.stage = "start"
        st.rerun()
    st.stop()


# ── 면접 화면 ───────────────────────────────────────────────
profile = state.profile
for state_key, empty in (
    ("highlights", {}), ("last_suggest", None), ("last_question", None), ("previous", None), ("round", 1),
    ("strategies", {}), ("retry_counts", {}), ("verdict_open", False), ("memo_results", {}), ("memo_best", {}),
    ("speak_logs", {}), ("reports", {}), ("retry_history", {}), ("memo_edits", {}), ("memo_reviews", {}),
):
    if state_key not in state:  # 이 기능이 생기기 전에 시작한 세션도 열리게
        state[state_key] = empty
if state.get("notice"):
    st.info(state.pop("notice"))


def memo_summary() -> dict:
    """암기 탭 기록 요약 (체크리스트용): 말하기 타이머로 기록한 횟수 · 대본을 고친 질문 수 · 실전 시뮬레이션을 확인한 질문 수."""
    speak = sum(len(v) for logs in state.get("speak_logs", {}).values()
                for v in (logs.values() if isinstance(logs, dict) else [logs]))
    edited = len({key.split(":")[0] for key in state.get("memo_edits", {})})
    checked = len({key.split(":")[0] for key in state.get("memo_results", {})})
    return {"speak": speak, "edited": edited, "checked": checked}


def checklist_rows(report_done: bool | None = None) -> list[dict]:
    """단계 체크리스트 (탭 6개 + 리포트). 진행 막대 · 리포트 창 체크리스트 · 마침 안내가 같이 쓴다."""
    try:
        precheck_items = coach.load_precheck()
    except (OSError, KeyError, ValueError):
        precheck_items = []
    ev = state.get("evaluation")
    clues = coach.clue_status(ev, state.get("retries", {}), state.get("retry_counts", {}),
                              state.get("clue_set"), state.get("clue_round", 1)) if ev else None
    return coach.report_checklist(
        state.get("messages", []), ev, clues, bool(state.get("verdict_open")), memo_summary(),
        state.get("last_suggest"), state.get("last_question"), precheck_items, current_precheck(precheck_items),
        bool(state.get("report_downloaded")) if report_done is None else report_done,
    )


def build_current_report(ev: dict, updated_at: str | None = None) -> str:
    """지금 회차의 면접리포트.md (리포트 창 · 다음 회차 진행이 같이 쓴다)."""
    try:
        precheck_items = coach.load_precheck()
    except (OSError, KeyError, ValueError):
        precheck_items = []
    return coach.build_report(
        profile, state.questions, ev, state.retries, state.messages,
        state.last_suggest, state.last_question, state.previous, state.round,
        precheck_items, current_precheck(precheck_items), updated_at, user_now().date(),
        retry_counts=state.retry_counts, understanding=state.understanding,
        retry_history=state.get("retry_history", {}),
        clue_set=state.get("clue_set"), clue_round=state.get("clue_round", 1), memo=memo_summary(),
        verdict_open=bool(state.get("verdict_open")),
        practice=current_practice(),
    )


def past_reports() -> list[dict]:
    """지난 회차 리포트: 불러온 리포트 중 지금 직군 것 + 이어 하는 리포트 (같은 것은 한 번만)."""
    reports = list(job_reports().values())
    if state.get("previous") and all(state.previous is not r for r in reports):
        reports.append(state.previous)
    return reports


def current_practice() -> list[dict]:
    """리포트에 남길 연습 대본: 지난 회차 대본 + 이번 회차 암기 탭에서 고치거나 직접 쓴 대본 (질문 글 기준).
    다음 회차의 암기 탭 '다른 질문' 에서 '내 연습 대본 (n회차)' 로 다시 나온다."""
    texts = {q["question"]: q["question"] for q in state.get("questions", [])}
    by_id = {coach.practice_id(t): t for t in texts}
    by_id.update({q["id"]: q["question"] for q in other_questions()})
    current = {}
    for key, script in state.get("memo_edits", {}).items():
        head = key.split(":")[0]
        if head.isdigit() and 1 <= int(head) <= len(state.get("questions", [])):
            current[state.questions[int(head) - 1]["question"]] = script
        elif head in by_id:
            current[by_id[head]] = script
    return coach.merge_practice(coach.saved_practice(past_reports()), current, int(state.get("round", 1)))


def go_next_round():
    """다음 회차 면접: 지금 회차를 리포트로 만들어 '불러온 리포트' 에 넣고, 그 리포트로 이어 하는 시작 화면을 연다.
    (리포트 파일을 받아 다시 올리는 것과 같은 길. 버튼 콜백이라 다음 실행 전에 돈다.)"""
    data = coach.parse_report(build_current_report(state.evaluation))
    data["file_name"] = coach.report_file_name(profile["company"], profile["job"], state.round, user_now().date())
    fid = f"round-{state.round}-{time.time_ns()}"
    reset(profile["job"], coach.field_of(profile))
    state.reports[fid] = data
    activate_report(fid)  # 시작 화면 칸을 채우고 '이번 면접: 다음 회차' 로
    state.stage = "start"


next_round_no = coach.next_round({"round": state.round})
st.title(f"{profile['company']} · {coach.field_of(profile)} · {profile['job']} 신입 면접 · {state.round}회차")
def ask_report():
    state.open_report = True  # 창은 아래(함수를 다 정의한 뒤)에서 연다


# 다음 회차 · 리포트 버튼을 한 줄에 (리포트는 탭이 아니라 넓은 창으로 본다)
with st.container(horizontal=True, gap="small"):
    next_clicked = st.button(f":material/skip_next: {next_round_no}회차 면접 진행하기", key="next_round",
                             help="지금 회차를 리포트로 남기고, 같은 회사로 다음 회차 면접을 시작해요.")
    st.button(":material/description: 리포트 저장하기", key="open_report_btn", on_click=ask_report,
              help="면접리포트.md 를 미리 보고 내려받아요. 다음 회차 시작 화면에 올리면 이어서 할 수 있어요.")
if next_clicked:
    if not state.get("evaluation"):
        st.info("위원 4명에게 평가받은 뒤에 다음 회차 면접을 진행할 수 있어요.")
    else:
        state.open_next_round = True  # 안내 창은 아래(함수를 다 정의한 뒤)에서 연다


def next_round_dialog():
    """'n회차 면접 진행하기' 안내 창: 오른쪽 위 X 로 닫고(머무르기), 아래 [저장하기] [n회차 시작하기].
    제목에 회차 숫자가 들어가서 열 때마다 대화 상자를 만든다."""
    @st.dialog(f"{next_round_no}회차 면접 진행하기")
    def body():
        st.write(f"{next_round_no}회차로 넘어가면 지금 화면의 기록은 사라지고, 왼쪽 '불러온 리포트' 에 "
                 f"{state.round}회차로 남아요. 목록은 새로고침하면 사라지니 먼저 리포트를 저장해 두세요.")
        st.caption(":material/lock: 리포트에는 이름 · 회사 · 내 경험 원문 · 면접 대화 · 답변 · 체크리스트 메모가 들어가요. "
                   "다른 사람과 공유할 때 주의해 주세요.")
        # 리포트 창과 같은 규칙: 개인정보 안내를 확인해야 저장 버튼이 켜진다 (사용자 요청 — disabled 예외)
        agreed = st.checkbox("위 안내를 확인했어요. 개인정보가 들어간 파일이라는 걸 알고 내려받을게요.", key="next_agree")
        file_name = coach.report_file_name(profile["company"], profile["job"], state.round, user_now().date())
        save_col, go_col = st.columns(2)
        save_col.download_button(
            ":material/download: 저장하기", data=build_current_report(state.evaluation, user_now().strftime("%Y-%m-%d %H:%M")),
            file_name=file_name, mime="text/markdown", disabled=not agreed, width="stretch",
            on_click=mark_report_downloaded, key="next_round_save",
        )
        if go_col.button(f"{next_round_no}회차 시작하기", type="primary", width="stretch", key="next_round_go"):
            go_next_round()
            st.rerun()  # 창 안 버튼은 창만 다시 그리므로 화면 전체를 다시 그린다
        if not agreed:
            st.caption(":material/info: 안내를 확인하고 체크하면 저장하기 버튼이 켜져요. 저장하지 않고 시작해도 돼요.")
        elif state.get("report_downloaded"):
            st.caption(":material/check: 리포트를 저장했어요.")

    body()

def show_messages():
    for message in state.messages:
        with st.chat_message(message["role"], avatar=AVATARS[message["role"]]):
            st.markdown(message["content"])


# ── 형광펜 ─────────────────────────────────────────────────
# 색상 계열이 서로 겹치지 않는 밝은 바탕 4개. 글자는 모두 진한 색이라 잘 보인다.
HIGHLIGHT_COLORS = {
    "specific": "#FFE45C",   # 노랑 — 구체성
    "relevance": "#8CCBFF",  # 하늘 — 직무 연관
    "structure": "#9BE89B",  # 연두 — 구조
    "evidence": "#FFADD2",   # 분홍 — 근거 · 검증
}
HIGHLIGHT_TEXT = "#171719"  # 밝은 바탕 위 진한 글자


def ai_note(what: str = "AI가 쓴 의견"):
    """AI가 만든 내용 표시 (ui-ux-pro-max: AI Interaction · Disclaimer)."""
    st.caption(f":material/smart_toy: {what}이에요. 사실과 다를 수 있으니 직접 확인해 주세요.")


HIGHLIGHT_CSS = f"""<style>
.hl {{ overflow-wrap: anywhere; }}
.hl details {{ display: inline; }}
.hl summary {{ display: inline; cursor: pointer; list-style: none; }}
.hl summary::-webkit-details-marker {{ display: none; }}
.hl .mark {{ color: {HIGHLIGHT_TEXT}; padding: 1px 3px; border-radius: 4px; line-height: 2;
  box-decoration-break: clone; -webkit-box-decoration-break: clone; }}
.hl .chip {{ color: {HIGHLIGHT_TEXT}; font-size: 0.72em; font-weight: 600; padding: 0 4px;
  margin-left: 3px; border-radius: 3px; vertical-align: 1px; }}
.hl .detail {{ display: block; margin: 4px 0 8px; padding: 6px 10px; font-size: 0.9em;
  border-left: 3px solid #888; }}
</style>"""


def highlight_background(tags: list[str]) -> str:
    """기준 1개면 그 색, 여러 개면 색을 사선 줄무늬로 섞는다."""
    colors = [HIGHLIGHT_COLORS[t] for t in tags]
    if len(colors) == 1:
        return colors[0]
    stops = ", ".join(f"{c} {i * 6}px {(i + 1) * 6}px" for i, c in enumerate(colors))
    return f"repeating-linear-gradient(135deg, {stops})"


def chip(tag: str) -> str:
    return f'<span class="chip" style="background:{HIGHLIGHT_COLORS[tag]}">{coach.CRITERIA[tag]}</span>'


HIGHLIGHT_COLOR_NAMES = {"specific": "노랑", "relevance": "하늘", "structure": "연두", "evidence": "분홍"}
_legend_count = [0]  # 한 화면에 형광펜이 여러 개라 기준지표 칸마다 다른 key (실행마다 0부터)


def show_legend(question: dict):
    st.html(HIGHLIGHT_CSS + '<div class="hl">' + " ".join(chip(t) for t in HIGHLIGHT_COLORS)
            + " <small>· 줄무늬는 여러 기준 · 문장을 누르면 상세 보기 · 기준 판단은 AI가 했어요</small></div>")
    _legend_count[0] += 1
    with st.popover(":material/rule: 기준지표", type="tertiary", key=f"hl_rule_{_legend_count[0]}",
                    help="AI가 문장에 형광펜을 칠할 때 따른 기준이에요."):
        st.markdown("**형광펜 기준 판단 근거**")
        st.caption("미리 정해 둔 기준이에요. AI는 이 표와 아래 '보는 점' 으로 문장마다 기준을 0~4개 골라 칠해요.")
        rows = coach.highlight_criteria()
        if rows:
            st.table([{"색": HIGHLIGHT_COLOR_NAMES[r["key"]], "기준": r["name"], "이런 문장에 칠해요": r["rule"],
                       "채점": f"0~{coach.CRITERION_MAX}점"} for r in rows], hide_index=True)
        else:
            st.info("기준표를 읽지 못했어요. prompts.py 의 형광펜 지시문 [기준] 줄 모양을 확인해 주세요.")
        st.markdown(f"**이 질문에서 보는 점:** {question['point']}")
        st.caption("문장을 누르면 AI가 그 기준을 고른 이유 1문장을 볼 수 있어요. 판단은 AI가 했으니 직접 확인해 주세요.")


def show_highlighted(sentences: list[str], numbers: list[int], marks: dict):
    parts = []
    for sentence, no in zip(sentences, numbers):
        mark = marks.get(no, {"tags": [], "why": ""})
        text = html.escape(sentence)
        if mark["tags"]:
            names = " · ".join(coach.CRITERIA[t] for t in mark["tags"])
            summary = (f'<span class="mark" style="background:{highlight_background(mark["tags"])}">{text}</span>'
                       + "".join(chip(t) for t in mark["tags"]))
        else:
            names = "해당 기준 없음"
            summary = text
        detail = f"<b>{names}</b>" + (f" — {html.escape(mark['why'])}" if mark["why"] else "")
        parts.append(f'<details><summary>{summary}</summary><span class="detail">{detail}</span></details>')
    st.html(HIGHLIGHT_CSS + '<div class="hl">' + " ".join(parts) + "</div>")


def get_highlight(cache_key: str, blocks: list[dict]) -> dict | None:
    """형광펜 결과를 한 번만 만들고 저장해 둔다. blocks: [{question, point, sentences}]."""
    if cache_key not in state.highlights:
        user_input, numbers = coach.build_highlight_input(blocks)

        def store(raw):
            state.highlights[cache_key] = {"numbers": numbers, "marks": coach.summarize_highlight(raw)}

        if not call_ai("문장마다 기준을 표시하고 있어요...", coach.build_highlight(profile), user_input,
                       HIGHLIGHT_SCHEMA, "highlight", store):
            return None
    return state.highlights[cache_key]


ACTION_ICONS = {"추가": ":material/add:", "수정": ":material/edit:", "축약": ":material/content_cut:", "삭제": ":material/delete:"}
SPEAK_STEP_ICONS = {1: ":material/menu_book:", 2: ":material/visibility:", 3: ":material/visibility_off:"}


def show_strategy(place: str, cache_key: str, no: int, scores: dict, weak: str, answer: str, ev: dict):
    """20점 미만인 답에 '+N점 전략 가이드'. 더 받을 수 있는 점수는 코드가 계산하고, 전략 글은 AI가 쓴다.
    cache_key 로 한 번 만든 전략을 저장해 두고, 같은 답이면 평가 · 재도전 탭이 같이 쓴다."""
    gap = coach.strategy_gap(scores)
    if not gap:
        return
    st.markdown(f"**:material/trending_up: +{sum(gap.values())}점 전략 가이드**")
    st.caption(" · ".join(f"{coach.CRITERIA[key]} +{g}" for key, g in gap.items()))
    if cache_key in state.strategies:
        ai_note("점수는 앱이 계산했고, 전략 글은 AI가 쓴 의견")
    if cache_key not in state.strategies:
        # 같은 답의 버튼이 평가 · 재도전 탭에 함께 그려질 수 있어서 위치(place)를 key 에 넣는다.
        if st.button("전략 가이드 받기", key=f"strategy_{place}_{cache_key}"):
            question = state.questions[no - 1]

            def store(raw):
                state.strategies[cache_key] = coach.summarize_strategy(raw, scores)

            if call_ai(
                "점수를 올릴 전략을 찾고 있어요...",
                coach.build_strategy(profile, question, {"scores": scores, "weak": weak}, ev),
                answer or "(답 없음)", STRATEGY_SCHEMA, "strategy", store,
            ):
                st.rerun()
        return
    # 만든 뒤에는 카드를 접기 칸 안에 넣는다 (부르는 곳이 접기 칸 안이 아니어야 한다 — 접기 칸은 겹칠 수 없음)
    items = state.strategies[cache_key]
    with st.expander(f":material/tips_and_updates: 전략 가이드 카드 {len(items)}개 보기"):
        for item in items:
            with st.container(border=True):
                st.markdown(f"**{item['name']}** {item['score']}/{coach.CRITERION_MAX} · **+{item['gain']}점 여지**")
                for t in item["tips"]:
                    line = f"{ACTION_ICONS.get(t['action'], ':material/chevron_right:')} **{t['action']}** · {t['tip']}"
                    if t["target"]:
                        line += f"  \n  ↳ 내 답: \"{t['target']}\""
                    st.markdown(line)
                if not item["tips"]:
                    st.caption("이 기준에 대한 전략을 받지 못했어요.")


def show_perfect_hints(ev: dict):
    """만점일 때 힌트: 평가에 이미 있는 더 다듬을 점 · 다듬은 답 · 확인할 것 (고르는 건 coach.perfect_hints, AI 새 호출 없음)."""
    hints = coach.perfect_hints(ev)
    if not hints:
        st.info("이번 평가에는 더 다듬을 점이 따로 없어요. 이 답들을 그대로 외워 두세요.")
        return
    st.caption("만점이어도 실제 면접에서 한 번 더 다듬을 수 있는 점이에요.")
    ai_note("더 다듬을 점 · 다듬은 답 · 확인할 것은 AI가 평가 때 쓴 의견")
    for hint in hints:
        with st.container(border=True):
            st.markdown(f"**질문 {hint['no']}** · {coach.ANSWER_MAX}/{coach.ANSWER_MAX}점")
            st.caption(hint["question"])
            if hint["weak"]:
                st.markdown(f":material/lightbulb: **더 다듬는다면:** {hint['weak']}")
            if hint["rewrite"]:
                st.markdown("**힌트 답변**")
                st.markdown(f"> {hint['rewrite']}")
            for item in hint["check"]:
                st.markdown(f":material/fact_check: **면접 전 확인:** {item}")


def show_clues(ev: dict):
    """역전의 실마리: 가장 낮은 답 MAX_CLUES 개와 각 답의 가장 낮은 기준. 고르는 건 코드(coach.pick_clues).
    찾은 실마리는 state.clue_set 에 고정해 둔다 (재도전 뒤에도 같은 실마리에 '역전 성공! 전 → 후' 를 보여 주려고).
    실마리를 모두 재도전하면 '역전의 실마리 찾기' 로 최신 점수에서 다시 찾는다."""
    retries, retry_counts = state.get("retries", {}), state.get("retry_counts", {})
    if "clue_set" not in state:
        state.clue_set = coach.pick_clues(ev, retries=retries, retry_counts=retry_counts)
    clues = state.clue_set
    # 만점은 아니지만 재도전을 모두 써서 실마리로 고르지 않은 답 (최신 점수 기준)
    used_up = [a["no"] for a in coach.latest_answers(ev, retries)
               if a["score"] < coach.ANSWER_MAX and retry_counts.get(a["no"], 0) >= coach.MAX_RETRIES]
    if not clues and used_up:
        st.info(f":material/flag: 남은 질문 {', '.join(map(str, used_up))}번은 재도전을 {coach.MAX_RETRIES}번 모두 했어요. "
                "리포트를 받아 다음 회차에서 이어서 연습하거나, 암기 탭에서 말하기 연습으로 다듬어 보세요.")
        return
    if not clues:
        st.success(":material/celebration: 모든 답이 20점 만점이에요.")
        if st.button(":material/lightbulb: 힌트 확인하기", key="perfect_hints"):
            state.perfect_hints_open = not state.get("perfect_hints_open")
            st.rerun()
        if state.get("perfect_hints_open"):
            show_perfect_hints(ev)
        return
    progress = coach.clue_progress(clues, ev, retries, retry_counts)
    clue_round = state.get("clue_round", 1)
    done_count = sum(r["retried"] for r in progress["rows"])
    st.subheader(":material/search: 역전의 실마리를 찾았습니다.")
    st.badge(f"실마리 {clue_round}회차 · {len(clues)}개 중 {done_count}개 재도전 완료",
             icon=":material/check_circle:" if progress["done"] else ":material/update:",
             color="green" if progress["done"] else "blue")
    if state.pop("clue_updated", False):
        st.success(f":material/update: 실마리가 **{clue_round}회차**로 업데이트됐어요. 재도전 점수를 넣은 최신 점수에서 다시 찾았어요.")
    st.caption(f"점수가 가장 낮은 답 {len(clues)}개예요. 여기부터 고치면 점수가 가장 많이 올라요."
               + (f" 재도전을 {coach.MAX_RETRIES}번 모두 한 질문({', '.join(map(str, used_up))}번)은 빼고 골랐어요."
                  if used_up and clue_round > 1 else ""))
    for clue, row in zip(clues, progress["rows"]):
        with st.container(border=True):
            st.markdown(
                f"**질문 {clue['no']}** · {clue['score']}/{coach.ANSWER_MAX}점 · "
                f"가장 약한 기준 **{clue['name']} {clue['criterion_score']}/{coach.CRITERION_MAX}**"
            )
            st.caption(clue["question"])
            if row["up"]:
                st.success(f":material/trending_up: **역전 성공!** {row['before']} → {row['after']}점 (+{row['diff']})")
            used = retry_counts.get(clue["no"], 0)  # 재도전 횟수 (MAX_RETRIES 까지)
            left = used < coach.MAX_RETRIES
            if row["retried"] and not row["up"]:
                more = "한 번 더 도전해 볼 수 있어요." if left else f"재도전을 {coach.MAX_RETRIES}번 모두 했어요."
                st.info(f"재도전 완료 · {row['before']} → {row['after']}점 ({row['diff']:+d}). {more}")
            elif not row["up"]:
                st.markdown(f"**가장 약한 점:** {clue['weak']}")
                st.caption(f"'역전의 기회 잡기' 를 누르면 아래에서 질문 {clue['no']} 의 형광펜 · 전략 가이드를 보며 다시 답할 수 있어요.")
            if not row["up"]:
                # 남은 기회를 버튼에 보여 준다. 0이면 꺼진 버튼 (사용자 요청 — CLAUDE.md 'disabled 금지' 의 예외, 이유는 버튼 글자로)
                remaining = coach.MAX_RETRIES - used
                name = "한 번 더 도전하기" if row["retried"] else "역전의 기회 잡기"
                label = f":material/replay: {name} · 남은 기회 {remaining}/{coach.MAX_RETRIES}"
                if st.button(label, key=f"clue_retry_{clue['no']}", disabled=not left,
                             type="secondary" if row["retried"] or not left else "primary",
                             help=None if left else "이 질문은 재도전 기회를 모두 썼어요. 다음 회차 면접에서 이어서 연습해 보세요."):
                    state.go_retry_no = clue["no"]
                    state.go_tab = RETRY_TAB
                    st.rerun()
    # 실마리를 모두 재도전해야 다음 실마리를 찾을 수 있다 (사용자 요청으로 disabled 예외: 못 누르는 이유를 버튼 글자로 보여 줌)
    if progress["done"]:
        if st.button(":material/search: 역전의 실마리 찾기", key="clue_find", type="primary",
                     help="최신 점수(재도전 점수 포함)에서 가장 낮은 답을 다시 찾아요."):
            state.clue_set = coach.pick_clues(ev, retries=retries, retry_counts=retry_counts)
            state.clue_round = clue_round + 1
            state.clue_updated = True  # 다음 화면에서 한 번만 '업데이트됐어요' 를 알린다
            st.rerun()
    else:
        st.button("재도전을 진행해보세요.", key="clue_find", disabled=True,
                  help=f"위 실마리 {len(clues)}개를 모두 재도전하면 다음 실마리를 찾을 수 있어요.")


PANEL_ICONS = {  # 위원 캐릭터 태그 아이콘 (Material 이름은 streamlit/material_icon_names.py 에서 확인)
    "실무 전문가": ":material/construction:",
    "논리 분석가": ":material/psychology:",
    "커뮤니케이션 전문가": ":material/forum:",
    "채용 담당자": ":material/person_search:",
}


def show_panel_cards(panel: list[dict]):
    """위원 캐릭터 태그를 하나 고르면 그 위원의 의견을 카드 하나로 자세히 보여 준다."""
    by_role = {m["role"]: m for m in panel}
    role = st.pills(
        "위원별 의견", list(by_role), key="panel_pick", default=next(iter(by_role)), required=True,
        format_func=lambda r: f"{PANEL_ICONS.get(r, ':material/person:')} {r} · {by_role[r]['score']}",
        help="태그를 눌러 위원 한 명씩 자세히 볼 수 있어요.",
    )
    m = by_role[role]
    with st.container(border=True):
        name_col, score_col = st.columns([3, 1], vertical_alignment="center")
        name_col.markdown(f"#### {PANEL_ICONS.get(role, ':material/person:')} {role}")
        score_col.metric("점수", f"{m['score']}/{coach.PANEL_MAX}", label_visibility="collapsed")
        st.progress(m["score"] / coach.PANEL_MAX)
        st.caption(f"평가 기준 · {PANEL_CRITERIA[role]}")
        st.markdown(f":green[:material/thumb_up:] **좋은 점**  \n{m['good'] or '(의견 없음)'}")
        st.markdown(f":red[:material/report:] **뽑지 말아야 할 이유**  \n{m['against'] or '(의견 없음)'}")


def show_example(question: dict, score: int):
    """만점 예시 답안: 질문 은행에 미리 적어 둔 가상 지원자의 답 (AI 호출 없음 · 내 경험과 무관).
    내 답을 고칠 방향만 참고하도록, 문장을 그대로 외우지 말라고 안내한다."""
    example = question.get("example", "")
    if score >= coach.ANSWER_MAX or not example:
        return
    st.markdown("**만점 예시 답안** · :material/person_book: 가상 지원자")
    st.info("  \n".join(coach.split_sentences(example)))
    st.caption("질문 은행에 미리 적어 둔 예시라 내 경험 · 숫자와 무관해요. "
               "결론 → 상황 · 행동(숫자) → 확인 방법 → 직무 연결 흐름만 참고해서 내 경험으로 고쳐 보세요.")


def show_evaluation(ev: dict):
    # 역전의 실마리 · 형광펜 · 전략 가이드 · 다음 연습에서 고칠 것은 재도전 탭에서 본다 (기능 중복을 줄임)
    totals = coach.total_scores(ev, state.get("retries", {}))
    st.subheader(f":material/gavel: {coach.eval_title(totals, ev['panel_average'])}")
    st.metric("위원 평균", f"{ev['panel_average']:.1f}/{coach.PANEL_MAX}")
    ai_note("점수 합계 · 평균은 앱이 계산했고, 위원 의견 · 약한 점 · 고친 답은 AI가 쓴 의견")
    show_panel_cards(ev["panel"])
    conflict_col, agree_col = st.columns(2)
    with conflict_col.container(border=True, height="stretch"):
        st.markdown(":orange[:material/call_split:] **판단이 갈린 곳**")
        st.write(ev["conflict"] or "(의견 없음)")
    with agree_col.container(border=True, height="stretch"):
        st.markdown(":green[:material/handshake:] **모두 같은 판단**")
        st.write(ev["agree"] or "(의견 없음)")
    with st.expander(":material/table_view: 전체 요약 · 위원 4명 한눈에 보기"):
        # st.table 은 긴 글을 칸 안에서 줄바꿈해서 가로 스크롤이 생기지 않는다 (st.dataframe 은 줄바꿈 옵션이 없음).
        st.table(
            [
                {
                    "위원": m["role"],  # 표 칸은 아이콘을 그리지 못해서 글자만
                    "평가 기준": PANEL_CRITERIA[m["role"]],
                    "뽑지 말아야 할 이유": m["against"],
                    "좋은 점": m["good"],
                    "점수": m["score"],
                }
                for m in ev["panel"]
            ],
            hide_index=True,
        )
    with st.expander(":material/menu_book: 평가 기준과 근거 보기"):
        try:
            st.markdown(coach.load_panel_rationale())
        except OSError:
            st.error("평가 기준 근거 문서(data/평가기준_근거.md)를 읽지 못했어요.")

    if state.previous:
        prev = coach.compare_previous(state.previous, ev, state.questions, state.retries)
        st.subheader(f"지난 면접({prev['round']}회차 · {prev['date']})과 비교")
        if prev["criteria_changed"]:
            st.warning("지난 회차와 평가 기준이 달라서 점수 비교가 정확하지 않을 수 있어요.")
        panel_col, total_col = st.columns(2)
        panel_col.metric("위원 평균", f"{prev['panel_after']:.1f}/{coach.PANEL_MAX}", delta=round(prev["panel_diff"], 1))
        if prev["total_before"] is not None:
            total_col.metric(
                "최신 종합", f"{prev['total_after']}/{coach.TOTAL_MAX}", delta=prev["total_after"] - prev["total_before"]
            )
        if prev["rows"]:
            st.table(prev["rows"], hide_index=True)
        else:
            st.caption("지난 면접과 같은 질문이 없어서 질문별 비교는 없어요.")

    st.subheader("답변별 점수")
    # 질문마다 나온 회차 태그 (지난 회차는 회색, 이번 회차는 초록) · 지난 회차에만 나온 질문은 '전체 회차 보기' 에서
    history = coach.question_history(past_reports())
    current_round = int(state.round)
    current_texts = {q["question"] for q in state.questions}
    past_only = {t: rows for t, rows in history.items() if t not in current_texts}
    show_all = False
    if past_only:
        options = [f"{current_round}회차만 보기", "전체 회차 보기"]
        if state.get("eval_rounds") not in options:
            state.eval_rounds = options[0]
        show_all = st.segmented_control(
            "보기", options, key="eval_rounds", required=True, label_visibility="collapsed",
            help="전체 회차 보기: 이번 회차에 나오지 않은 지난 회차 질문과 그때 답도 함께 보여요 (점수는 이번 회차 종합에 들어가지 않아요).",
        ) == options[1]

    def tags(text: str, with_current: bool) -> str:
        rounds = {row["round"] for row in history.get(text, [])} - {current_round}
        rounds = sorted(rounds | ({current_round} if with_current else set()))
        return " ".join(f":green-badge[{r}회차]" if r == current_round else f":gray-badge[{r}회차]" for r in rounds)

    for a in ev["answers"]:
        label = f"질문 {a['no']} · {a['score']}/{coach.ANSWER_MAX}점 {tags(a['question'], True)}"
        with st.expander(label, expanded=a["needs_rewrite"]):
            st.caption(a["question"])
            st.write(" · ".join(f"{name} {a['scores'][key]}" for key, name in coach.CRITERIA.items()))
            st.markdown("**내 답**")
            show_answer(coach.answer_text(state.messages, a["no"] - 1), state.questions[a["no"] - 1], f"eval:{a['no']}", False)
            st.markdown(f"**가장 약한 점:** {a['weak']}")
            show_example(state.questions[a["no"] - 1], a["score"])
            if a["score"] < coach.ANSWER_MAX:
                if st.button(":material/replay: AI 코칭을 반영해 재도전으로 역전의 기회 잡기", key=f"eval_retry_{a['no']}",
                             type="primary", help="재도전 탭에서 형광펜 · 전략 가이드를 보며 이 질문에 다시 답해요."):
                    state.go_retry_no = a["no"]
                    state.go_tab = RETRY_TAB
                    st.rerun()

    if not show_all:
        return
    # 지난 회차에만 나온 질문: 그 회차의 최신 답 · 점수 (읽기만 · 이번 회차 종합 점수에는 들어가지 않는다)
    st.markdown("**지난 회차에만 나온 질문**")
    st.caption("지난 회차 기록이에요. 점수는 그 회차 최신 점수이고, 이번 회차 종합 점수에는 들어가지 않아요. "
               ":material/psychology: 암기 탭의 '다른 질문' 에서 연습할 수 있어요.")
    for text, rows in sorted(past_only.items(), key=lambda kv: -kv[1][-1]["round"]):
        last = rows[-1]
        score = f"{last['score']}/{coach.ANSWER_MAX}점" if isinstance(last["score"], int) else "점수 없음"
        with st.expander(f"지난 {last['round']}회차 질문 · {score} {tags(text, False)}"):
            st.caption(text)
            st.markdown(f"**{last['round']}회차 내 답**")
            st.markdown("  \n".join(coach.split_sentences(last["answer"])) or "(답 없음)")


def highlight_toggle(key: str) -> bool:
    """답 하나에만 형광펜을 켜고 끄는 스위치."""
    return st.toggle(":material/ink_highlighter: 형광펜 모드", key=key, help="이 답의 문장마다 어떤 기준과 연결되는지 색으로 보여 줘요.")


def show_answer(text: str, question: dict, cache_key: str, highlight_on: bool):
    """답 하나를 보여 준다. highlight_on 이면 형광펜으로.
    cache_key 가 같으면 (예: 평가 탭과 재도전 탭의 같은 답) 한 번 만든 형광펜을 같이 쓴다."""
    sentences = coach.split_sentences(text)
    block = {"question": question["question"], "point": question["point"], "sentences": sentences}
    highlight = get_highlight(cache_key, [block]) if highlight_on and sentences else None
    if highlight:
        show_legend(question)
        show_highlighted(sentences, highlight["numbers"][0], highlight["marks"])
    else:
        st.markdown("  \n".join(sentences) or "(답 없음)")  # 한 문장씩 줄을 바꿔 읽기 쉽게


def record_retry(no: int, attempt: dict, original_score: int):
    """재도전 하나를 기록에 더하고, 반영할 재도전(최고 점수)을 다시 고른다 (고르는 건 coach.reflected_retry).
    재도전 탭 · 암기 탭의 재도전 검토가 같이 쓴다."""
    history = state.setdefault("retry_history", {}).setdefault(no, [])
    history.append(attempt)
    best = coach.reflected_retry(original_score, history)
    if best:
        state.retries[no] = best
    else:
        state.retries.pop(no, None)  # 모두 처음 점수 이하 → 처음 점수 반영


def show_failed_retries(no: int, original_score: int):
    """반영되지 않은 재도전을 접기 칸으로 (최고 점수만 종합 점수에 들어간다)."""
    fails = coach.failed_retries(original_score, state.get("retry_history", {}).get(no, []))
    if not fails:
        return
    with st.expander(f":material/history: 반영 안 된 재도전 {len(fails)}번 보기"):
        st.caption("종합 점수에는 가장 높은 점수만 들어가요. 아래는 반영되지 않은 재도전 기록이에요.")
        for n, r in fails:
            with st.container(border=True):
                st.markdown(f"**{n}번째 재도전** · {original_score} → {r['score']}점 ({r['score'] - original_score:+d})")
                st.markdown("\n".join(f"> {line}" for line in r["answer"].splitlines()))
                st.caption(f"AI 의견 · 약한 점: {r['weak']}")


COACH_TREND_ICONS = {"up": ":green[:material/trending_up:]", "down": ":red[:material/trending_down:]",
                     "same": ":gray[:material/trending_flat:]"}


def coach_card_height(rows: list[dict]) -> int:
    """위원 코치 카드 높이(px): 글 길이로 줄 수를 넉넉히 어림해 가장 긴 카드에 맞춘다.
    (Streamlit 은 서버에서 글 높이를 잴 수 없어서 어림한다. 넉넉하면 아래 여백만 조금 남고, 모자라면 카드 안에 스크롤이 생긴다.)
    두 칸 너비에서 본문은 한 줄 약 17자 · 24px, 작은 글씨는 약 20자 · 21px 로 본다."""
    def lines(text: str, per_line: int) -> int:
        return max(1, math.ceil(len(text) / per_line))

    tallest = max(24 + 21 * lines(r["changes"], 20) + 24 * lines(r["message"], 17) for r in rows)
    return 32 + 2 * 16 + tallest + 8  # 위아래 여백 + 줄 사이 간격 + 여유


def show_panel_coaching(before: dict, after: dict):
    """다시 채점 결과 맨 끝: 위원 4명의 코치 피드백 (점수 변화로 coach.panel_coaching 이 고른 고정 문장)."""
    st.markdown("**:material/groups: 위원 코치 피드백**")
    st.caption("기준별 점수 변화로 앱이 고른 코칭이에요. AI가 답을 다시 읽고 쓴 의견은 아니에요.")
    rows = coach.panel_coaching(before, after)
    height = coach_card_height(rows)  # 4장 모두 가장 긴 카드 높이로
    cols = st.columns(2)
    for i, row in enumerate(rows):
        with cols[i % 2].container(border=True, height=height):
            st.markdown(f"{PANEL_ICONS.get(row['role'], ':material/person:')} **{row['role']}**")
            st.caption(row["changes"])
            st.markdown(f"{COACH_TREND_ICONS[row['trend']]} {row['message']}")


def show_retry_result(no: int, ev: dict, index: int, place: str, celebrate: bool = False):
    """재도전 결과 하나 (전 → 후). 재도전 탭 · 암기 탭의 재도전 검토가 같은 구조로 같이 쓴다.
    index: retry_history 안의 몇 번째 재도전인지. place: 두 탭이 함께 그려져도 칸 key 가 겹치지 않게.
    celebrate: 점수가 오르면 '역전 성공!' 을 여기서 띄운다 (재도전 탭은 실마리 카드에만 띄우므로 False)."""
    last = ev["answers"][no - 1]
    question = state.questions[no - 1]
    history = state.get("retry_history", {}).get(no, [])
    result = history[index]
    reflected = state.retries.get(no)  # 종합 점수에는 최고 점수 (coach.reflected_retry)
    diff = coach.compare(last["scores"], result["scores"])
    if diff["diff"] > 0 and celebrate:
        st.success(f":material/celebration: 역전 성공! {diff['before']} → {diff['after']}점으로 {diff['diff']}점 올랐어요.")
    elif diff["diff"] == 0:
        st.info(f"점수가 {diff['after']}점 그대로예요. 아래 약한 점과 전략 가이드를 보고 한 부분만 바꿔 보세요.")
    elif diff["diff"] < 0:  # 진짜로 내려갔을 때만
        st.warning(
            f"{diff['before']} → {diff['after']}점으로 {-diff['diff']}점 내려갔어요. "
            "아래 기준별 변화와 약한 점을 보고 다시 도전해 보세요."
        )
    st.metric("후 점수", f"{diff['after']}/{coach.ANSWER_MAX}", delta=diff["diff"])
    if reflected is result:
        st.caption(":material/check: 이 점수가 종합 점수에 반영돼요 (최고 점수 반영).")
    elif reflected:
        n = history.index(reflected) + 1
        st.caption(f":material/info: 종합 점수에는 {n}번째 재도전의 최고 점수 {reflected['score']}점이 반영돼 있어요.")
    else:
        st.caption(f":material/info: 처음 점수보다 높지 않아서, 종합 점수에는 처음 점수 {last['score']}점이 그대로 반영돼요.")
    # 기준별 전/후 막대 그래프 (숫자는 모두 coach.compare() 가 계산한 값)
    chart = pd.DataFrame(
        {"전": [r["전"] for r in diff["rows"]], "후": [r["후"] for r in diff["rows"]]},
        index=[r["기준"] for r in diff["rows"]],
    )
    st.bar_chart(chart, stack=False, y_label="점수 (0~5)", color=["#C2C4C8", "#4263D6"], height=240)
    st.table(diff["rows"], hide_index=True)
    st.markdown(f"**이번 답의 약한 점:** {result['weak']}")
    ai_note("점수 차이는 앱이 계산했고, 약한 점은 AI가 쓴 의견")
    retry_key = f"retry:{no}:{result['answer']}"  # 형광펜 · 전략은 두 탭이 같은 답이면 같이 쓴다
    with st.expander(":material/edit_note: 다시 쓴 답 보기"):
        show_answer(result["answer"], question, retry_key, highlight_toggle(f"hl_{place}_after_{no}"))
    show_strategy(f"{place}_after", retry_key, no, result["scores"], result["weak"], result["answer"], ev)
    show_panel_coaching(last["scores"], result["scores"])


def show_retry(ev: dict):
    if state.pop("scroll_top", False):
        scroll_to_top()
    show_clues(ev)  # 역전의 실마리는 재도전 탭 맨 위 (평가 탭에서 옮김)
    # '다음 연습에서 고칠 것' 은 처음 평가 때 한 번 만든 글이라 재도전 뒤에 바뀌지 않는다 → 화면에서는 뺀다 (리포트에만)
    st.divider()
    # 고르는 칸은 지금 점수(재도전 최고 점수 반영) 낮은 순 · 비교 기준(last)은 면접 때 처음 답
    original = {a["no"]: a for a in ev["answers"]}
    counts = state.get("retry_counts", {})

    def label(a: dict) -> str:
        first = original[a["no"]]["score"]
        score = f"{first} → {a['score']}" if a["score"] != first else f"{first}"
        return (f"질문 {a['no']} · {score}/{coach.ANSWER_MAX}점 · 재도전 {counts.get(a['no'], 0)}/{coach.MAX_RETRIES} · "
                f"{a['question']}")

    labels = {a["no"]: label(a) for a in coach.retry_order(coach.latest_answers(ev, state.get("retries", {})))}
    no = st.selectbox("다시 답할 질문 (지금 점수 낮은 순)", list(labels), format_func=labels.get, key="retry_no")
    last = original[no]
    question = state.questions[no - 1]
    before = coach.answer_text(state.messages, no - 1)

    history = state.get("retry_history", {}).get(no, [])
    result = history[-1] if history else None   # 화면에는 방금 한 재도전
    comeback = bool(result) and result["score"] > last["score"]  # 역전 성공이면 결과를 맨 위, 역전 전 기록은 맨 아래로

    def show_past():
        st.metric("지난 점수", f"{last['score']}/{coach.ANSWER_MAX}")
        st.markdown(f"**지난 약한 점:** {last['weak']}")
        with st.expander("지난 답 보기"):
            show_answer(before, question, f"eval:{no}", highlight_toggle(f"hl_retry_before_{no}"))
        # 다시 쓰기 전에 참고하도록 지난 답의 전략 가이드 (평가 탭과 같은 결과를 같이 쓴다)
        show_strategy("retry_before", f"eval:{no}", no, last["scores"], last["weak"], before, ev)

    def show_answer_box():
        st.markdown("**이제, 당신의 차례입니다.**")
        new_answer = st.text_area(
            "다시 답하기", height=180, key=f"retry_answer_{no}", max_chars=coach.MAX_ANSWER_CHARS
        )
        used = state.retry_counts.get(no, 0)
        st.caption(f"이 질문 재도전 {used}/{coach.MAX_RETRIES}번")
        if st.button("다시 채점", type="primary"):
            if not new_answer.strip():
                st.info("다시 쓴 답을 적은 뒤 눌러 주세요.")
            elif used >= coach.MAX_RETRIES:
                st.info(
                    f"이 질문은 재도전을 {coach.MAX_RETRIES}번 모두 했어요. 다른 질문에 도전하거나, "
                    "리포트를 받아 다음 회차에서 이어서 연습해 보세요."
                )
            else:
                def store(raw):
                    attempt = {"answer": new_answer.strip(), **coach.summarize_retry(raw)}
                    record_retry(no, attempt, last["score"])
                    state.retry_counts[no] = used + 1
                    if attempt["score"] > last["score"]:
                        state.scroll_top = True  # 역전 성공: 결과가 맨 위에 오므로 페이지 맨 위로

                if call_ai(
                    "다시 쓴 답을 채점하고 있어요...",
                    coach.build_retry(profile, question, before, last["weak"]),
                    new_answer.strip(), RETRY_SCHEMA, "retry", store,
                ):
                    st.rerun()

    def show_result():
        # 점수가 오르면 '역전 성공!' 은 맨 위 역전의 실마리 카드에만 띄운다 (여기서는 후 점수 +n 으로만 보여 줌)
        show_retry_result(no, ev, len(history) - 1, "retry")

    if comeback:
        show_result()
        st.divider()
        show_answer_box()
        st.divider()
        st.markdown("**:material/history: 역전 전 기록**")
        st.caption("역전하기 전의 점수와 답이에요. 지금 점수는 위의 재도전 결과예요.")
        show_past()
    else:
        show_past()
        show_answer_box()
        if result:
            show_result()
    show_failed_retries(no, last["score"])


def show_question_cards(pairs: list[tuple[str, str]]):
    for angle, question in pairs:
        with st.container(border=True):
            st.caption(f"{angle} 관점")
            st.markdown(question)
    if pairs:
        ai_note("AI가 만든 질문")


def current_precheck(items: list[dict]) -> dict:
    """지금 화면의 체크 · 메모 상태 (리포트 · 이어 하기용)."""
    n = range(len(items))
    return coach.precheck_state(
        items,
        [bool(state.get(f"pre_found_{i}")) for i in n],
        [bool(state.get(f"pre_missing_{i}")) for i in n],
        [str(state.get(f"pre_memo_{i}", "")) for i in n],
    )


def show_precheck():
    st.subheader(":material/search: 사전 정보 직접 탐색")
    st.write(
        "궁금하지만 면접 질문으로는 어울리지 않을 수 있는 정보예요. 면접 전에 스스로 찾아 채워 보세요. "
        "찾아봐도 없으면 **언제 확인하면 되는지** 알려 드려요."
    )
    try:
        items = coach.load_precheck()
    except (OSError, KeyError, ValueError):
        st.error("사전 탐색 체크리스트(data/사전탐색_체크리스트.csv)를 읽지 못했어요.")
        return

    found = [bool(state.get(f"pre_found_{i}")) for i in range(len(items))]
    missing = [bool(state.get(f"pre_missing_{i}")) for i in range(len(items))]
    summary = coach.precheck_summary(items, found, missing)
    st.progress(summary["found"] / summary["total"], text=f"찾음 {summary['found']}/{summary['total']} · 못 찾음 {summary['missing']}")

    groups = list(dict.fromkeys(item["group"] for item in items))
    for group in groups:
        with st.expander(group):
            for i, item in enumerate(items):
                if item["group"] != group:
                    continue
                with st.container(border=True):
                    st.checkbox(f":material/check_circle: **{item['item']}**", key=f"pre_found_{i}")
                    st.caption(f"찾는 곳: {item['where']}")
                    st.text_input(
                        "찾은 내용 메모",
                        key=f"pre_memo_{i}",
                        placeholder="예: 2025년 시리즈 B 투자",
                        label_visibility="collapsed",
                        max_chars=coach.MAX_MEMO_CHARS,
                    )
                    if st.checkbox(":material/help: 찾아봐도 없어요", key=f"pre_missing_{i}") and not state.get(f"pre_found_{i}"):
                        st.info(coach.PRECHECK_TIMING[item["timing"]])

    if summary["missing"]:
        st.markdown("**못 찾은 정보는 이렇게 챙기세요**")
        for timing, names in summary["later"].items():
            if names:
                st.markdown(f"- {coach.PRECHECK_LATER_LABEL[timing]}: " + " · ".join(names))
    st.caption("체크와 메모는 면접리포트.md 에 들어가고, 다음 회차에 리포트를 올리면 이어져요.")


def show_last_question():
    st.subheader("추천 질문")
    st.write("면접 마지막의 \"마지막으로 할 질문 있나요?\" 에 할 질문을 회사 · 직무 · 성장 관점으로 추천해 드려요.")
    if st.button("마지막 질문 생성하기", type="primary"):
        if state.last_suggest:
            st.info("추천 질문을 이미 만들었어요. 아래에서 확인해 주세요.")  # 같은 추천을 다시 부르지 않는다
        else:
            def store(raw):
                state.last_suggest = coach.summarize_last_suggest(raw)

            if call_ai("질문을 만들고 있어요...", coach.build_last_suggest(profile), LAST_SUGGEST_INPUT,
                       LAST_SUGGEST_SCHEMA, "last_suggest", store):
                st.rerun()
    if state.last_suggest:
        show_question_cards(state.last_suggest)

    st.divider()
    st.subheader("내 질문 다듬기")
    st.write("직접 쓴 질문을 회사 · 직무 · 성장 관점으로 다듬어 드려요.")
    my_question = st.text_area(
        "면접관에게 할 내 질문", height=100, key="last_question_input", max_chars=coach.MAX_LAST_QUESTION_CHARS
    )
    if st.button("질문 다듬기"):
        instructions = coach.build_last_question(profile)
        if not my_question.strip():
            st.info("면접관에게 할 질문을 적은 뒤 눌러 주세요.")
        elif not coach.is_prompt_ready(instructions):
            st.error("마지막 질문 프롬프트에 빈칸(___)이 있어요. prompts.py 의 LAST_QUESTION 글자 수를 채워 주세요.")
        else:
            def store(raw):
                state.last_question = coach.summarize_last_question(raw)

            if call_ai("질문을 다듬고 있어요...", instructions, my_question.strip(),
                       LAST_QUESTION_SCHEMA, "last_question", store):
                st.rerun()

    result = state.last_question
    if result:
        show_question_cards(result["questions"])
        if result["why"]:
            st.markdown(f"**원래 질문에서 빠진 것:** {result['why']}")


def user_now() -> datetime:
    """사용자 브라우저 시간대의 지금 시각. 배포 서버 시계는 UTC 라서 그대로 쓰지 않는다."""
    try:
        tz = ZoneInfo(st.context.timezone or DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo(DEFAULT_TIMEZONE)
    return datetime.now(tz)


def show_report_checklist():
    """단계 체크리스트: 탭 7개 순서 그대로, 하위 항목은 들여 써서 (표시만 · 고르는 건 coach.report_checklist).
    위쪽 진행 막대와 같은 목록이라 'n단계 중 n단계 완료' 숫자가 늘 같다."""
    rows = checklist_rows()

    def icon(done: bool) -> str:
        return ":green[:material/check_box:]" if done else ":gray[:material/check_box_outline_blank:]"

    with st.container(border=True):
        st.markdown(f"**:material/checklist: 단계 체크리스트** · {coach.checklist_summary(rows)}")
        st.caption("앱이 지금 기록으로 자동 표시해요. 탭 번호와 같은 순서이고, 마지막이 이 리포트예요. 하위 항목은 그 단계 안에서 할 수 있는 일이에요.")
        for r in rows:
            detail = f" :gray[({r['detail']})]" if r["detail"] else ""
            tag = " :gray[· 선택]" if r["optional"] else ""
            number = f"{r['step']}. " if r["step"] else ""  # 리포트는 탭이 아니라 번호 없음
            lines = [f"{icon(r['done'])} **{number}{r['item']}**{detail}{tag}"]
            lines += [
                f"{'&nbsp;' * 7}{icon(s['done'])} {s['item']}" + (f" :gray[({s['detail']})]" if s["detail"] else "")
                for s in r["sub"]
            ]
            st.markdown("  \n".join(lines))


def show_report(ev: dict):
    """리포트 창: 개인정보 안내 · 확인 체크 · 다운로드 · 마지막 업데이트를 맨 위에, 그 아래 단계 체크리스트 · 미리보기."""
    today = user_now().date()  # 파일 이름 · 리포트 날짜 모두 사용자 시간대 기준

    # 리포트 내용이 바뀐 때만 '마지막 업데이트' 시각을 새로 찍는다 (가장 최신 시각 하나만 남긴다).
    content = build_current_report(ev)
    if state.get("report_content") != content:
        state.report_content = content
        state.report_updated = user_now().strftime("%Y-%m-%d %H:%M")
    report = build_current_report(ev, state.report_updated)

    file_name = coach.report_file_name(profile["company"], profile["job"], state.round, today)
    st.warning(
        ":material/lock: 리포트에는 이름 · 회사 · 내 경험 원문 · 면접 대화 · 답변 · 체크리스트 메모가 들어가요. "
        "다른 사람과 공유할 때 주의해 주세요."
    )
    # 위 안내를 확인했다고 체크해야 다운로드할 수 있다 (사용자 요청 — CLAUDE.md '버튼을 disabled 로 막지 말 것' 의 예외)
    agreed = st.checkbox("위 안내를 확인했어요. 개인정보가 들어간 파일이라는 걸 알고 내려받을게요.", key="report_agree")
    button_col, time_col = st.columns([3, 2], vertical_alignment="center")
    button_col.download_button(
        f"{file_name} 다운로드",
        data=report,
        file_name=file_name,
        mime="text/markdown",
        type="primary",
        disabled=not agreed,
        on_click=mark_report_downloaded,  # 받으면 마지막 단계 완료 → 설문 안내
    )
    time_col.caption(f":material/schedule: 마지막 업데이트: **{state.report_updated}**")
    if not agreed:
        # 비활성 버튼이 왜 꺼져 있는지 알려 준다 (ui-ux-pro-max: Interaction · Disabled States)
        st.caption(":material/info: 위 안내를 확인하고 체크하면 다운로드 버튼이 켜져요.")
    show_report_checklist()
    st.caption(
        "오른쪽 위 복사 아이콘으로 내용을 복사할 수 있어요. 점수는 모두 앱이 계산한 값이고, "
        "'AI 의견' 표시가 붙은 글은 AI가 쓴 거예요. 마지막 질문을 만들어 두면 리포트에 같이 들어가요. "
        "다음 면접 시작 화면에서 이 파일을 올리면 이어서 할 수 있어요 (맨 끝 주석은 이어 하기용 데이터예요)."
    )
    st.code(report, language="markdown", wrap_lines=True)  # 긴 줄은 자동 줄바꿈 (가로 스크롤 없음)


# ── 최종 판결: 문자 → 이메일 연출. 판정은 coach.verdict(), 글은 모두 고정 문구 (AI 호출 없음) ──
VERDICT_CSS = """<style>
.vd { display: grid; gap: 14px; width: 100%; margin: 4px 0; overflow-wrap: anywhere; }
.vd * { box-sizing: border-box; }
.vd-phone { background: #171719; border-radius: 28px; padding: 18px 18px 22px;
  width: 100%; margin: 0; border: 4px solid #2E2F33; animation: vd-in .3s ease-out both; }
.vd-notch { width: 80px; height: 6px; border-radius: 3px; background: #2E2F33; margin: 0 auto 10px; }
.vd-contact { text-align: center; color: #F7F7F8; font-size: .875rem; font-weight: 600;
  border-bottom: 1px solid #2E2F33; padding-bottom: 8px; }
.vd-contact span { display: block; color: #AEB0B6; font-size: .75rem; font-weight: 400; }
/* 문자 대화: 아래에서부터 쌓인다. 새 문자가 아래에 자라면 앞 문자가 위로 밀려 올라간다 */
.vd-thread { display: flex; flex-direction: column; justify-content: flex-end; min-height: 190px; padding-top: 10px; }
.vd-sms { background: #2E2F33; color: #F7F7F8; border-radius: 14px 14px 14px 4px; padding: 10px 13px;
  font-size: .92em; line-height: 1.5; max-width: 75%; width: fit-content; overflow: hidden; }
.vd-time { color: #878A93; font-size: .75rem; margin: 3px 0 0 4px; }
.vd-m1 { animation: vd-pop .2s ease-out .5s both; }
.vd-m2 { overflow: hidden; animation: vd-grow .3s ease-out 1.9s both; }
/* 결과 메일: 메일 앱 한 통처럼 (머리글 · 제목 · 결과 카드 · 점수 3칸 · 서명 · 안내 주석) */
.vd-mail { background: #FFFFFF; color: #171719; border: 1px solid #E1E2E4; border-radius: 16px; overflow: hidden;
  line-height: 1.6; word-break: keep-all; box-shadow: 0 1px 2px rgba(23, 23, 25, .04); animation: vd-in .3s ease-out 3s both; }
.vd-mail-bar { display: flex; align-items: center; gap: 8px; padding: 10px 24px; background: #F7F7F8;
  border-bottom: 1px solid #EAEBEC; color: #70737C; font-size: .8125rem; }
.vd-dot { width: 8px; height: 8px; border-radius: 4px; background: #10256B; }
.vd-mail-head { display: flex; align-items: center; gap: 12px; padding: 20px 24px 0; }
.vd-avatar { flex: 0 0 40px; height: 40px; border-radius: 20px; background: #10256B; color: #FFFFFF;
  display: grid; place-items: center; font-weight: 600; }
.vd-sender { flex: 1; min-width: 0; line-height: 1.4; }
.vd-sender b { display: block; font-weight: 600; font-size: .9375rem; }
.vd-sender span, .vd-when { color: #70737C; font-size: .8125rem; }
.vd-subject { padding: 16px 24px 0; font-size: 1.25rem; font-weight: 600; line-height: 1.35; word-break: keep-all; }
.vd-body { padding: 16px 24px 24px; }
.vd-body > p { margin: 0 0 16px; }
.vd-status { border: 1px solid; border-radius: 12px; padding: 16px 18px; margin-bottom: 16px; }
.vd-status.pass { background: #F2FFF6; border-color: #B8EFCA; }
.vd-status.candidate { background: #F3F5FB; border-color: #CDD5EE; }
.vd-status.more { background: #FFF5F5; border-color: #F8CFCF; }
.vd-pill { display: inline-block; font-size: .75rem; font-weight: 600; color: #FFFFFF; border-radius: 999px;
  padding: 2px 10px; margin-bottom: 8px; }
.pass .vd-pill { background: #006E25; } .candidate .vd-pill { background: #10256B; } .more .vd-pill { background: #B00C0C; }
.vd-result { font-size: 1.125rem; font-weight: 600; line-height: 1.4; margin-bottom: 6px; word-break: keep-all; }
.pass .vd-result { color: #006E25; } .candidate .vd-result { color: #10256B; } .more .vd-result { color: #B00C0C; }
.vd-status p { margin: 0; color: #46474C; }
.vd-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-bottom: 20px; }
.vd-stat { border: 1px solid #EAEBEC; border-radius: 12px; padding: 12px 14px; }
.vd-stat.key { background: #F7F7F8; }
.vd-stat span { display: block; color: #70737C; font-size: .8125rem; }
.vd-stat b { font-size: 1.375rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.vd-stat small { color: #70737C; font-size: .8125rem; }
.vd-sign { color: #46474C; }
.vd-foot { background: #F7F7F8; border-top: 1px solid #EAEBEC; padding: 14px 24px; color: #70737C; font-size: .75rem; }
.vd-foot p { margin: 0; }
@keyframes vd-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes vd-pop { from { opacity: 0; transform: translateY(10px) scale(.96); } to { opacity: 1; transform: none; } }
@keyframes vd-grow { from { opacity: 0; max-height: 0; margin-top: 0; transform: translateY(12px); }
  to { opacity: 1; max-height: 260px; margin-top: 10px; transform: none; } }
@media (prefers-reduced-motion: reduce) { .vd-phone, .vd-m1, .vd-m2, .vd-mail { animation: none; } }
</style>"""


def show_verdict(ev: dict):
    totals = coach.total_scores(ev, state.retries)
    result = coach.verdict(totals, ev["panel_average"])
    st.caption(
        f"판정 기준: **합격** 위원 평균 {coach.PASS_PANEL:.1f} · 최신 종합 {coach.PASS_TOTAL} 이상 · "
        f"**합격 후보** 위원 평균 {coach.CANDIDATE_PANEL:.1f} · 최신 종합 {coach.CANDIDATE_TOTAL} 이상 · "
        "그 밖은 재도전 필요. 재도전하면 최신 종합이 바뀌어요 (평가 탭 타이틀과 같은 기준)."
    )
    if not state.verdict_open:
        if st.button(":material/mail: 최종 결과 확인하기", type="primary"):
            state.verdict_open = True
            st.rerun()
        return

    company = html.escape(profile["company"])
    name = html.escape(profile["name"])
    job = html.escape(profile["job"])
    need = " · ".join(html.escape(s) for s in result["short"])
    # 위원 평균이 모자라면 재도전만으로는 못 채운다 (재도전은 종합 점수만 올림) → 다음 회차 면접을 안내
    next_round = f"재도전으로 대답을 수정하는 연습을 거친 후, {int(state.round) + 1}회차 면접을 통해 위원 평가 점수를 올려보세요."
    if result["level"] == "pass":
        title, body = "모의면접 합격입니다. 당신의 가능성을 증명했습니다.", "암기와 말하기 연습을 지속하세요."
    elif result["level"] == "candidate":
        title = "합격 후보로 선정되었습니다."
        body = (f"합격선(위원 평균 {coach.PASS_PANEL:.1f} · 종합 {coach.PASS_TOTAL})까지 <b>{need}</b> 남았어요. "
                + (next_round if result["panel_short"] else
                   "경쟁률이 높을 경우 재도전으로 대답을 수정하거나 암기와 말하기 연습으로 다듬어보세요."))
    else:
        title = next_round if result["panel_short"] else "재도전으로 대답을 수정해보세요."
        body = f"합격 후보까지 <b>{need}</b> 부족해요. 아직 역전의 기회가 남아 있어요."
    initial = html.escape(profile["company"].strip()[:1] or "M")  # 보낸 사람 동그라미: 회사 이름 첫 글자
    mail = (
        '<div class="vd-mail">'
        + '<div class="vd-mail-bar"><span class="vd-dot"></span>받은편지함 · 새 메일 1통</div>'
        + f'<div class="vd-mail-head"><div class="vd-avatar">{initial}</div>'
        + f'<div class="vd-sender"><b>{company} 모의면접 위원회</b><span>받는 사람: {name}</span></div>'
        + '<div class="vd-when">지금</div></div>'
        + f'<div class="vd-subject">[{company}] {job} 신입 모의면접 결과 안내 ({state.round}회차)</div>'
        + '<div class="vd-body">'
        + f"<p>{name}님, 모의면접에 참여해 주셔서 감사합니다.</p>"
        + f'<div class="vd-status {result["level"]}"><span class="vd-pill">{result["label"]}</span>'
        + f'<div class="vd-result">{title}</div><p>{body}</p></div>'
        + '<div class="vd-stats">'
        + f'<div class="vd-stat key"><span>최신 종합</span><b>{totals["latest"]}</b><small>/{coach.TOTAL_MAX}</small></div>'
        + f'<div class="vd-stat"><span>최초 종합</span><b>{totals["first"]}</b><small>/{coach.TOTAL_MAX}</small></div>'
        + f'<div class="vd-stat"><span>위원 평균</span><b>{ev["panel_average"]:.1f}</b><small>/{coach.PANEL_MAX}</small></div>'
        + "</div>"
        + f'<div class="vd-sign">{company} 모의면접 위원회 드림</div>'
        + "</div>"
        # 안내 문구는 메일 맨 아래 주석으로 모은다
        + '<div class="vd-foot">'
        + f"<p>※ 보낸 사람: {company} 모의면접 위원회 · 이 앱에서만 보이는 시뮬레이션이에요.</p>"
        + "<p>※ 이 결과는 AI 모의면접 학습 지표이며 실제 채용 결과와 무관하고, 실제 합격 가능성을 보장하지 않아요. "
          "문자와 메일은 실제로 보내지 않아요.</p>"
        + "</div></div>"
    )
    st.html(
        VERDICT_CSS
        + '<div class="vd">'
        + '<div class="vd-phone"><div class="vd-notch"></div>'
        + f'<div class="vd-contact">{company} (모의)<span>문자 메시지</span></div>'
        + '<div class="vd-thread">'
        + '<div class="vd-m1"><div class="vd-sms">최종 면접 결과가 도착했습니다.</div><div class="vd-time">지금</div></div>'
        + f'<div class="vd-m2"><div class="vd-sms">{name}님, {company} {job} 신입 모의면접 결과를 '
          "메일로 보내 드렸습니다. 메일함을 확인해 주세요.</div><div class=\"vd-time\">지금</div></div>"
        + "</div></div>"
        + mail
        + "</div>"
    )
    report_col, retry_col = st.columns(2)
    if report_col.button(":material/description: 성장 리포트 보기", type="primary", width="stretch"):
        state.open_report = True  # 리포트 창 열기
        st.rerun()
    if not result["passed"] and retry_col.button(":material/replay: 재도전으로 점수 올리기", width="stretch"):
        state.go_tab = RETRY_TAB
        st.rerun()


# ── 암기 시뮬레이션: 핵심어 뽑기 · 빈칸 · 채점은 모두 coach.py 규칙 (AI 호출 없음) ──
WEEKDAYS = "월화수목금토일"
MEMO_CSS = f"""<style>
.mm {{ line-height: 2.1; overflow-wrap: anywhere; }}
.mm .key {{ color: {HIGHLIGHT_TEXT}; background: #E8EBF5; border-radius: 4px; padding: 1px 6px; margin: 0 3px 3px 0;
  display: inline-block; font-size: .92em; }}
.mm .blank {{ color: transparent; border-bottom: 2px solid currentColor; border-bottom-color: #AEB0B6; padding: 0 2px; }}
.mm .shown {{ color: {HIGHLIGHT_TEXT}; background: #DCE1F0; border-radius: 3px; padding: 0 2px; }}
.mm .kw {{ color: {HIGHLIGHT_TEXT}; background: #E8EBF5; border-radius: 3px; padding: 0 3px; font-weight: 600; }}
.mm .rest {{ opacity: .62; }}  /* 테마 글자색을 흐리게: 라이트 · 다크 모두 대비 4.5 이상 */
.mm .badge {{ display: inline-block; font-size: .75em; font-weight: 600; color: #B00C0C; background: #FFFFFF;
  border: 1px solid #FF4242; border-radius: 4px; padding: 0 4px; margin-right: 4px; line-height: 1.4; }}
.mm .sline {{ padding: 2px 6px; margin-bottom: 4px; }}
.mm .sgap {{ color: {HIGHLIGHT_TEXT}; background: #FEECEC; border-left: 4px solid #FF4242; border-radius: 4px;
  padding: 2px 6px; margin-bottom: 4px; }}
.mm .legend .sgap {{ display: inline; padding: 0 4px; border-left-width: 3px; }}
.mm .legend {{ font-size: .85em; }}
</style>"""


# 말하기 중 경과 시간 표시 (브라우저에서 1초마다). __ELAPSED__ = 서버가 잰 경과(ms), __START__ = 시작 시각.
# 네이비(#4263D6)는 밝은 · 어두운 화면 모두에서 읽힌다.
SPEAK_TIMER_HTML = """<div id="t" style="font:600 1.2rem system-ui,sans-serif;color:#4263D6"></div>
<script>
const s = Date.now() - __ELAPSED__;
const el = document.getElementById("t");
function tick() {
  const e = Math.floor((Date.now() - s) / 1000);
  el.textContent = "● 말하는 중 · 시작 __START__ · "
    + String(Math.floor(e / 60)).padStart(2, "0") + ":" + String(e % 60).padStart(2, "0");
}
tick(); setInterval(tick, 250);
</script>"""


def latest_answer(no: int) -> str:
    """재도전했으면 마지막 재도전 답, 아니면 면접 때 답."""
    retry = state.retries.get(no)
    return retry["answer"] if retry else coach.answer_text(state.messages, no - 1)


def key_chips(keys: list[str], css: str = "key") -> str:
    return "".join(f'<span class="{css}">{html.escape(k)}</span>' for k in keys) or "<small>(핵심어 없음)</small>"


def go_memo_step(index: int):
    """단계별 연습: MEMO_STEPS[index] 로 옮긴다 (모드 · 빈칸 단계는 다음 실행에서 그리기 전에 정한다)."""
    state.go_memo = index
    st.rerun()


def timer_buttons(key: str, phase: str):
    """한 단계의 타이머 버튼. 재는 중에는 ':material/play_arrow: 시작' 자리가 ':material/close: 취소'(기록하지 않고 끝내기)로 바뀐다.
    ':material/stop: 완료' 는 기록하고 끝낸다. 시작 · 완료 시각과 걸린 시간은 서버 시각으로 잰다."""
    timer = state.get("speak_timer")
    running = bool(timer) and timer["key"] == key and timer["phase"] == phase
    start_col, stop_col = st.columns(2)
    if running:
        # 시작과 취소는 다른 key 라서, 시작을 누른 다음 실행에서 취소가 눌린 것으로 잡히지 않는다
        if start_col.button(":material/close: 취소", key=f"speak_cancel_{phase}_{key}", width="stretch",
                            help="기록하지 않고 타이머를 끝내요."):
            state.speak_timer = None
            st.rerun()
    elif start_col.button(":material/play_arrow: 시작", key=f"speak_start_{phase}_{key}", width="stretch", type="primary"):
        state.speak_timer = {"key": key, "phase": phase, "t": time.time(), "label": user_now().strftime("%H:%M:%S")}
        st.rerun()
    if stop_col.button(":material/stop: 완료", key=f"speak_stop_{phase}_{key}", width="stretch",
                       type="primary" if running else "secondary", help="걸린 시간을 기록하고 끝내요."):
        if not running:
            st.info("먼저 이 단계의 ':material/play_arrow: 시작' 을 눌러 주세요.")
        else:
            log = {
                "시작": timer["label"],
                "완료": user_now().strftime("%H:%M:%S"),
                "걸린 시간(초)": round(time.time() - timer["t"]),
            }
            logs = speak_logs_for(key)
            logs[phase] = ([log] + logs.get(phase, []))[: coach.SPEAK_LOG_KEEP]
            state.speak_logs[key] = logs
            state.speak_timer = None
            st.rerun()
    if running:
        # 서버 기준 경과를 넘겨서 브라우저 시계와 서버 시계가 달라도 같은 시간을 보여 준다.
        # st.iframe 은 스크립트를 실행하므로 사용자 글 · AI 출력은 넣지 않는다 (숫자와 서버 시각만 넣음).
        elapsed_ms = int((time.time() - timer["t"]) * 1000)
        st.iframe(
            SPEAK_TIMER_HTML.replace("__ELAPSED__", str(elapsed_ms)).replace("__START__", timer["label"]),
            height=40,
        )
    return running


def skeleton_html(text: str) -> str:
    """뼈대: 문장마다 핵심어 칩."""
    parts = [f'<div>{i}. {key_chips(item["keys"])}</div>' for i, item in enumerate(coach.skeleton(text), 1)]
    return MEMO_CSS + '<div class="mm">' + "".join(parts) + "</div>"


def cloze_html(text: str, level: int, reveal: bool = False) -> str:
    """빈칸: 가린 핵심어는 밑줄만 (reveal 이면 노랗게 보여 줌)."""
    words = []
    for word, hidden in coach.cloze(text, level):
        css = ("shown" if reveal else "blank") if hidden else ""
        words.append(f'<span class="{css}">{html.escape(word)}</span>' if css else html.escape(word))
    return MEMO_CSS + '<div class="mm">' + " ".join(words) + "</div>"


def go_speak_phase(phase: str):
    """말하기 모드: 그 단계(· 힌트)로 옮긴다 (다음 실행에서 그리기 전에 정한다)."""
    state.go_speak = phase
    st.rerun()


def speak_logs_for(key: str) -> dict:
    logs = state.speak_logs.get(key, {})
    if isinstance(logs, list):  # 단계가 나뉘기 전 기록은 '대본 없이 말하기' 로 본다
        logs = {"speak": logs}
    return logs


def show_speaking(key: str, text: str, question: str):
    """:material/record_voice_over: 말하기 모드: 1단계 대본 읽기 → 2단계 힌트(뼈대 → 빈칸 가볍게 · 절반 · 전부) → 3단계 대본 없이.
    단계마다 타이머로 재고, 1단계 읽기 시간과 비교한다."""
    if state.get("speak_step") not in coach.SPEAK_STEP_NAMES:
        state.speak_step = 1
    step = st.segmented_control(
        "단계", list(coach.SPEAK_STEP_NAMES), key="speak_step", required=True,
        format_func=lambda n: f"{SPEAK_STEP_ICONS[n]} {coach.SPEAK_STEP_NAMES[n]}", width="stretch",
    )

    hint = None
    if step == 1:
        st.caption("대본을 소리 내어 읽으며 재요. 내 읽기 속도를 구하고, 2 · 3단계 시간과 비교해요.")
    elif step == 2:
        if state.get("speak_hint") not in coach.SPEAK_HINTS:
            state.speak_hint = "skeleton"
        hint = st.segmented_control(
            "힌트", list(coach.SPEAK_HINTS), key="speak_hint", required=True, format_func=coach.SPEAK_HINTS.get,
            help="뼈대 → 가볍게 → 절반 → 전부 순서로 힌트를 줄여 가며 말해 보세요.",
        )
        st.caption("아래 힌트만 보고 소리 내어 말하며 재요.")
    else:
        st.caption("대본을 가리고 기억나는 대로 말하며 재요.")
    phase = coach.speak_phase(step, hint)

    running = timer_buttons(key, phase)
    if step == 1:
        if running:
            with st.container(border=True):
                st.write(text)
        else:
            st.caption(":material/play_arrow: 시작을 누르면 대본이 보여요.")
    elif step == 2:
        st.html(skeleton_html(text) if hint == "skeleton" else cloze_html(text, hint))

    logs = speak_logs_for(key)
    read_s = logs["read"][0]["걸린 시간(초)"] if logs.get("read") else None
    if logs.get(phase):
        for kind, message in coach.phase_feedback(read_s, logs[phase][0]["걸린 시간(초)"], phase, text, question):
            getattr(st, kind)(message)

    # 지금까지 잰 단계별 최근 시간 (1단계 읽기 대비)
    progress = []
    for p in coach.SPEAK_PHASES:
        if logs.get(p):
            seconds = logs[p][0]["걸린 시간(초)"]
            versus = f"{(seconds - read_s) / read_s * 100:+.0f}%" if read_s and p != "read" else "-"
            progress.append({"단계": coach.phase_label(p), "최근 시간(초)": seconds, "읽기 대비": versus})
    if progress:
        st.markdown("**단계별 기록**")
        st.table(progress, hide_index=True)

    following = coach.next_phase(phase)
    if following and st.button(f"다음 단계로 :material/arrow_forward: {coach.phase_label(following)}", key=f"speak_next_{phase}"):
        go_speak_phase(following)


def show_memo_strategy():
    try:
        st.markdown(coach.load_memo_strategy())
    except OSError:
        st.error("암기 전략 문서(data/암기전략.md)를 읽지 못했어요.")
    st.markdown("**복습 일정**")
    for label, day in coach.review_schedule(user_now().date()):
        st.markdown(f"- {label}: {day.month}월 {day.day}일 ({WEEKDAYS[day.weekday()]})")


def show_memo_skeleton(no: int, source: str, text: str):
    st.caption(":material/record_voice_over: 핵심어만 보고 소리 내어 답해 보세요. 걸리는 시간은 위 '내 대본' 옆에 있어요.")
    # 스위치: 끄면 뼈대(핵심어)만, 켜면 전체 문장에서 빠진 내용을 회색으로 함께
    full = st.toggle(
        "전체 문장 함께 보기", key=f"memo_full_{no}_{source}",
        help="끄면 뼈대(핵심어)만 보여요. 켜면 핵심어 사이에 빠진 내용을 회색으로 함께 보여 줘요.",
    )
    if full:
        rows = []
        for i, sentence in enumerate(coach.split_sentences(text), 1):
            words = [
                f'<span class="{"kw" if kind == "key" else "rest"}">{html.escape(w)}</span>'
                for w, kind in coach.mark_words(sentence)
            ]
            rows.append(f"<div>{i}. {' '.join(words)}</div>")
        st.html(MEMO_CSS + '<div class="mm">' + "".join(rows)
                + '<div class="legend"><span class="kw">핵심어</span> · <span class="rest">회색은 빠진 내용</span></div></div>')
    else:
        st.html(skeleton_html(text))


def show_memo_cloze(no: int, source: str, text: str) -> int:
    if state.get("memo_level") not in coach.MEMO_TAGS:
        state.memo_level = 1  # 태그는 하나가 꼭 골라져 있게 (기본: 가볍게)
    level = st.segmented_control(
        "가리는 양", options=list(coach.MEMO_TAGS), key="memo_level", required=True,
        format_func=coach.MEMO_TAGS.get,
        help="가볍게: 핵심어 4개 중 1개 · 절반: 2개 중 1개 · 전부: 핵심어를 모두 가려요.",
    )
    reveal = st.toggle("정답 보기", key=f"memo_reveal_{no}_{source}_{level}")
    st.html(cloze_html(text, level, reveal))
    hidden_count = sum(1 for _, h in coach.cloze(text, level) if h)
    st.caption(f"빈칸 {hidden_count}개 · 빈칸에 들어갈 말을 소리 내어 말한 뒤 '정답 보기' 로 확인해 보세요.")
    return level


def sentence_lines(rows: list[str]) -> str:
    return MEMO_CSS + '<div class="mm">' + "".join(rows) + "</div>"


def show_memo_simulation(result_key: str, question: dict, text: str):
    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        st.markdown(question["question"])
    attempt = st.text_area(
        "기억나는 대로 답해 보세요 (원래 답은 가려져 있어요)", height=160,
        key=f"memo_try_{result_key}", max_chars=coach.MAX_ANSWER_CHARS,
    )
    if st.button("확인하기", type="primary", key=f"memo_check_{result_key}"):
        if not attempt.strip():
            st.info("기억나는 대로 적은 뒤 눌러 주세요.")
        else:
            check = {
                **coach.recall_check(text, attempt),
                "sentences": coach.sentence_recall(text, attempt),
                "attempt": attempt.strip(),
            }
            state.memo_results[result_key] = check
            state.memo_best[result_key] = max(state.memo_best.get(result_key, 0), check["recall"])
    check = state.memo_results.get(result_key)
    if not check:
        return

    written = check.get("attempt", attempt)  # 이 칸이 생기기 전 기록은 지금 칸의 글
    sentences = check.get("sentences") or coach.sentence_recall(text, written)
    judged = [row for row in sentences if row["remembered"] is not None]
    remembered = sum(1 for row in judged if row["remembered"])
    rate_col, sentence_col, best_col = st.columns(3)
    rate_col.metric("핵심어 기억", f"{check['recall']}%", help=f"{len(check['found'])}/{check['total']}개")
    sentence_col.metric("문장 기억", f"{remembered}/{len(judged)}")
    best_col.metric("이 답 최고 기록", f"{state.memo_best.get(result_key, 0)}%")
    st.progress(check["recall"] / 100)
    back = coach.fallback_step(check["recall"])
    if back is None:
        st.success(f"핵심어를 {coach.MEMO_PASS}% 넘게 기억했어요. 다음 질문으로 넘어가도 좋아요.")
    else:
        # 생각보다 덜 외워졌으면 낮은 단계부터 다시
        st.warning(
            f"생각보다 덜 외워졌어요 ({check['recall']}%). "
            f"**{coach.step_label(back)}** 부터 다시 연습하고 돌아오세요."
        )
        if st.button(f":material/fast_rewind: {coach.step_label(back)} 부터 다시", key=f"memo_back_{result_key}", type="primary"):
            go_memo_step(back)

    # 원래 답(왼쪽) · 내가 쓴 답(오른쪽)을 문장마다 한 줄씩 나란히. 기억 못 한 원래 문장만 칠한다.
    left, right = st.columns(2)
    with left:
        st.markdown("**원래 답**")
        st.html(sentence_lines([
            # 색만으로 구분하지 않도록 '놓침' 글자 배지도 붙인다 (ui-ux-pro-max: Color Only)
            (f'<div class="sgap"><span class="badge">놓침</span>{i}. {html.escape(row["sentence"])}</div>'
             if row["remembered"] is False else f'<div class="sline">{i}. {html.escape(row["sentence"])}</div>')
            for i, row in enumerate(sentences, 1)
        ]))
    with right:
        st.markdown("**내가 쓴 답**")
        st.html(sentence_lines([
            f'<div class="sline">{i}. {html.escape(s)}</div>' for i, s in enumerate(coach.split_sentences(written), 1)
        ]))
    st.html(MEMO_CSS + f'<div class="mm"><div class="legend"><span class="sgap">칠한 문장</span> = 그 문장 핵심어를 '
            f"{round(coach.SENTENCE_RECALL * 100)}% 미만으로 쓴 원래 문장</div></div>")


TEXT_MODE, SPEAK_MODE = ":material/edit_note: 텍스트 모드", ":material/record_voice_over: 말하기 모드"


def script_hidden() -> bool:
    """외우는 중이라 대본을 가려야 하는 단계: 텍스트 ③ 실전 시뮬레이션 · 말하기 모드 (말하기 1단계는 시작하면 대본이 나온다)."""
    if state.get("memo_top") == SPEAK_MODE:
        return True
    return state.get("memo_view") == coach.MEMO_MODES[-1]


def show_script_editor(no, result_key: str, original: str, text: str, ev: dict | None, practice: dict | None = None):
    """:material/menu_book: 대본: 먼저 읽고, 아래 '넓게 열어 고치기' 로 고친다. 저장하면 모든 연습 단계가 고친 대본을 쓴다.
    화면 폭이 좁아서 넓은 창(대화 상자)에서 원래 대본 | 고친 대본을 나란히 보며 고친다.
    외우는 단계(script_hidden)에서는 대본을 접어 둔다."""
    edited = result_key in state.memo_edits
    st.markdown(":material/menu_book: **내 대본**" + (" · :green[고친 대본]" if edited else "")
                + f"  :gray[· 소리 내어 읽으면 약 {coach.speak_seconds(text)}초]")
    lines = "  \n".join(coach.split_sentences(text)) or ":gray[아직 대본이 없어요. 아래 버튼으로 써 보세요.]"
    if script_hidden():
        with st.expander("대본 펼쳐 보기 · 지금은 외우는 단계라 접어 뒀어요"):
            st.markdown(lines)
    else:
        with st.container(border=True):
            st.markdown(lines)
    label = ":material/open_in_full: 넓게 열어 고치기" if text else ":material/edit: 넓게 열어 대본 쓰기"
    if st.button(label, key=f"memo_edit_open_{result_key}",
                 help="원래 대본과 고친 대본을 나란히 보며 고쳐요. 말해 보니 어색한 곳이 있으면 바로 고쳐 보세요."):
        script_dialog(no, result_key, original, text, ev, practice)
    if not practice:  # 다른 질문은 연습만: 재도전 검토 내역이 없다
        show_review_result(no, result_key, ev)


def graded_answers(no: int) -> set[str]:
    """이 질문에서 이미 채점받은 답 (면접 때 답 · 재도전한 답). 띄어쓰기 · 줄바꿈 차이는 같은 답으로 본다."""
    def norm(s: str) -> str:
        return " ".join(s.split())
    answers = [coach.answer_text(state.messages, no - 1)] + [a["answer"] for a in state.get("retry_history", {}).get(no, [])]
    return {norm(a) for a in answers if a.strip()}


@st.dialog("대본 고치기", width="large")
def script_dialog(no, result_key: str, original: str, text: str, ev: dict | None, practice: dict | None = None):
    """원래 대본 | 고친 대본. '수정하고 재도전 검토 받기' 는 재도전 탭과 같은 RETRY 채점 · 같은 횟수 상한 (AI 1번).
    이미 채점받은 대본과 같으면 다시 채점하지 않는다 (AI 점수가 흔들려 점수만 바뀌고 기회가 줄기 때문).
    practice ({question, label}): 이번 회차가 아닌 '다른 질문' — 저장 · 되돌리기만 있고 채점하지 않는다."""
    draft_key = f"memo_draft_{result_key}"
    # 저장하지 않고 창을 닫아도 쓰던 글은 남긴다 (창이 닫히면 칸의 값은 지워지므로 따로 보관)
    kept = state.setdefault("memo_draft_kept", {})
    by_line = "\n".join(coach.split_sentences(text))  # 왼쪽 원래 대본처럼 한 문장씩 줄을 바꿔 비교하기 쉽게
    if state.pop("memo_draft_reset", None) == result_key:
        kept.pop(result_key, None)
        state[draft_key] = by_line  # 칸을 그리기 전에만 값을 바꿀 수 있다
    elif draft_key not in state:
        state[draft_key] = kept.get(result_key, by_line)

    def keep_draft():
        kept[result_key] = state[draft_key]

    if practice:
        st.markdown(f"**다른 질문 · 연습만** {practice['question']}")
    else:
        st.markdown(f"**질문 {no}.** {state.questions[no - 1]['question']}")
    left, right = st.columns(2)
    with left:
        st.markdown(f"**원래 대본** · {practice['label'] if practice else '내 최신 답'}")
        with st.container(border=True, height=360):
            st.markdown("  \n".join(coach.split_sentences(original)) or "(답 없음)")
    with right:
        draft = st.text_area("**고친 대본**", key=draft_key, height=360, max_chars=coach.MAX_ANSWER_CHARS, on_change=keep_draft)
        if result_key in kept and " ".join(kept[result_key].split()) != " ".join(text.split()):
            st.caption(":material/draft: 저장하지 않은 고친 글이에요. 창을 닫아도 남아 있어요.")
    save_col, review_col, undo_col = st.columns([1, 1.4, 1])
    if save_col.button(":material/save: 고친 대본 저장", key=f"memo_save_{result_key}", width="stretch"):
        if not draft.strip():
            st.info("대본을 적은 뒤 저장해 주세요.")
        else:
            state.memo_edits[result_key] = draft.strip()
            state.memo_results.pop(result_key, None)  # 대본이 바뀌었으니 지난 채점은 지운다
            kept.pop(result_key, None)
            st.rerun()
    if practice:
        review_col.caption("다른 질문은 연습만 해요. 점수는 이번 회차 면접 답으로만 계산해요.")
    elif review_col.button(":material/replay: 수정하고 재도전 검토 받기", key=f"memo_review_{result_key}", type="primary", width="stretch"):
        used = state.retry_counts.get(no, 0)
        if not draft.strip():
            st.info("대본을 적은 뒤 눌러 주세요.")
        elif not ev:
            st.info("위원 4명에게 평가받은 뒤에 재도전 검토를 받을 수 있어요. :material/forum: 면접 탭의 '위원 4명에게 평가받기' 를 눌러 주세요.")
        elif used >= coach.MAX_RETRIES:
            st.info(f"이 질문은 재도전 검토를 {coach.MAX_RETRIES}번 모두 받았어요. 고친 대본은 저장해서 연습할 수 있어요.")
        elif " ".join(draft.split()) in graded_answers(no):
            st.info("이미 채점받은 대본이라 다시 채점하지 않았어요 (재도전 기회는 그대로예요). "
                    "대본을 고친 뒤 다시 누르거나, 연습만 하려면 '고친 대본 저장' 을 눌러 주세요.")
        else:
            last = ev["answers"][no - 1]
            new_answer = draft.strip()

            def store(raw):
                state.memo_edits[result_key] = new_answer
                attempt = {"answer": new_answer, **coach.summarize_retry(raw)}
                record_retry(no, attempt, last["score"])
                state.retry_counts[no] = used + 1
                state.memo_results.pop(result_key, None)
                state.memo_reviews[result_key] = len(state.retry_history[no]) - 1  # 몇 번째 재도전인지
                kept.pop(result_key, None)

            if call_ai(
                "고친 대본을 채점하고 있어요...",
                coach.build_retry(profile, state.questions[no - 1], coach.answer_text(state.messages, no - 1), last["weak"]),
                new_answer, RETRY_SCHEMA, "retry", store,
            ):
                st.rerun()
    # 되돌리기는 고친 글을 지우므로 한 번 더 묻는다 (지운 글은 되살릴 수 없음)
    ask_key = f"memo_undo_ask_{result_key}"
    if undo_col.button(":material/undo: 원래 대본으로 되돌리기", key=f"memo_undo_{result_key}", width="stretch"):
        state[ask_key] = True
    if state.get(ask_key):
        st.warning("고친 대본을 지우고 원래 대본으로 되돌릴까요? 지운 글은 되살릴 수 없어요.")
        cancel_col, confirm_col = st.columns(2)
        if cancel_col.button("고친 대본 남기기", key=f"memo_undo_cancel_{result_key}", width="stretch"):
            state.pop(ask_key, None)
            st.rerun(scope="fragment")
        if confirm_col.button(":material/delete: 고친 대본 지우기", key=f"memo_undo_yes_{result_key}", width="stretch"):
            state.pop(ask_key, None)
            state.memo_edits.pop(result_key, None)
            state.memo_results.pop(result_key, None)
            state.memo_draft_reset = result_key
            st.rerun()
    if not practice:
        st.caption(
            f"재도전 검토는 :material/replay: 재도전 탭과 같은 기준으로 채점하고, 질문당 {coach.MAX_RETRIES}번까지예요 "
            f"(지금 {state.retry_counts.get(no, 0)}번). 처음 점수보다 높으면 가장 높은 점수가 종합 점수 · 리포트에 반영돼요. "
            "저장 · 검토 · 되돌리기를 마치면 이 창이 닫혀요."
        )


def show_review_result(no: int, result_key: str, ev: dict | None):
    """'수정하고 재도전 검토 받기' 결과를 바로 아래에: 재도전 탭의 결과와 같은 구조 (show_retry_result)."""
    index = state.memo_reviews.get(result_key)
    history = state.get("retry_history", {}).get(no, [])
    if not ev or not isinstance(index, int) or not 0 <= index < len(history):
        return
    with st.container(border=True):
        st.markdown(f"**:material/fact_check: 재도전 검토 내역** · {index + 1}번째 재도전")
        show_retry_result(no, ev, index, "memo", celebrate=True)


MEMO_SCOPES = ["이번 회차 질문", "다른 질문 · 연습만"]


def source_kind(label: str) -> str:
    """답변 보기 이름의 종류: 회차 숫자가 들어간 이름(지난 n회차 답 · 내 연습 대본 (n회차))은 숫자를 빼고 본다."""
    if label.startswith("지난 "):
        return "지난 회차 답"
    if label.startswith("내 연습 대본"):
        return "내 연습 대본"
    return label


def remember_source(key: str):
    state.memo_source_pref = source_kind(state[key])


def pick_source(col, sources: dict, key: str, help_text: str) -> str:
    """답변 보기: 한 번 고른 종류(예: 만점 예시 · 내가 쓴 대본)는 질문을 바꿔도 다른 것을 누를 때까지 그대로.
    그 질문에 그 종류가 없으면 첫 번째(기본)로."""
    options = list(sources)
    match = next((o for o in options if source_kind(o) == state.get("memo_source_pref")), None)
    if match:
        state[key] = match  # 칸을 그리기 전이라 값을 정할 수 있다
    elif state.get(key) not in options:
        state.pop(key, None)
    return col.radio("답변 보기", options, horizontal=True, key=key, help=help_text,
                     on_change=remember_source, args=(key,))


def step_question(key: str, options: list, delta: int):
    """암기 탭 < > 버튼: 고르는 칸(key)을 이전 · 다음 질문으로. 버튼 콜백이라 칸을 그리기 전에 바뀐다."""
    current = state.get(key)
    i = options.index(current) if current in options else 0
    state[key] = options[(i + delta) % len(options)]


def other_questions() -> list[dict]:
    """암기 탭 '다른 질문': 불러온 지난 회차 리포트의 질문(그 회차 최신 답)과 질문 은행의 나머지 질문 (coach.practice_questions)."""
    reports = past_reports()
    try:
        bank = coach.load_questions()
    except (OSError, ValueError, KeyError):
        return []
    return coach.practice_questions(reports, [q["question"] for q in state.questions], bank,
                                    profile["job"], coach.field_of(profile))


def show_memorize():
    st.subheader(":material/psychology: 암기 시뮬레이션")
    st.caption("AI를 부르지 않아요. 핵심어는 간단한 규칙(조사를 뗀 3글자 이상 · 숫자가 든 단어)으로 뽑아서 완벽하지 않을 수 있어요.")

    # 단계 이동 표시가 있으면 모드 · 단계 · 빈칸 양을 그리기 전에 정한다.
    if "go_memo" in state:
        step_mode, step_level = coach.MEMO_STEPS[state.pop("go_memo")]
        state.memo_top = TEXT_MODE
        state.memo_view = coach.MEMO_MODES[step_mode]
        if step_level:
            state.memo_level = step_level
    if "go_speak" in state:
        step, hint = coach.phase_step(state.pop("go_speak"))
        state.memo_top = SPEAK_MODE
        state.speak_step = step
        if hint is not None:
            state.speak_hint = hint

    ev = state.evaluation
    scores = {}
    if ev:
        totals_by_no = {a["no"]: a["score"] for a in ev["answers"]}
        scores = {no: state.retries[no]["score"] if no in state.retries else s for no, s in totals_by_no.items()}
    # 연습할 질문: 이번 회차 질문(점수 · 재도전 검토 있음) / 다른 질문(지난 회차 · 질문 은행, 연습만)
    if state.get("memo_scope") not in MEMO_SCOPES:
        state.memo_scope = MEMO_SCOPES[0]
    scope = st.segmented_control("연습할 질문", MEMO_SCOPES, key="memo_scope", required=True,
                                 help="다른 질문은 지난 회차 질문과 질문 은행의 질문이에요. 연습만 하고 점수에는 들어가지 않아요.")
    practice = None
    if scope == MEMO_SCOPES[0]:
        labels = {
            i + 1: f"질문 {i + 1}" + (f" · {scores[i + 1]}/{coach.ANSWER_MAX}점" if i + 1 in scores else "") + f" · {q['question']}"
            for i, q in enumerate(state.questions)
        }
        question_col, source_col = st.columns([3, 2])
        no = question_col.selectbox("외울 질문", list(labels), format_func=labels.get, key="memo_no")
        question = state.questions[no - 1]
        sources = {"내 최신 답": latest_answer(no)}
        saved = coach.saved_practice(past_reports()).get(question["question"])
        if saved:  # 지난 회차에 고친 연습 대본 (점수에는 들어가지 않는다)
            sources[f"내 연습 대본 ({saved['round']}회차)"] = saved["script"]
        if ev and ev["answers"][no - 1]["needs_rewrite"] and ev["answers"][no - 1]["rewrite"].strip():
            sources["AI 고친 답"] = ev["answers"][no - 1]["rewrite"]
        source = pick_source(source_col, sources, f"memo_source_{no}", "AI 고친 답은 14점 미만인 답에만 있어요.")
        caption = f"질문 {no}" + (f" · 지금 점수 {scores[no]}/{coach.ANSWER_MAX}점" if no in scores else "")
        pick_key, options = "memo_no", list(labels)
    else:
        others = other_questions()
        if not others:
            st.info("연습할 다른 질문이 없어요. 다음 회차 면접을 하면 지난 회차 질문이 여기에 쌓여요.")
            return
        by_id = {q["id"]: q for q in others}
        question_col, source_col = st.columns([3, 2])
        no = question_col.selectbox(
            "외울 질문 (연습만)", list(by_id), key="memo_other",
            format_func=lambda i: by_id[i]["question"] + (
                f" · 지난 {by_id[i]['past']['round']}회차" if by_id[i]["past"]
                else f" · {by_id[i]['saved']['round']}회차 연습" if by_id[i]["saved"] else ""),
        )
        question = by_id[no]
        sources = {}
        if question["saved"]:  # 지난 회차에 고치거나 직접 쓴 대본이 있으면 그걸 먼저
            sources[f"내 연습 대본 ({question['saved']['round']}회차)"] = question["saved"]["script"]
        if question["past"]:
            sources[f"지난 {question['past']['round']}회차 답"] = question["past"]["answer"]
        if question["example"]:
            sources["만점 예시"] = question["example"]
        sources["내가 쓴 대본"] = ""
        source = pick_source(source_col, sources, f"memo_source_{no}",
                             "만점 예시는 가상 지원자의 예시라 내 경험에 맞게 고쳐 쓰세요. '내가 쓴 대본' 은 직접 써서 외워요.")
        practice = {"question": question["question"], "label": source}
        options = list(by_id)
        caption = f"다른 질문 {options.index(no) + 1}/{len(options)} · 연습만 (점수는 이번 회차 면접 답으로만 계산해요)"
        pick_key = "memo_other"
    result_key = f"{no}:{source}"
    original = sources[source].strip()
    text = state.memo_edits.get(result_key, original).strip()  # 고친 대본이 있으면 그걸로 외운다
    # 지금 질문을 크게: 질문을 보고 답하는 연습이라 질문이 화면의 첫 내용이어야 한다
    # 양옆 < > 로 이전 · 다음 질문 (끝에서는 처음으로 돌아간다 · 버튼을 막지 않는다)
    with st.container(border=True, key="memo_qcard"):
        # < > 는 윗줄(질문 번호 · 점수) 양옆에만. 질문 글은 아랫줄에 카드 폭 전체로
        prev_col, body_col, next_col = st.columns([1, 12, 1], vertical_alignment="center")
        prev_col.button(":material/chevron_left:", key="memo_prev", help="이전 질문",
                        on_click=step_question, args=(pick_key, options, -1))
        body_col.caption(caption)
        next_col.button(":material/chevron_right:", key="memo_next_q", help="다음 질문",
                        on_click=step_question, args=(pick_key, options, 1))
        st.markdown(f"#### {question['question']}")
    if practice and not text:  # 다른 질문: 대본을 직접 쓰면 그때부터 연습할 수 있다
        show_script_editor(no, result_key, original, text, None, practice)
        return
    if not text:
        st.info("이 질문에는 아직 외울 답이 없어요. 재도전 탭에서 이 질문에 답하면 여기서 외울 수 있어요.")
        if ev and st.button(":material/replay: 재도전 탭에서 답 쓰기", key=f"memo_empty_go_{no}"):
            state.go_retry_no = no
            state.go_tab = RETRY_TAB
            st.rerun()
        return
    show_script_editor(no, result_key, original, text, ev, practice)
    st.divider()

    # 답변 연습: 모드 → 단계 → 단계 내용 순서. 외우는 전략은 두 모드 공통이라 제목 옆 작은 버튼으로.
    title_col, strategy_col = st.columns([4, 1], vertical_alignment="center")
    title_col.subheader(":material/record_voice_over: 답변 연습")
    with strategy_col.popover(":material/push_pin: 전략 보기", width="stretch"):
        show_memo_strategy()
    if state.get("memo_top") not in (TEXT_MODE, SPEAK_MODE):
        state.memo_top = TEXT_MODE
    top = st.segmented_control("모드", [TEXT_MODE, SPEAK_MODE], key="memo_top", required=True, width="stretch")

    if top == SPEAK_MODE:
        show_speaking(result_key, text, question["question"])
        return

    # 텍스트 모드: 누른 단계의 기능만 보인다
    if state.get("memo_view") not in coach.MEMO_MODES:
        state.memo_view = coach.MEMO_MODES[0]
    view = st.segmented_control("단계", coach.MEMO_MODES, key="memo_view", required=True, width="stretch")
    mode_index = coach.MEMO_MODES.index(view)
    level = None
    if mode_index == 0:
        show_memo_skeleton(no, source, text)
    elif mode_index == 1:
        level = show_memo_cloze(no, source, text)
    else:
        show_memo_simulation(result_key, question, text)

    # 지금 단계가 익숙해지면 다음 단계로
    following = coach.next_step(mode_index, level)
    if following is not None and st.button(
        f"다음 단계로 :material/arrow_forward: {coach.step_label(following)}", key=f"memo_next_{mode_index}_{level}"
    ):
        go_memo_step(following)


# 탭 = 단계. 이름 앞 번호로 순서를 보여 주고, 위의 단계 표시가 완료 · 남은 단계를 알려 준다.
CHAT_TAB, EVAL_TAB, RETRY_TAB = ":material/forum: 1. 면접", ":material/bar_chart: 2. 평가", ":material/replay: 3. 재도전"
VERDICT_TAB, MEMO_TAB = ":material/mail: 4. 최종 결과", ":material/psychology: 5. 암기"
LAST_TAB = ":material/live_help: 6. 점검하기"  # 사전 정보 탐색 · 마지막에 할 질문
FEEDBACK_URL = os.getenv("FEEDBACK_SURVEY_URL", "").strip()  # 다 마친 뒤 설문 링크 (.env · Streamlit Secrets)
if not FEEDBACK_URL.startswith("https://"):
    FEEDBACK_URL = ""


def step_status() -> list[dict]:
    """단계마다 이름 · 완료 여부 · 선택 단계 여부. 완료는 그 단계에서 실제로 한 일이 있을 때."""
    tabs = [CHAT_TAB, EVAL_TAB, RETRY_TAB, VERDICT_TAB, MEMO_TAB, LAST_TAB, None]  # 마지막은 리포트 버튼
    return [{"tab": tab, "name": r["item"], "done": r["done"], "optional": r["optional"]}
            for tab, r in zip(tabs, checklist_rows())]


def show_stepper(steps: list[dict]):
    """단계 진행: 'n단계 중 n단계 완료 · 남은 단계 n개' 와 진행 막대만 (탭 이름에 단계 번호가 있어 중복 표시는 하지 않는다)."""
    done = sum(s["done"] for s in steps)
    st.progress(done / len(steps), text=coach.checklist_summary(steps))  # 리포트 창 체크리스트와 같은 문장


def mark_report_downloaded():
    state.report_downloaded = True


def show_finish():
    """마지막 단계(리포트 받기)까지 마치면 설문으로 연결한다. 남은 선택 단계가 있으면 함께 알려 준다."""
    left = [s["name"] for s in step_status() if not s["done"]]
    if left:
        st.success(":material/celebration: 마지막 단계인 리포트까지 받았어요. 수고하셨어요!")
        st.caption(f"남은 선택 단계({' · '.join(left)})는 언제든 이어서 할 수 있어요.")
    else:
        st.success(":material/celebration: 모든 단계를 마쳤어요. 수고하셨어요!")
    if FEEDBACK_URL:
        st.write("서비스를 써 보신 경험을 알려 주시면 더 좋은 연습 도구를 만드는 데 쓸게요. (1~2분)")
        st.link_button("피드백 설문 참여하기", FEEDBACK_URL, icon=":material/rate_review:", type="primary")
    else:
        st.caption(":material/rate_review: 피드백 설문 링크는 준비 중이에요.")

# 탭 · 재도전 질문을 바꾸라는 표시가 있으면, 그리기 전에 정한다 (그린 뒤에는 바꿀 수 없음).
if state.pop("open_eval", False):
    state.view = EVAL_TAB
if state.get("go_tab"):
    state.view = state.pop("go_tab")
if state.get("go_retry_no"):
    state.retry_no = state.pop("go_retry_no")

# 탭은 면접 시작부터 항상 같은 모양 · 같은 key 로 둔다. 화면 구조가 바뀌면
# Streamlit이 대화를 다시 그리면서 스크롤이 맨 위로 올라가기 때문이다.
show_stepper(step_status())
chat_tab, eval_tab, retry_tab, verdict_tab, memo_tab, last_tab = st.tabs(
    [CHAT_TAB, EVAL_TAB, RETRY_TAB, VERDICT_TAB, MEMO_TAB, LAST_TAB], key="view", on_change="rerun"
)

with chat_tab:
    show_messages()
    live = st.container()  # 답을 보내는 동안의 내 답 · 로딩 · 에러가 대화 바로 아래에 나온다
    if state.stage == "done":
        st.success("질문 5개를 모두 마쳤어요. 수고하셨습니다.")
        if state.evaluation:
            st.info("평가가 끝났어요. 위의 :material/bar_chart: 평가 탭에서 확인해 주세요.")
            if st.button(":material/bar_chart: 평가 확인하기", type="primary"):
                state.go_tab = EVAL_TAB
                st.rerun()
        elif st.button("위원 4명에게 평가받기", type="primary"):
            def store(raw):
                state.evaluation = coach.summarize_evaluation(raw, state.questions)
                state.pop("clue_set", None); state.pop("clue_round", None)
                state.go_tab = EVAL_TAB  # 평가가 끝나면 평가 탭으로 바로 이동

            if call_ai(
                "답변을 검토하겠습니다. 위원 4명이 면접 기록을 보고 있어요...",
                coach.build_evaluator(profile),
                coach.format_record(state.questions, state.messages),
                EVAL_SCHEMA, "evaluation", store,
            ):
                st.rerun()

with eval_tab:
    if state.evaluation:
        show_evaluation(state.evaluation)
    elif state.stage == "done":
        st.info(":material/forum: 면접 탭의 '위원 4명에게 평가받기' 버튼을 눌러 주세요.")
    else:
        st.info("질문 5개를 마치면 위원 4명에게 평가받을 수 있어요.")

with retry_tab:
    if state.evaluation:
        show_retry(state.evaluation)
    else:
        st.info("위원 4명에게 평가받은 뒤, 점수가 낮은 질문부터 다시 답해 볼 수 있어요.")

with last_tab:
    show_precheck()  # 사전 탐색은 면접 전 · 중에도 쓸 수 있게 항상 보인다
    st.divider()
    if state.stage == "done":
        show_last_question()
    else:
        st.info("면접을 마치면 마지막에 할 질문을 추천받고, 내 질문을 다듬을 수 있어요.")

with verdict_tab:
    if state.evaluation:
        show_verdict(state.evaluation)
    else:
        st.info("위원 4명에게 평가받으면 최종 결과를 확인할 수 있어요.")

with memo_tab:
    if state.stage == "done":
        show_memorize()
    else:
        st.info("면접을 마치면 내 답을 외우는 연습을 할 수 있어요.")



@st.dialog("면접 리포트", width="large")
def report_dialog():
    """위쪽 :material/description: 리포트 버튼 · 최종 결과의 '성장 리포트 보기' 가 여는 넓은 창.
    창 안의 다운로드는 창만 다시 그려서, 받은 뒤 마침 안내(설문)가 창 안에 바로 보인다."""
    if state.evaluation:
        show_report(state.evaluation)
        if state.get("report_downloaded"):
            show_finish()
    else:
        st.info("위원 4명에게 평가받으면 면접리포트.md 를 받을 수 있어요. :material/forum: 면접 탭에서 질문 5개를 마친 뒤 평가받아 주세요.")


if state.pop("open_report", False):
    report_dialog()
if state.pop("open_next_round", False) and state.get("evaluation"):
    next_round_dialog()

# 면접이 끝나도 평가받기 전까지는 입력창을 둔다 (맨 아래 고정 입력창이 사라지면 페이지 높이가 바뀌며 스크롤이 튄다).
# 평가를 받은 뒤에는 뺀다: 입력창이 있으면 Streamlit 이 화면을 '맨 아래에 붙여' 두어서,
# 긴 내용이 그려질 때 저절로 맨 아래로 내려가기 때문이다.
if state.stage == "done":
    if not state.evaluation:
        pass_input = st.chat_input("면접이 끝났어요. 위원 4명에게 평가받아 보세요.")
    else:
        pass_input = None
    if pass_input is not None:
        next_button = ":material/bar_chart: 평가 확인하기" if state.evaluation else "위원 4명에게 평가받기"
        with live:
            st.info(f"면접은 끝났어요. '{next_button}' 버튼을 눌러 주세요.")
    st.stop()

answer = st.chat_input(f"답을 적어 주세요 ({coach.MAX_ANSWER_CHARS:,}자까지)", max_chars=coach.MAX_ANSWER_CHARS)
if answer is not None:
    if not answer.strip():
        with live:
            st.info("답을 적은 뒤 보내 주세요.")
        st.stop()

    with live:
        with st.chat_message("user", avatar=AVATARS["user"]):
            st.markdown(answer)

    question = state.questions[state.q_index]
    instructions = coach.build_interviewer(profile, question)
    transcript = coach.format_transcript(state.messages + [{"role": "user", "content": answer}])

    try:
        with live, st.spinner("면접관이 답을 읽고 있어요..."):
            result = ask_json(instructions, transcript, INTERVIEWER_SCHEMA, "interviewer")
    except LLMError as e:
        with live:
            st.error(str(e))
        st.stop()

    q = state.q_index
    state.messages.append({"role": "user", "content": answer, "q": q})
    state.understanding = coach.clamp(result.get("understanding"), 0, 100)
    reply = str(result.get("reply", "")).strip()
    ai_wants_follow_up = bool(result.get("follow_up"))

    if coach.should_follow_up(ai_wants_follow_up, state.follow_ups):
        # 꼬리 질문: 같은 질문에 머문다.
        state.follow_ups += 1
        state.messages.append({"role": "assistant", "content": reply, "q": q})
    else:
        # AI가 꼬리 질문을 더 원해도 한도를 넘으면 그 문장(질문)은 보여 주지 않고 넘어간다.
        if reply and not ai_wants_follow_up:
            state.messages.append({"role": "assistant", "content": reply, "q": q})
        state.q_index += 1
        state.follow_ups = 0
        if state.q_index < coach.TOTAL_QUESTIONS:
            state.messages.append(question_message(state.q_index))
        else:
            state.messages.append({"role": "assistant", "content": "면접을 마치겠습니다."})
            state.stage = "done"
    st.rerun()
