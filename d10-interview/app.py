# Streamlit 화면만. 프롬프트는 prompts.py, AI 호출은 llm.py, 계산은 coach.py.
import html
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
import streamlit as st

import coach
from llm import LLMError, ask_json
from prompts import (
    EVAL_SCHEMA,
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

st.set_page_config(page_title="AI 면접 코치", page_icon="🎤")
DEFAULT_TIMEZONE = "Asia/Seoul"  # 브라우저 시간대를 모를 때
# Streamlit에는 테마를 코드로 바꾸는 공식 기능이 없어서, 기본 설정 메뉴 위치를 알려 준다.
st.caption("🌓 다크 · 라이트 모드는 오른쪽 위 ⋮ 메뉴 → Settings 에서 바꿀 수 있어요.")


def reset(job: str | None = None):
    """job 을 주면 그 직군 모드의 시작 화면으로, 없으면 직군 고르기 화면으로."""
    st.session_state.clear()
    st.session_state.stage = "start" if job else "pick"
    if job:
        st.session_state.job = job


if "stage" not in st.session_state:
    reset()

state = st.session_state

# 아이콘 캐릭터 (원작 그래픽 대신 이모지)
AVATARS = {"assistant": "🧑‍💼", "user": "🙋"}
PANEL_ICONS = {"실무 전문가": "🛠️", "논리 분석가": "🧩", "커뮤니케이션 전문가": "💬", "채용 담당자": "🤝"}


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
    text = f"**질문 {index + 1}/{coach.TOTAL_QUESTIONS}.** {state.questions[index]['question']}"
    return {"role": "assistant", "content": text, "q": index, "kind": "question"}


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
        st.markdown(f"**{state.job} 직군 모드**" + (f" · {state.round}회차" if state.get("round") else ""))
    if state.stage == "pick":
        st.caption("직군을 고르면 그 직군 모드로 시작해요.")
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
    if state.stage != "pick":
        if st.button("처음부터 다시", width="stretch", help="같은 직군 모드로 새 면접을 시작해요."):
            reset(state.job)
            st.rerun()
        if st.button("직군 다시 고르기", width="stretch"):
            reset()
            st.rerun()


# ── 직군 고르기 ─────────────────────────────────────────────
if state.stage == "pick":
    st.title("AI 면접 코치")
    st.write("신입 모의면접이에요. 먼저 지원할 직군을 골라 주세요.")
    for column, job in zip(st.columns(len(coach.JOBS)), coach.JOBS):
        if column.button(job, width="stretch", type="primary" if PERSONAS[job] else "secondary"):
            if PERSONAS[job]:
                reset(job)
                st.rerun()
            else:
                st.info(f"'{job}' 직군 모드는 준비 중이에요. 면접관 페르소나가 아직 없어요.")
    st.stop()


# ── 시작 화면 ───────────────────────────────────────────────
if state.stage == "start":
    job = state.job
    st.title(f"{job} 직군 모드")
    st.write("신입 모의면접이에요. 질문 5개와 꼬리 질문으로 진행해요.")

    # 두 갈래 시작: 새 면접 / 이전 면접 이어하기
    mode = state.get("start_mode")
    new_col, resume_col = st.columns(2)
    if new_col.button("🆕 새 면접 시작하기", width="stretch", type="primary" if mode == "new" else "secondary"):
        if mode != "new":
            for key in ("previous", "previous_file", "f_name", "f_company", "f_company_desc", "f_experience"):
                state.pop(key, None)  # 이어하기에서 채운 값을 비우고 새로 시작
        state.start_mode = "new"
        st.rerun()
    if resume_col.button("📂 이전 면접 이어하기", width="stretch", type="primary" if mode == "resume" else "secondary"):
        state.start_mode = "resume"
        st.rerun()
    if not mode:
        st.caption("처음이면 '새 면접 시작하기', 지난 회차 면접리포트.md 가 있으면 '이전 면접 이어하기' 를 눌러 주세요.")
        st.stop()

    st.caption(f"이번 면접: **{coach.next_round(state.get('previous'))}회차**")

    if mode == "resume":
        uploaded = st.file_uploader(
            "이어서 할 회차의 면접리포트.md 를 하나만 올려 주세요.",
            type=["md"],
            accept_multiple_files=False,
            help="파일 하나에는 그 회차 데이터만 들어 있어요. 이어 하면 다음 회차로 기록돼요.",
        )
        if uploaded is None:
            state.previous = None
            state.previous_file = None
        elif uploaded.file_id != state.get("previous_file"):
            # 새 파일을 올렸을 때 한 번만 읽고, 아래 칸을 채운 뒤 다시 그린다.
            state.previous_file = uploaded.file_id
            try:
                previous = coach.parse_report(uploaded.getvalue().decode("utf-8", errors="replace"))
            except ValueError as e:
                state.previous = None
                st.error(str(e))
            else:
                if previous["profile"]["job"] != job:
                    state.previous = None
                    st.warning(
                        f"이 리포트는 '{previous['profile']['job']}' 직군이에요. "
                        "사이드바의 '직군 다시 고르기' 에서 그 직군을 골라 주세요."
                    )
                else:
                    state.previous = previous
                    for field in ("name", "company", "company_desc", "experience"):
                        state[f"f_{field}"] = previous["profile"][field]
                    # 경험 칸 글자 수 상한에 맞춘다 (상한보다 긴 값을 넣으면 칸이 에러를 낸다)
                    state.f_experience = state.f_experience[: coach.MAX_EXPERIENCE_CHARS]
                    st.rerun()

        previous = state.get("previous")
        if previous:
            st.success(
                f"{previous['round']}회차({previous['date']}) 면접을 불러왔어요. "
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
        started = st.form_submit_button("면접 시작하기", type="primary")

    if started:
        name, company, experience = name.strip(), company.strip(), experience.strip()
        company_desc = company_desc.strip()
        if not name or not company or not company_desc or not experience:
            st.warning("이름 · 회사 · 회사 설명 · 내 경험을 모두 적어 주세요.")
        elif len(experience) < coach.MIN_EXPERIENCE_CHARS:
            st.warning(f"내 경험을 {coach.MIN_EXPERIENCE_CHARS}자 이상 적어 주세요. (지금 {len(experience)}자)")
        else:
            previous = state.get("previous")
            same = bool(previous) and state.get("previous_mode", "").startswith("같은 질문")
            try:
                bank = coach.load_questions()
                matched = coach.match_questions(bank, job, previous["questions"]) if same else None
                if same and matched is None:
                    state.notice = "지난 질문 중 질문 은행에 없는 질문이 있어서 새 질문으로 시작했어요."
                questions = matched or coach.pick_questions(bank, job)
            except (OSError, ValueError, KeyError):
                st.error("질문 은행(data/questions.csv)을 읽지 못했어요.")
            else:
                state.profile = {
                    "name": name,
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
                state.retries = {}
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
        st.markdown(f"**🏢 회사** · {profile['company']} ({profile['company_desc']})")
        st.markdown(f"**💼 직군** · {profile['job']} 신입 · {state.round}회차")
        st.markdown(f"**{AVATARS['assistant']} 면접관** · {coach.persona_summary(profile['job'])}")
        kinds = " → ".join(q["type"] for q in state.questions)
        st.markdown(f"**📝 질문** · {coach.TOTAL_QUESTIONS}개 ({kinds})")
        if state.get("same_questions"):
            st.caption("지난 회차와 같은 질문이에요. 평가 후 질문별로 점수를 비교해 드려요.")
    st.markdown(
        f"- 질문은 한 번에 하나씩 나와요. 답이 부족하면 면접관이 **꼬리 질문을 최대 {coach.MAX_FOLLOW_UPS}개** 해요.\n"
        f"- 답은 한 번에 **{coach.MAX_ANSWER_CHARS:,}자**까지 쓸 수 있어요.\n"
        "- 면접이 끝나면 위원 4명이 평가하고, 점수가 낮은 질문은 다시 도전할 수 있어요.\n"
        "- 새로고침하면 진행 기록이 사라져요. 평가 뒤 📄 리포트 탭에서 면접리포트.md 를 받아 두세요."
    )
    begin_col, back_col = st.columns([2, 1])
    if begin_col.button("면접을 시작하겠습니다.", type="primary", width="stretch"):
        state.stage = "interview"
        st.rerun()
    if back_col.button("← 설정 고치기", width="stretch"):
        for field in ("name", "company", "company_desc", "experience"):
            state[f"f_{field}"] = profile[field]  # 입력한 값을 그대로 다시 채운다
        state.stage = "start"
        st.rerun()
    st.stop()


# ── 면접 화면 ───────────────────────────────────────────────
profile = state.profile
for state_key, empty in (
    ("highlights", {}), ("last_suggest", None), ("last_question", None), ("previous", None), ("round", 1),
    ("strategies", {}), ("retry_counts", {}), ("verdict_open", False),
):
    if state_key not in state:  # 이 기능이 생기기 전에 시작한 세션도 열리게
        state[state_key] = empty
if state.get("notice"):
    st.info(state.pop("notice"))
st.title(f"{profile['company']} · {profile['job']} 신입 면접 · {state.round}회차")

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
HIGHLIGHT_TEXT = "#111111"
HIGHLIGHT_CSS = f"""<style>
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


def show_legend():
    st.html(HIGHLIGHT_CSS + '<div class="hl">' + " ".join(chip(t) for t in HIGHLIGHT_COLORS)
            + " <small>· 줄무늬는 여러 기준 · 문장을 누르면 상세 보기</small></div>")


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


ACTION_ICONS = {"추가": "➕", "수정": "✏️", "축약": "✂️", "삭제": "🗑️"}


def show_strategy(place: str, cache_key: str, no: int, scores: dict, weak: str, answer: str, ev: dict):
    """20점 미만인 답에 '+N점 전략 가이드'. 더 받을 수 있는 점수는 코드가 계산하고, 전략 글은 AI가 쓴다.
    cache_key 로 한 번 만든 전략을 저장해 두고, 같은 답이면 평가 · 재도전 탭이 같이 쓴다."""
    gap = coach.strategy_gap(scores)
    if not gap:
        return
    st.markdown(f"**🎯 +{sum(gap.values())}점 전략 가이드**")
    st.caption(" · ".join(f"{coach.CRITERIA[key]} +{g}" for key, g in gap.items()))
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
    for item in state.strategies[cache_key]:
        with st.container(border=True):
            st.markdown(f"**{item['name']}** {item['score']}/{coach.CRITERION_MAX} · **+{item['gain']}점 여지**")
            for t in item["tips"]:
                line = f"{ACTION_ICONS.get(t['action'], '•')} **{t['action']}** · {t['tip']}"
                if t["target"]:
                    line += f"  \n  ↳ 내 답: \"{t['target']}\""
                st.markdown(line)
            if not item["tips"]:
                st.caption("이 기준에 대한 전략을 받지 못했어요.")


def show_clues(ev: dict):
    """역전의 실마리: 가장 낮은 답 MAX_CLUES 개와 각 답의 가장 낮은 기준. 고르는 건 코드(coach.pick_clues)."""
    clues = coach.pick_clues(ev)
    if not clues:
        st.success("🎉 모든 답이 20점 만점이에요.")
        return
    st.subheader("🔍 역전의 실마리를 찾았습니다.")
    st.caption(f"점수가 가장 낮은 답 {len(clues)}개예요. 여기부터 고치면 점수가 가장 많이 올라요.")
    for clue in clues:
        with st.container(border=True):
            st.markdown(
                f"**질문 {clue['no']}** · {clue['score']}/{coach.ANSWER_MAX}점 · "
                f"가장 약한 기준 **{clue['name']} {clue['criterion_score']}/{coach.CRITERION_MAX}**"
            )
            st.caption(clue["question"])
            st.markdown(f"**가장 약한 점:** {clue['weak']}")
            st.caption(f"아래 '답변별 점수' 의 질문 {clue['no']} 칸에서 형광펜 · 전략 가이드 · 고친 답을 볼 수 있어요.")
            if st.button("🔁 역전의 기회 잡기", key=f"clue_retry_{clue['no']}", type="primary"):
                state.go_retry_no = clue["no"]
                state.go_tab = RETRY_TAB
                st.rerun()


def show_evaluation(ev: dict):
    show_clues(ev)
    st.divider()

    st.metric("위원 평균", f"{ev['panel_average']:.1f}/{coach.PANEL_MAX}")
    # st.table 은 긴 글을 칸 안에서 줄바꿈해서 가로 스크롤이 생기지 않는다 (st.dataframe 은 줄바꿈 옵션이 없음).
    st.table(
        [
            {
                "위원": f"{PANEL_ICONS.get(m['role'], '')} {m['role']}",
                "평가 기준": PANEL_CRITERIA[m["role"]],
                "뽑지 말아야 할 이유": m["against"],
                "좋은 점": m["good"],
                "점수": m["score"],
            }
            for m in ev["panel"]
        ],
        hide_index=True,
    )
    with st.expander("📚 평가 기준과 근거 보기"):
        try:
            st.markdown(coach.load_panel_rationale())
        except OSError:
            st.error("평가 기준 근거 문서(data/평가기준_근거.md)를 읽지 못했어요.")
    st.markdown(f"**판단이 갈린 곳:** {ev['conflict']}")
    st.markdown(f"**모두 같은 판단:** {ev['agree']}")

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
    for a in ev["answers"]:
        with st.expander(f"질문 {a['no']} · {a['score']}/{coach.ANSWER_MAX}점", expanded=a["needs_rewrite"]):
            # 형광펜은 답변마다 필요할 때만 켠다 (켠 답변만 AI를 부른다). 스위치는 질문 칸 맨 위.
            highlight_on = highlight_toggle(f"hl_eval_{a['no']}")
            st.caption(a["question"])
            st.write(" · ".join(f"{name} {a['scores'][key]}" for key, name in coach.CRITERIA.items()))
            st.markdown("**내 답**")
            show_answer(
                coach.answer_text(state.messages, a["no"] - 1),
                state.questions[a["no"] - 1],
                f"eval:{a['no']}",
                highlight_on,
            )
            st.markdown(f"**가장 약한 점:** {a['weak']}")
            show_strategy(
                "eval", f"eval:{a['no']}", a["no"], a["scores"], a["weak"],
                coach.answer_text(state.messages, a["no"] - 1), ev,
            )
            if a["needs_rewrite"]:
                st.markdown("**고친 답**")
                st.info(a["rewrite"])
                if a["check"]:
                    st.markdown("**사람이 확인할 것**")
                    for fact in a["check"]:
                        st.markdown(f"- {fact}")

    st.subheader("다음 연습에서 고칠 것")
    for item in ev["next"]:
        st.markdown(f"- {item}")
    st.caption("🔁 재도전 탭에서 점수가 낮은 질문에 다시 답해 볼 수 있어요.")


def highlight_toggle(key: str) -> bool:
    """답 하나에만 형광펜을 켜고 끄는 스위치."""
    return st.toggle("🖍️ 형광펜 모드", key=key, help="이 답의 문장마다 어떤 기준과 연결되는지 색으로 보여 줘요.")


def show_answer(text: str, question: dict, cache_key: str, highlight_on: bool):
    """답 하나를 보여 준다. highlight_on 이면 형광펜으로.
    cache_key 가 같으면 (예: 평가 탭과 재도전 탭의 같은 답) 한 번 만든 형광펜을 같이 쓴다."""
    sentences = coach.split_sentences(text)
    block = {"question": question["question"], "point": question["point"], "sentences": sentences}
    highlight = get_highlight(cache_key, [block]) if highlight_on and sentences else None
    if highlight:
        show_legend()
        show_highlighted(sentences, highlight["numbers"][0], highlight["marks"])
    else:
        st.write(" ".join(sentences) or "(답 없음)")


def show_retry(ev: dict):
    ordered = coach.retry_order(ev["answers"])
    labels = {a["no"]: f"질문 {a['no']} · {a['score']}/{coach.ANSWER_MAX}점 · {a['question']}" for a in ordered}
    no = st.selectbox("다시 답할 질문 (점수 낮은 순)", list(labels), format_func=labels.get, key="retry_no")
    last = next(a for a in ordered if a["no"] == no)
    question = state.questions[no - 1]
    before = coach.answer_text(state.messages, no - 1)

    st.metric("지난 점수", f"{last['score']}/{coach.ANSWER_MAX}")
    st.markdown(f"**지난 약한 점:** {last['weak']}")
    with st.expander("지난 답 보기"):
        show_answer(before, question, f"eval:{no}", highlight_toggle(f"hl_retry_before_{no}"))
    # 다시 쓰기 전에 참고하도록 지난 답의 전략 가이드 (평가 탭과 같은 결과를 같이 쓴다)
    show_strategy("retry_before", f"eval:{no}", no, last["scores"], last["weak"], before, ev)

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
                state.retries[no] = {"answer": new_answer.strip(), **coach.summarize_retry(raw)}
                state.retry_counts[no] = used + 1

            if call_ai(
                "다시 쓴 답을 채점하고 있어요...",
                coach.build_retry(profile, question, before, last["weak"]),
                new_answer.strip(), RETRY_SCHEMA, "retry", store,
            ):
                st.rerun()

    result = state.retries.get(no)
    if result:
        diff = coach.compare(last["scores"], result["scores"])
        if diff["diff"] > 0:
            st.success(f"🎉 역전 성공! {diff['before']} → {diff['after']}점 (+{diff['diff']})")
        elif diff["diff"] == 0:
            st.info(f"점수가 {diff['after']}점 그대로예요. 아래 약한 점과 전략 가이드를 보고 한 부분만 바꿔 보세요.")
        else:
            st.warning(
                f"{diff['before']} → {diff['after']}점으로 {-diff['diff']}점 내려갔어요. "
                "아래 기준별 변화와 약한 점을 보고 다시 도전해 보세요."
            )
        st.metric("후 점수", f"{diff['after']}/{coach.ANSWER_MAX}", delta=diff["diff"])
        # 기준별 전/후 막대 그래프 (숫자는 모두 coach.compare() 가 계산한 값)
        chart = pd.DataFrame(
            {"전": [r["전"] for r in diff["rows"]], "후": [r["후"] for r in diff["rows"]]},
            index=[r["기준"] for r in diff["rows"]],
        )
        st.bar_chart(chart, stack=False, y_label="점수 (0~5)", color=["#9AA0A6", "#4C8BF5"], height=240)
        st.table(diff["rows"], hide_index=True)
        st.markdown(f"**이번 답의 약한 점:** {result['weak']}")
        st.markdown("**다시 쓴 답**")
        retry_key = f"retry:{no}:{result['answer']}"
        show_answer(result["answer"], question, retry_key, highlight_toggle(f"hl_retry_after_{no}"))
        show_strategy("retry_after", retry_key, no, result["scores"], result["weak"], result["answer"], ev)


def show_question_cards(pairs: list[tuple[str, str]]):
    for angle, question in pairs:
        with st.container(border=True):
            st.caption(f"{angle} 관점")
            st.markdown(question)


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
    st.subheader("🔍 사전 정보 직접 탐색")
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
                    st.checkbox(f"✅ **{item['item']}**", key=f"pre_found_{i}")
                    st.caption(f"찾는 곳: {item['where']}")
                    st.text_input(
                        "찾은 내용 메모",
                        key=f"pre_memo_{i}",
                        placeholder="예: 2025년 시리즈 B 투자",
                        label_visibility="collapsed",
                        max_chars=coach.MAX_MEMO_CHARS,
                    )
                    if st.checkbox("❓ 찾아봐도 없어요", key=f"pre_missing_{i}") and not state.get(f"pre_found_{i}"):
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


def show_report(ev: dict):
    try:
        precheck_items = coach.load_precheck()
    except (OSError, KeyError, ValueError):
        precheck_items = []

    today = user_now().date()  # 파일 이름 · 리포트 날짜 모두 사용자 시간대 기준

    def build(updated_at: str | None = None) -> str:
        return coach.build_report(
            profile, state.questions, ev, state.retries, state.messages,
            state.last_suggest, state.last_question, state.previous, state.round,
            precheck_items, current_precheck(precheck_items), updated_at, today,
        )

    # 리포트 내용이 바뀐 때만 '마지막 업데이트' 시각을 새로 찍는다 (가장 최신 시각 하나만 남긴다).
    content = build()
    if state.get("report_content") != content:
        state.report_content = content
        state.report_updated = user_now().strftime("%Y-%m-%d %H:%M")
    report = build(state.report_updated)

    file_name = coach.report_file_name(profile["company"], profile["job"], state.round, today)
    st.warning("🔒 리포트에는 이름 · 회사 · 내 경험 원문 · 답변 · 체크리스트 메모가 들어가요. 다른 사람과 공유할 때 주의해 주세요.")
    button_col, time_col = st.columns([3, 2], vertical_alignment="center")
    button_col.download_button(
        f"{file_name} 다운로드",
        data=report,
        file_name=file_name,
        mime="text/markdown",
        type="primary",
    )
    time_col.caption(f"🕒 마지막 업데이트: **{state.report_updated}**")
    st.caption(
        "오른쪽 위 복사 아이콘으로 내용을 복사할 수 있어요. 점수는 모두 앱이 계산한 값이고, "
        "'AI 의견' 표시가 붙은 글은 AI가 쓴 거예요. 마지막 질문을 만들어 두면 리포트에 같이 들어가요. "
        "다음 면접 시작 화면에서 이 파일을 올리면 이어서 할 수 있어요 (맨 끝 주석은 이어 하기용 데이터예요)."
    )
    st.code(report, language="markdown")


# ── 최종 판결: 문자 → 이메일 연출. 판정은 coach.verdict(), 글은 모두 고정 문구 (AI 호출 없음) ──
VERDICT_CSS = """<style>
.vd { display: grid; gap: 14px; max-width: 560px; margin: 4px auto; }
.vd * { box-sizing: border-box; }
.vd-banner { background: #0F1115; color: #F2F3F5; border-radius: 12px; padding: 16px 18px;
  font-weight: 600; text-align: center; animation: vd-in .5s ease-out both; }
.vd-phone { background: #0F1115; border-radius: 28px; padding: 18px 14px 22px; max-width: 320px;
  width: 100%; margin: 0 auto; border: 4px solid #2B2F36; animation: vd-in .5s ease-out .25s both; }
.vd-notch { width: 80px; height: 6px; border-radius: 3px; background: #2B2F36; margin: 0 auto 14px; }
.vd-sms { background: #2B2F36; color: #F2F3F5; border-radius: 14px; padding: 12px 14px; font-size: .92em; line-height: 1.5; }
.vd-sms b { display: block; font-size: .8em; color: #9AA0A6; margin-bottom: 4px; }
.vd-mail { background: #FFFFFF; color: #1A1C20; border: 1px solid #DADCE0; border-radius: 12px;
  padding: 18px 20px; line-height: 1.6; animation: vd-in .5s ease-out .5s both; }
.vd-mail .vd-subject { font-weight: 700; font-size: 1.02em; margin-bottom: 8px; }
.vd-mail .vd-from { color: #5F6368; font-size: .85em; margin-bottom: 12px; }
.vd-mail .vd-result { font-size: 1.15em; font-weight: 700; margin: 10px 0; }
.vd-mail .vd-pass { color: #137333; }
.vd-mail .vd-candidate { color: #1A56C4; }
.vd-mail .vd-more { color: #B3261E; }
.vd-mail .vd-score { display: flex; gap: 12px; flex-wrap: wrap; margin: 8px 0; }
.vd-mail .vd-score span { background: #F1F3F4; border-radius: 8px; padding: 6px 10px; }
.vd-mail .vd-note { color: #5F6368; font-size: .82em; border-top: 1px solid #E8EAED; padding-top: 10px; margin-top: 12px; }
@keyframes vd-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .vd-banner, .vd-phone, .vd-mail { animation: none; } }
</style>"""


def show_verdict(ev: dict):
    totals = coach.total_scores(ev, state.retries)
    result = coach.verdict(totals, ev["panel_average"])
    st.caption(
        f"판정 기준 (최신 종합 {coach.PASS_TOTAL}/{coach.TOTAL_MAX} 이상일 때): "
        f"위원 평균 **{coach.PASS_PANEL:.1f} 이상 합격** · **{coach.CANDIDATE_PANEL:.1f} 이상 합격 후보** · "
        "그 밖은 추가 학습 필요. 재도전하면 최신 종합이 바뀌어요."
    )
    if not state.verdict_open:
        if st.button("📨 최종 결과 확인하기", type="primary"):
            state.verdict_open = True
            st.rerun()
        return

    company = html.escape(profile["company"])
    name = html.escape(profile["name"])
    job = html.escape(profile["job"])
    need = " · ".join(html.escape(s) for s in result["short"])
    if result["level"] == "pass":
        headline = '<div class="vd-result vd-pass">모의면접 합격입니다. 당신의 가능성을 증명했습니다.</div>'
    elif result["level"] == "candidate":
        headline = ('<div class="vd-result vd-candidate">합격 후보로 선정되었습니다.</div>'
                    f"<p>합격선(위원 평균 {coach.PASS_PANEL:.1f})까지 <b>{need}</b> 남았어요. "
                    "재도전으로 마지막 한 걸음을 채워 보세요.</p>")
    else:
        headline = ('<div class="vd-result vd-more">추가 학습이 필요해요.</div>'
                    f"<p>합격 후보까지 <b>{need}</b> 부족해요. 아직 역전의 기회가 남아 있어요.</p>")
    st.html(
        VERDICT_CSS
        + '<div class="vd">'
        + '<div class="vd-banner">최종 면접 결과가 도착했습니다.</div>'
        + '<div class="vd-phone"><div class="vd-notch"></div>'
        + f'<div class="vd-sms"><b>문자 · {company} (모의)</b>{name}님, {company} {job} 신입 모의면접 결과를 '
          "메일로 보내 드렸습니다. 메일함을 확인해 주세요.</div></div>"
        + '<div class="vd-mail">'
        + f'<div class="vd-subject">[{company}] {job} 신입 모의면접 결과 안내 ({state.round}회차)</div>'
        + f'<div class="vd-from">보낸 사람: {company} 모의면접 위원회 · 이 앱에서만 보이는 시뮬레이션이에요</div>'
        + f"<p>{name}님, 모의면접에 참여해 주셔서 감사합니다.</p>"
        + headline
        + '<div class="vd-score">'
        + f"<span>최신 종합 <b>{totals['latest']}</b>/{coach.TOTAL_MAX}</span>"
        + f"<span>최초 종합 {totals['first']}/{coach.TOTAL_MAX}</span>"
        + f"<span>위원 평균 <b>{ev['panel_average']:.1f}</b>/{coach.PANEL_MAX}</span>"
        + "</div>"
        + '<div class="vd-note">이 결과는 AI 모의면접 학습 지표이며 실제 채용 결과와 무관하고, '
          "실제 합격 가능성을 보장하지 않아요. 문자와 메일은 실제로 보내지 않아요.</div>"
        + "</div></div>"
    )
    report_col, retry_col = st.columns(2)
    if report_col.button("📄 성장 리포트 보기", type="primary", width="stretch"):
        state.go_tab = REPORT_TAB
        st.rerun()
    if not result["passed"] and retry_col.button("🔁 재도전으로 점수 올리기", width="stretch"):
        state.go_tab = RETRY_TAB
        st.rerun()


CHAT_TAB, EVAL_TAB, RETRY_TAB = "💬 면접", "📊 평가", "🔁 재도전"
LAST_TAB, VERDICT_TAB, REPORT_TAB = "🙋 마지막 질문", "📨 최종 결과", "📄 리포트"

# 탭 · 재도전 질문을 바꾸라는 표시가 있으면, 그리기 전에 정한다 (그린 뒤에는 바꿀 수 없음).
if state.get("go_tab"):
    state.view = state.pop("go_tab")
if state.get("go_retry_no"):
    state.retry_no = state.pop("go_retry_no")

# 탭은 면접 시작부터 항상 같은 모양 · 같은 key 로 둔다. 화면 구조가 바뀌면
# Streamlit이 대화를 다시 그리면서 스크롤이 맨 위로 올라가기 때문이다.
chat_tab, eval_tab, retry_tab, last_tab, verdict_tab, report_tab = st.tabs(
    [CHAT_TAB, EVAL_TAB, RETRY_TAB, LAST_TAB, VERDICT_TAB, REPORT_TAB], key="view", on_change="rerun"
)

with chat_tab:
    show_messages()
    live = st.container()  # 답을 보내는 동안의 내 답 · 로딩 · 에러가 대화 바로 아래에 나온다
    if state.stage == "done":
        st.success("질문 5개를 모두 마쳤어요. 수고하셨습니다.")
        if state.evaluation:
            st.info("평가가 끝났어요. 위의 📊 평가 탭에서 확인해 주세요.")
            if st.button("📊 평가 확인하기", type="primary"):
                state.go_tab = EVAL_TAB
                st.rerun()
        elif st.button("위원 4명에게 평가받기", type="primary"):
            def store(raw):
                state.evaluation = coach.summarize_evaluation(raw, state.questions)
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
        st.info("💬 면접 탭의 '위원 4명에게 평가받기' 버튼을 눌러 주세요.")
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

with report_tab:
    if state.evaluation:
        show_report(state.evaluation)
    else:
        st.info("위원 4명에게 평가받으면 면접리포트.md 를 받을 수 있어요.")

# 면접이 끝나도 입력창은 그대로 둔다. 화면 맨 아래 고정된 입력창이 사라지면
# 페이지 높이가 바뀌면서 스크롤이 위로 튀기 때문이다.
if state.stage == "done":
    if st.chat_input("면접이 끝났어요. 위원 4명에게 평가받아 보세요.") is not None:
        next_button = "📊 평가 확인하기" if state.evaluation else "위원 4명에게 평가받기"
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
