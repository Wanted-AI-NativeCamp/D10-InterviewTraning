# 역전 취업 코칭 — AI 모의면접 코치

신입 지원자를 위한 AI 모의면접 서비스예요. Streamlit 화면에 OpenAI API를 붙여 만들었어요.

**직군 · 회사 고르기 → 면접 5문제 (질문마다 꼬리 질문 최대 1개) → 평가 위원 4명 채점 → 낮은 답 재도전 → Markdown 파일로 저장 · 복원**

---

## 1. 내 컴퓨터에서 실행하기

필요한 것: Python 3.10 이상 (3.12에서 확인), OpenAI API 키

```bash
git clone https://github.com/Wanted-AI-NativeCamp/D10-InterviewTraning.git
cd D10-InterviewTraning/d10-interview

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

`.env` 를 열어 키를 넣어요.

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-6-luna
```

```bash
streamlit run app.py             # 브라우저에서 http://localhost:8501
```

| 환경 변수 | 필수 | 설명 |
| --- | --- | --- |
| `OPENAI_API_KEY` | ✅ | OpenAI API 키 |
| `OPENAI_MODEL` | | 비우면 `gpt-6-luna` |
| `FEEDBACK_SURVEY_URL` | | 면접을 마친 뒤 보여 줄 설문 링크 |
| `DEV_MOCK` | | `1` 이면 AI 없이 만점 모의 데이터를 여는 개발용 버튼 (배포에는 넣지 않기) |
| `ERROR_LOG_FILE_ENABLED` | | `true` 이면 오류 기록을 `logs/errors.jsonl` 에도 남김 |

`.env` 는 Git에 올라가지 않아요. 키는 절대 커밋하지 마세요.

## 2. 배포하기 (Streamlit Community Cloud)

1. 이 저장소를 내 GitHub 계정으로 Fork 해요.
2. [share.streamlit.io](https://share.streamlit.io) → **Create app**
   - Branch: `main`
   - Main file path: `d10-interview/app.py`
   - Advanced settings → Python 3.12
3. **Secrets** 에 `.env` 와 같은 이름으로 넣어요.
   ```toml
   OPENAI_API_KEY = "sk-..."
   OPENAI_MODEL = "gpt-6-luna"
   ```
4. Deploy. 패키지는 `d10-interview/requirements.txt` 를 자동으로 읽어요.

서버에 데이터베이스가 없어요. 면접 기록은 브라우저 세션에만 있고, 새로고침하면 사라지니 **[데이터 저장하기]** 로 Markdown 파일을 받아 두고 다음에 **[Markdown 복원]** 으로 이어 가요.

## 3. 테스트하기 (API 키 · 비용 없이)

```bash
cd d10-interview
pip install -r requirements-dev.txt
python -m unittest discover tests    # Windows 한글 출력: PYTHONIOENCODING=utf-8 을 앞에 붙여요
```

테스트는 실제 OpenAI를 부르지 않아요. 가짜 AI가 실제와 같은 JSON 형식으로 답해서, 면접 → 평가 → 재도전 → 저장 · 복원 흐름을 화면 단위까지 확인해요 (약 3분).

---

## 4. 이렇게 만들었어요 — 핵심 원칙

비슷한 AI 코칭 서비스를 만든다면 이 다섯 가지만 지키면 돼요.

### ① AI는 판단, 코드는 계산
AI에게는 "이 답이 구체적인가", "다음에 무엇을 물을까" 같은 **판단**만 맡겨요.
질문 개수(5), 꼬리 질문 횟수(최대 1), 점수 합계 · 평균 · 전후 차이, 점수 범위(0~5 · 0~10) 자르기는 **코드가 정해요**.
AI가 "하나 더 묻자"고 해도 코드가 막고, AI가 쓴 합계는 쓰지 않아요. 그래서 결과가 매번 흔들리지 않아요.

### ② AI 출력은 JSON 스키마(strict)로만 받기
모든 요청에 응답 형식을 JSON 스키마로 정해 줘요 (`response_format` · `strict: true`).
글을 받아서 잘라 쓰지 않으니 화면이 깨지지 않고, 받은 값은 한 번 더 검사해서 범위를 벗어나면 보정해요.

### ③ 역할별로 파일을 나누기

| 파일 | 하는 일 |
| --- | --- |
| `prompts.py` | 프롬프트 문장과 JSON 스키마만 |
| `llm.py` | OpenAI 호출은 여기 **한 곳**뿐 (`ask_json`) |
| `coach.py` | 질문 고르기 · 점수 계산 · 저장 파일 만들기 · 읽기 (AI 없음) |
| `app.py` | Streamlit 화면만 |
| `data/questions.csv` | 질문 은행 (칸: 직군 · 분야 · 유형 · 질문 · 보는 점 …) |

프롬프트를 고칠 땐 `prompts.py`, 질문을 늘릴 땐 CSV에 줄만 추가하면 돼요. 다른 직군 · 분야로 바꾸기도 쉬워요.

### ④ 지어내지 않게 하기
지원자가 쓰지 않은 경험 · 숫자 · 회사 정보는 AI가 만들지 않고 `[확인 필요: ○○]` 로 남기게 해요.
평가 위원에게는 질문별 '보는 점'을 주되, 키워드가 있는지만으로 판단하지 않게 해요.

### ⑤ 가짜 AI로 먼저 고정하고 고치기
기능을 바꾸기 전에 지금 동작을 테스트로 고정해 둬요. `llm.ask_json` 을 가짜로 바꾸면 비용 없이 같은 흐름을 몇 번이고 돌릴 수 있어요.
오류 기록에는 답변 전문 · 개인정보 · API 키 · AI 응답 전문을 남기지 않아요.

---

더 자세한 규칙은 [`d10-interview/CLAUDE.md`](d10-interview/CLAUDE.md), 기획 문서는 [`d10-interview/prd/`](d10-interview/prd/) 에 있어요.
