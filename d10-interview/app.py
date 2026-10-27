# Streamlit 화면만. 프롬프트는 prompts.py, AI 호출은 llm.py, 계산은 coach.py.
import streamlit as st

import coach
from llm import LLMError, ask_json
from prompts import EVAL_SCHEMA, INTERVIEWER_SCHEMA, PERSONAS

st.set_page_config(page_title="AI 면접 코치", page_icon="🎤")


def reset():
    st.session_state.clear()
    st.session_state.stage = "start"


if "stage" not in st.session_state:
    reset()

state = st.session_state


def question_message(index: int) -> dict:
    text = f"**질문 {index + 1}/{coach.TOTAL_QUESTIONS}.** {state.questions[index]['question']}"
    return {"role": "assistant", "content": text, "q": index, "kind": "question"}


# ── 사이드바 상태창 ──────────────────────────────────────────
with st.sidebar:
    st.header("상태창")
    if state.stage == "start":
        st.caption("면접을 시작하면 진행 상황이 보여요.")
    else:
        answered = state.q_index
        current = min(answered + 1, coach.TOTAL_QUESTIONS)
        st.progress(answered / coach.TOTAL_QUESTIONS, text=f"질문 {current}/{coach.TOTAL_QUESTIONS}")
        st.metric("면접관이 본 이해도", "-" if state.understanding is None else f"{state.understanding}/100")
        if state.get("evaluation"):
            ev = state.evaluation
            st.metric("위원 평균", f"{ev['panel_average']:.1f}/{coach.PANEL_MAX}")
    if st.button("처음부터 다시", width="stretch"):
        reset()
        st.rerun()


# ── 시작 화면 ───────────────────────────────────────────────
if state.stage == "start":
    st.title("AI 면접 코치")
    st.write("신입 모의면접이에요. 질문 5개와 꼬리 질문으로 진행해요.")

    with st.form("start"):
        name = st.text_input("이름")
        job = st.selectbox("지원 직군", coach.JOBS)
        company = st.text_input("회사")
        company_desc = st.text_input("회사 설명", help="어떤 서비스를 하는 회사인지 한 줄로 적어 주세요.")
        experience = st.text_area(
            "내 경험",
            height=150,
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
        elif not PERSONAS[job]:
            st.error(f"'{job}' 면접관 페르소나가 아직 없어요. prompts.py 의 PERSONAS 에 문장을 넣어 주세요.")
        else:
            try:
                questions = coach.pick_questions(coach.load_questions(), job)
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
                state.q_index = 0
                state.follow_ups = 0
                state.understanding = None
                state.evaluation = None
                state.messages = [
                    {"role": "assistant", "content": f"{name} 님, 면접을 시작하겠습니다."},
                    question_message(0),
                ]
                state.stage = "interview"
                st.rerun()
    st.stop()


# ── 면접 화면 ───────────────────────────────────────────────
profile = state.profile
st.title(f"{profile['company']} · {profile['job']} 신입 면접")

def show_messages():
    for message in state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def show_evaluation(ev: dict):
    st.metric("위원 평균", f"{ev['panel_average']:.1f}/{coach.PANEL_MAX}")
    st.dataframe(
        [
            {"위원": m["role"], "뽑지 말아야 할 이유": m["against"], "좋은 점": m["good"], "점수": m["score"]}
            for m in ev["panel"]
        ],
        hide_index=True,
    )
    st.markdown(f"**판단이 갈린 곳:** {ev['conflict']}")
    st.markdown(f"**모두 같은 판단:** {ev['agree']}")

    st.subheader("답변별 점수")
    for a in ev["answers"]:
        with st.expander(f"질문 {a['no']} · {a['score']}/{coach.ANSWER_MAX}점", expanded=a["needs_rewrite"]):
            st.caption(a["question"])
            st.write(" · ".join(f"{name} {a['scores'][key]}" for key, name in coach.CRITERIA.items()))
            st.markdown(f"**가장 약한 점:** {a['weak']}")
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


CHAT_TAB, EVAL_TAB = "💬 면접", "📊 평가"

# 탭을 바꾸라는 표시가 있으면, 탭을 그리기 전에 열 탭을 정한다 (그린 뒤에는 바꿀 수 없음).
if state.pop("go_eval", False):
    state.view = EVAL_TAB

# 탭은 면접 시작부터 항상 같은 모양 · 같은 key 로 둔다. 화면 구조가 바뀌면
# Streamlit이 대화를 다시 그리면서 스크롤이 맨 위로 올라가기 때문이다.
chat_tab, eval_tab = st.tabs([CHAT_TAB, EVAL_TAB], key="view", on_change="rerun")

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

if state.stage == "done":
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
