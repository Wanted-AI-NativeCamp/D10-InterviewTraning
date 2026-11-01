# D10 · AI 모의면접 코치

신입 지원자를 위한 **AI 모의면접 서비스**예요. Streamlit 화면에 OpenAI API를 붙여 만들었어요.
직군 · 회사 · 내 경험을 넣으면 면접 5문제(꼬리 질문 포함)를 진행하고, 평가 위원 4명이 채점한 뒤 재도전 · 암기 연습 · 리포트까지 이어져요.

> AI 네이티브 캠프 10일차 실습(`git-practice`)에서 시작해 디벨롭한 프로젝트예요.

### 브랜치

| 브랜치 | 상태 |
| --- | --- |
| `main` | 최신. UI 컨셉 적용 후 (로고 · 파비콘, Wanted Sans 글꼴, 화면 개선) |
| `before-design-concept` | UI 컨셉 적용 **전** 상태 (커밋 `247143e`, 10/29). Pretendard 글꼴, 로고 없음 |
| `before-mvp` | 서비스 방향성 재점검 **전** 상태 (11/01). 면접관 타입 태그(빠른 면접 진행 · 빠른 피드백 제공)까지 |
| `after-mvp` | `before-mvp` 에서 갈라져 서비스 방향성을 재점검하며 고치는 브랜치 |

이전 상태를 로컬에서 보려면 `git switch before-design-concept`, 다시 최신으로는 `git switch main`.

---

## 한눈에 보는 흐름

```
시작(직군 · 분야 · 회사 · 내 경험)
  → 브리핑(면접관 페르소나 · 사전 점검)
  → 면접 5문제 (질문마다 꼬리 질문 최대 1개)
  → 위원 4명 평가
  → 재도전(고친 답 비교) · 모의 결과 · 점검하기 · 암기
  → 리포트(.md) 다운로드 → 다음 회차에서 리포트를 다시 읽어 이어하기
```

면접이 끝나면 아래 탭으로 결과를 봐요.

| 탭 | 하는 일 |
| --- | --- |
| 1. 면접 | 면접 대화 기록 (`st.chat_message`) |
| 2. 평가 | 위원 4명 점수 · 기준별 점수 · 문장별 하이라이트 · 개선 전략 |
| 3. 재도전 | 점수가 낮은 답을 다시 써서 전후 비교 (질문당 최대 3회) |
| 4. 모의 결과 | 종합 판결 (합격 · 합격 후보 · 재도전 필요) |
| 5. 점검하기 | 종합 점검 · 회사 사전 정보 탐색 체크리스트 · 마지막에 할 질문 |
| 6. 암기 | 뼈대 보기 → 빈칸 채우기 → 실전 시뮬레이션, 말하기 시간 재기 |

---

## 파일 구조

```
git-practice/                  ← 저장소 루트
├── README.md                  ← 지금 이 문서
└── d10-interview/             ← 앱 전체가 여기에 있어요
    ├── app.py                 ← Streamlit 화면 (가장 큰 파일, 약 3,300줄)
    ├── coach.py               ← 계산 · 규칙 · 리포트 (AI 호출 없음)
    ├── prompts.py             ← 프롬프트 문장 + JSON 스키마
    ├── llm.py                 ← OpenAI 호출 (유일한 한 곳)
    ├── requirements.txt       ← 필요한 파이썬 패키지
    ├── CLAUDE.md              ← Claude Code가 지키는 프로젝트 규칙
    ├── .env.example           ← 환경 변수 이름만 (값은 .env 에)
    ├── .gitignore
    ├── .streamlit/
    │   └── config.toml        ← 테마 (몽타주 디자인 시스템 색 · Wanted Sans 글꼴)
    ├── assets/
    │   ├── logo.png           ← 로고 (밝은 테마)
    │   ├── logo_dark.png      ← 로고 (어두운 테마)
    │   └── favicon.png        ← 브라우저 탭 아이콘
    └── data/
        ├── questions.csv              ← 질문 은행 (103문항)
        ├── 사전탐색_체크리스트.csv     ← 회사 · 직무 사전 조사 항목
        ├── 암기전략.md                 ← 암기 탭 안내 글
        ├── 평가기준_근거.md            ← "왜 위원 4명이 같은 기준으로 보나" 설명
        └── mock_perfect.json          ← 개발용 만점 모의 데이터 (DEV_MOCK=1 일 때만)
```

Git에 올라가지 않는 것: `.env`(API 키), `__pycache__/`, `delete/`, `.claude/settings.local.json`

### 파일 사이의 관계

