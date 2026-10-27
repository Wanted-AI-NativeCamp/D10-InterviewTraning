# Streamlit 화면만. 프롬프트는 prompts.py, AI 호출은 llm.py, 계산은 coach.py.
import html

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
            state[f"pre_memo_{i}"] = value["memo"]


# ── 사이드바 상태창 ──────────────────────────────────────────
with st.sidebar:
    st.header("상태창")
    if state.get("job"):
        st.markdown(f"**{state.job} 직군 모드**" + (f" · {state.round}회차" if state.get("round") else ""))
    if state.stage == "pick":
        st.caption("직군을 고르면 그 직군 모드로 시작해요.")
    elif state.stage == "start":
        st.caption("면접을 시작하면 진행 상황이 보여요.")
    else:
        answered = state.q_index
        current = min(answered + 1, coach.TOTAL_QUESTIONS)
        st.progress(answered / coach.TOTAL_QUESTIONS, text=f"질문 {current}/{coach.TOTAL_QUESTIONS}")
        st.metric("면접관이 본 이해도", "-" if state.understanding is None else f"{state.understanding}/100")
        if state.get("evaluation"):
            ev = state.evaluation
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

    st.caption(f"이번 면접: **{coach.next_round(state.get('previous'))}회차**")

    with st.expander("📂 이전 면접리포트.md로 이어서 하기", expanded=bool(state.get("previous"))):
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
                    st.rerun()

        previous = state.get("previous")
        if previous:
            st.success(
                f"{previous['round']}회차({previous['date']}) 면접을 불러왔어요. "
                f"이번 면접은 {coach.next_round(previous)}회차로 기록돼요. 아래 칸을 채웠으니 확인해 주세요."
            )
            if previous["precheck"]:
                st.caption(f"사전 정보 탐색 체크 · 메모 {len(previous['precheck'])}개도 이어서 채워져요.")
            st.metric("지난 위원 평균", f"{previous['panel_average']:.1f}/{coach.PANEL_MAX}")
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
            help=f"면접관이 참고할 경험을 {coach.MIN_EXPERIENCE_CHARS}자 이상 적어 주세요.",
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
                questions = coach.match_questions(bank, job, previous["questions"]) if same else None
                if same and questions is None:
                    state.notice = "지난 질문 중 질문 은행에 없는 질문이 있어서 새 질문으로 시작했어요."
                questions = questions or coach.pick_questions(bank, job)
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
                state.messages = [
                    {"role": "assistant", "content": f"{name} 님, 면접을 시작하겠습니다."},
                    question_message(0),
                ]
                state.stage = "interview"
                st.rerun()
    st.stop()


# ── 면접 화면 ───────────────────────────────────────────────
profile = state.profile
for state_key, empty in (
    ("highlights", {}), ("last_suggest", None), ("last_question", None), ("previous", None), ("round", 1),
    ("strategies", {}),
):
    if state_key not in state:  # 이 기능이 생기기 전에 시작한 세션도 열리게
        state[state_key] = empty
if state.get("notice"):
    st.info(state.pop("notice"))
st.title(f"{profile['company']} · {profile['job']} 신입 면접 · {state.round}회차")

def show_messages():
    for message in state.messages:
        with st.chat_message(message["role"]):
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
        try:
            with st.spinner("문장마다 기준을 표시하고 있어요..."):
                raw = ask_json(coach.build_highlight(profile), user_input, HIGHLIGHT_SCHEMA, "highlight")
        except LLMError as e:
            st.error(str(e))
            return None
        state.highlights[cache_key] = {"numbers": numbers, "marks": coach.summarize_highlight(raw)}
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
            try:
                with st.spinner("점수를 올릴 전략을 찾고 있어요..."):
                    raw = ask_json(
                        coach.build_strategy(profile, question, {"scores": scores, "weak": weak}, ev),
                        answer or "(답 없음)",
                        STRATEGY_SCHEMA,
                        "strategy",
                    )
            except LLMError as e:
                st.error(str(e))
            else:
                state.strategies[cache_key] = coach.summarize_strategy(raw, scores)
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


