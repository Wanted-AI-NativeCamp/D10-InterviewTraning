# Streamlit 화면만. 프롬프트는 prompts.py, AI 호출은 llm.py, 계산은 coach.py.
import streamlit as st

import coach
from llm import LLMError, ask_json
from prompts import INTERVIEWER_SCHEMA, PERSONAS

st.set_page_config(page_title="AI 면접 코치", page_icon="🎤")


def reset():
    st.session_state.clear()
    st.session_state.stage = "start"


if "stage" not in st.session_state:
    reset()

state = st.session_state


def question_message(index: int) -> str:
    return f"**질문 {index + 1}/{coach.TOTAL_QUESTIONS}.** {state.questions[index]['question']}"


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
    if st.button("처음부터 다시", width="stretch"):
        reset()
        st.rerun()


# ── 시작 화면 ───────────────────────────────────────────────
if state.stage == "start":
    st.title("AI 면접 코치")
    st.write("클래스로 신입 모의면접이에요. 질문 5개와 꼬리 질문으로 진행해요.")

    with st.form("start"):
        name = st.text_input("이름")
        job = st.selectbox("지원 직군", coach.JOBS)
        company = st.text_input("회사", value="클래스로")
        experience = st.text_area(
            "내 경험",
            height=150,
            help=f"면접관이 참고할 경험을 {coach.MIN_EXPERIENCE_CHARS}자 이상 적어 주세요.",
        )
        started = st.form_submit_button("면접 시작하기", type="primary")

    if started:
        name, company, experience = name.strip(), company.strip(), experience.strip()
        if not name or not company or not experience:
            st.warning("이름 · 회사 · 내 경험을 모두 적어 주세요.")
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
                state.profile = {"name": name, "job": job, "company": company, "experience": experience}
                state.questions = questions
                state.q_index = 0
                state.follow_ups = 0
                state.understanding = None
                state.messages = [
                    {"role": "assistant", "content": f"{name} 님, 면접을 시작하겠습니다."},
                    {"role": "assistant", "content": question_message(0)},
                ]
                state.stage = "interview"
                st.rerun()
    st.stop()


# ── 면접 화면 ───────────────────────────────────────────────
profile = state.profile
st.title(f"{profile['company']} · {profile['job']} 신입 면접")

for message in state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if state.stage == "done":
    st.success("질문 5개를 모두 마쳤어요. 수고하셨습니다.")
    st.stop()

answer = st.chat_input("답을 적어 주세요")
if answer is not None:
    if not answer.strip():
        st.info("답을 적은 뒤 보내 주세요.")
        st.stop()

    with st.chat_message("user"):
        st.markdown(answer)

    question = state.questions[state.q_index]
    instructions = coach.build_interviewer(
        profile["job"], profile["company"], profile["experience"], question
    )
    transcript = coach.format_transcript(state.messages + [{"role": "user", "content": answer}])

    try:
        with st.spinner("면접관이 답을 읽고 있어요..."):
            result = ask_json(instructions, transcript, INTERVIEWER_SCHEMA, "interviewer")
    except LLMError as e:
        st.error(str(e))
        st.stop()

    state.messages.append({"role": "user", "content": answer})
    state.understanding = coach.clamp(result.get("understanding"), 0, 100)
    reply = str(result.get("reply", "")).strip()
    ai_wants_follow_up = bool(result.get("follow_up"))

    if coach.should_follow_up(ai_wants_follow_up, state.follow_ups):
        # 꼬리 질문: 같은 질문에 머문다.
        state.follow_ups += 1
        state.messages.append({"role": "assistant", "content": reply})
    else:
        # AI가 꼬리 질문을 더 원해도 한도를 넘으면 그 문장(질문)은 보여 주지 않고 넘어간다.
        if reply and not ai_wants_follow_up:
            state.messages.append({"role": "assistant", "content": reply})
        state.q_index += 1
        state.follow_ups = 0
        if state.q_index < coach.TOTAL_QUESTIONS:
            state.messages.append({"role": "assistant", "content": question_message(state.q_index)})
        else:
            state.messages.append({"role": "assistant", "content": "면접을 마치겠습니다."})
            state.stage = "done"
    st.rerun()