```
app.py ──▶ coach.py ──▶ prompts.py
  │           │
  │           └──▶ data/*.csv · *.md · *.json
  └──▶ llm.py ──▶ OpenAI API
```

- **화면(`app.py`)** 은 `coach.py`로 프롬프트를 채우고, `llm.py`의 `ask_json()`으로 AI를 불러요.
- **AI는 판단만** 하고, 점수 합계 · 평균 · 전후 차이 · 질문 개수 · 꼬리 질문 횟수는 **코드(`coach.py`)가 계산**해요.

### 파일별 역할

| 파일 | 하는 일 | 하지 않는 일 |
| --- | --- | --- |
| `app.py` | 화면, 단계 전환(`start` → `briefing` → `interview` → `done`), 탭, 다이얼로그, `st.session_state` 관리 | 프롬프트 문자열 · API 직접 호출 |
| `coach.py` | 질문 고르기, 점수 자르기(clamp) · 합계, 판결, 재도전 비교, 암기 도구(빈칸 · 회상률), 리포트 만들기 · 읽기 | API 호출 |
| `prompts.py` | 면접관 페르소나, 분야 설명, 프롬프트(`INTERVIEWER`, `EVALUATOR`, `RETRY`, `STRATEGY`, `HIGHLIGHT`, `LAST_QUESTION` 등)와 각 JSON 스키마 | 함수 · API 호출 |
| `llm.py` | `ask_json(instructions, user_input, schema, name)` 하나. strict JSON 스키마로 응답을 받고, 에러를 한국어 한 줄(`LLMError`)로 바꿈 | 화면 코드 |

### `coach.py` 주요 숫자 (여기만 바꾸면 규칙이 바뀌어요)

| 상수 | 값 | 뜻 |
| --- | --- | --- |
| `TOTAL_QUESTIONS` | 5 | 면접 질문 수 |
| `MAX_FOLLOW_UPS` | 1 | 질문당 꼬리 질문 최대 개수 |
| `CRITERIA` | 4개 | 구체성 · 직무 연관 · 구조 · 근거/검증 (각 0~5점, 답 하나 20점) |
| `PANEL_MAX` | 10 | 위원 점수 상한 (0~10) |
| `REWRITE_BELOW` | 14 | 이 점수 미만인 답만 고친 답을 보여 줌 |
| `PASS_TOTAL` / `PASS_PANEL` | 90 / 9.0 | 합격선 (종합 100점 · 위원 평균) |
| `CANDIDATE_TOTAL` / `CANDIDATE_PANEL` | 70 / 7.0 | 합격 후보선 |
| `MAX_RETRIES` | 3 | 질문당 재도전 횟수 |
| `MAX_ANSWER_CHARS` | 1500 | 답 한 개 최대 글자 수 |

### 질문 은행 (`data/questions.csv`)

칸: `직군, 분야, 유형, 질문, 보는 점, 만점 예시, 회사 키워드`

| 직군 | 분야 |
| --- | --- |
| 공통 | 공통 |
| 디자인 | 공통 · 헬스케어 · 핀테크/금융 · 커머스 · 에듀테크 · 모빌리티/여행 · 콘텐츠/미디어 · B2B/SaaS · 게임 |
| 개발 · PO · 마케팅 | 공통 |

---

## 실행하기

```bash
cd d10-interview
pip install -r requirements.txt
cp .env.example .env      # .env 를 열어 값을 채워요
streamlit run app.py
```

### 환경 변수 (`.env`)

| 이름 | 필수 | 설명 |
| --- | --- | --- |
| `OPENAI_API_KEY` | ✅ | OpenAI API 키 |
| `OPENAI_MODEL` | | 비우면 `gpt-6-luna` |
| `FEEDBACK_SURVEY_URL` | | 다 마친 뒤 보여 줄 설문 링크 (`https://`로 시작) |
| `DEV_MOCK` | | `1`이면 시작 화면에 "만점 모의 데이터" 버튼 (개발용, 배포에는 넣지 않기) |

배포할 때는 `.env` 대신 **Streamlit Secrets**에 같은 이름으로 넣어요.

---

## 코드를 고칠 때 참고

- 프롬프트 문장은 `prompts.py`에만 있어요. 화면 글은 `app.py`, 숫자 규칙은 `coach.py`.
- OpenAI 호출은 `llm.py` 한 곳뿐이에요. (`OpenAI(` 로 검색하면 한 군데만 나와야 해요)
- 지원자가 쓰지 않은 경험 · 숫자는 AI가 지어내지 않고 `[확인 필요: ○○]`로 남겨요.
- 자세한 개발 규칙은 [`d10-interview/CLAUDE.md`](d10-interview/CLAUDE.md)에 있어요.