def show_evaluation(ev: dict):
    st.metric("위원 평균", f"{ev['panel_average']:.1f}/{coach.PANEL_MAX}")
    # st.table 은 긴 글을 칸 안에서 줄바꿈해서 가로 스크롤이 생기지 않는다 (st.dataframe 은 줄바꿈 옵션이 없음).
    st.table(
        [
            {
                "위원": m["role"],
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
        prev = coach.compare_previous(state.previous, ev, state.questions)
        st.subheader(f"지난 면접({prev['round']}회차 · {prev['date']})과 비교")
        st.metric("위원 평균", f"{prev['panel_after']:.1f}/{coach.PANEL_MAX}", delta=round(prev["panel_diff"], 1))
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

    new_answer = st.text_area("다시 답하기", height=180, key=f"retry_answer_{no}")
    if st.button("다시 채점", type="primary"):
        if not new_answer.strip():
            st.info("다시 쓴 답을 적은 뒤 눌러 주세요.")
        else:
            try:
                with st.spinner("다시 쓴 답을 채점하고 있어요..."):
                    raw = ask_json(
                        coach.build_retry(profile, question, before, last["weak"]),
                        new_answer.strip(),
                        RETRY_SCHEMA,
                        "retry",
                    )
            except LLMError as e:
                st.error(str(e))
            else:
                state.retries[no] = {"answer": new_answer.strip(), **coach.summarize_retry(raw)}
                st.rerun()

    result = state.retries.get(no)
    if result:
        diff = coach.compare(last["scores"], result["scores"])
        st.metric("후 점수", f"{diff['after']}/{coach.ANSWER_MAX}", delta=diff["diff"])
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
        try:
            with st.spinner("질문을 만들고 있어요..."):
                raw = ask_json(coach.build_last_suggest(profile), LAST_SUGGEST_INPUT, LAST_SUGGEST_SCHEMA, "last_suggest")
        except LLMError as e:
            st.error(str(e))
        else:
            state.last_suggest = coach.summarize_last_suggest(raw)
            st.rerun()
    if state.last_suggest:
        show_question_cards(state.last_suggest)

    st.divider()
    st.subheader("내 질문 다듬기")
    st.write("직접 쓴 질문을 회사 · 직무 · 성장 관점으로 다듬어 드려요.")
    my_question = st.text_area("면접관에게 할 내 질문", height=100, key="last_question_input")
    if st.button("질문 다듬기"):
        instructions = coach.build_last_question(profile)
        if not my_question.strip():
            st.info("면접관에게 할 질문을 적은 뒤 눌러 주세요.")
        elif not coach.is_prompt_ready(instructions):
            st.error("마지막 질문 프롬프트에 빈칸(___)이 있어요. prompts.py 의 LAST_QUESTION 글자 수를 채워 주세요.")
        else:
            try:
                with st.spinner("질문을 다듬고 있어요..."):
                    raw = ask_json(instructions, my_question.strip(), LAST_QUESTION_SCHEMA, "last_question")
            except LLMError as e:
                st.error(str(e))
            else:
                state.last_question = coach.summarize_last_question(raw)
                st.rerun()

    result = state.last_question
    if result:
        show_question_cards(result["questions"])
        if result["why"]:
            st.markdown(f"**원래 질문에서 빠진 것:** {result['why']}")


def show_report(ev: dict):
    try:
        precheck_items = coach.load_precheck()
    except (OSError, KeyError, ValueError):
        precheck_items = []
    report = coach.build_report(
        profile, state.questions, ev, state.retries, state.messages,
        state.last_suggest, state.last_question, state.previous, state.round,
        precheck_items, current_precheck(precheck_items),
    )
    file_name = coach.report_file_name(profile["company"], profile["job"], state.round)
    st.download_button(
        f"{file_name} 다운로드",
        data=report,
        file_name=file_name,
        mime="text/markdown",
        type="primary",
    )
    st.caption(
        "오른쪽 위 복사 아이콘으로 내용을 복사할 수 있어요. 점수는 모두 앱이 계산한 값이고, "
        "'AI 의견' 표시가 붙은 글은 AI가 쓴 거예요. 마지막 질문을 만들어 두면 리포트에 같이 들어가요. "
        "다음 면접 시작 화면에서 이 파일을 올리면 이어서 할 수 있어요 (맨 끝 주석은 이어 하기용 데이터예요)."
    )
    st.code(report, language="markdown")


CHAT_TAB, EVAL_TAB, RETRY_TAB = "💬 면접", "📊 평가", "🔁 재도전"
LAST_TAB, REPORT_TAB = "🙋 마지막 질문", "📄 리포트"

# 탭을 바꾸라는 표시가 있으면, 탭을 그리기 전에 열 탭을 정한다 (그린 뒤에는 바꿀 수 없음).
if state.pop("go_eval", False):
    state.view = EVAL_TAB

# 탭은 면접 시작부터 항상 같은 모양 · 같은 key 로 둔다. 화면 구조가 바뀌면
# Streamlit이 대화를 다시 그리면서 스크롤이 맨 위로 올라가기 때문이다.
chat_tab, eval_tab, retry_tab, last_tab, report_tab = st.tabs(
    [CHAT_TAB, EVAL_TAB, RETRY_TAB, LAST_TAB, REPORT_TAB], key="view", on_change="rerun"
)

with chat_tab:
    show_messages()
    live = st.container()  # 답을 보내는 동안의 내 답 · 로딩 · 에러가 대화 바로 아래에 나온다
    if state.stage == "done":
        st.success("질문 5개를 모두 마쳤어요. 수고하셨습니다.")
        if state.evaluation:
            st.info("평가가 끝났어요. 위의 📊 평가 탭에서 확인해 주세요.")
            if st.button("📊 평가 확인하기", type="primary"):
                state.go_eval = True
                st.rerun()
        elif st.button("위원 4명에게 평가받기", type="primary"):
            try:
                with st.spinner("위원 4명이 면접 기록을 보고 있어요..."):
                    raw = ask_json(
                        coach.build_evaluator(profile),
                        coach.format_record(state.questions, state.messages),
                        EVAL_SCHEMA,
                        "evaluation",
                    )
            except LLMError as e:
                st.error(str(e))
            else:
                state.evaluation = coach.summarize_evaluation(raw, state.questions)
                state.go_eval = True  # 평가가 끝나면 평가 탭으로 바로 이동
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

answer = st.chat_input("답을 적어 주세요")
if answer is not None:
    if not answer.strip():
        with live:
            st.info("답을 적은 뒤 보내 주세요.")
        st.stop()

    with live:
        with st.chat_message("user"):
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
