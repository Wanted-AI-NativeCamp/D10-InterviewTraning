# 역전 취업 코칭 MVP1 — 개발 프롬프트

> **사용법 (사람이 읽는 부분)**
> 1. 빈 폴더를 만들고 그 안에서 Claude Code(또는 다른 AI 코딩 도구)를 연다.
> 2. 이 파일을 그 폴더에 넣고 이렇게 말한다: **"MVP1_BUILD_PROMPT.md 를 끝까지 읽고, 1단계부터 순서대로 진행해 줘. 단계마다 완료 조건을 확인하고 나에게 보고한 뒤 다음 단계로 가."**
> 3. 단계마다 보고를 읽고 화면을 직접 확인한 뒤 "다음 단계 진행해"라고 답한다.
>
> OpenAI API 키는 마지막 실제 실행 때만 필요하다. 개발 · 테스트는 가짜 AI(모의 응답)로 한다.

---

## 0. AI 코딩 도구에게 — 역할과 작업 규칙

너는 Python · Streamlit 개발자다. 이 문서 하나만 보고 **"역전 취업 코칭" MVP1** 을 빈 폴더에서 처음부터 만든다. 원본 저장소는 없다.

작업 규칙:
1. **12장의 단계 순서대로** 만든다. 한 단계가 끝나면 완료 조건을 직접 확인하고, 만든 파일 · 확인 결과 · 남은 문제를 사용자에게 보고한 뒤 **사용자 승인을 받고** 다음 단계로 간다.
2. **이 문서에 없는 기능을 더하지 않는다.** 15장 "확인 필요 항목"과 이 문서에 정하지 않은 부분은 임의로 정하지 말고 사용자에게 묻는다.
3. **AI 프롬프트 문장(부록 A)은 글자 하나도 바꾸지 않는다.** 바꾸고 싶으면 제안만 한다.
4. **AI는 판단, 코드는 계산.** 질문 수 · 순서 · 꼬리 질문 한도 · 점수 합계 · 평균 · 판정 · 범위 보정은 코드가 한다. AI가 쓴 합계는 쓰지 않는다.
5. **실제 OpenAI API 를 부르지 않는다.** 개발 · 테스트는 11장의 가짜 AI 로 한다. 실제 호출은 13장에서 사용자가 키를 넣고 직접 실행할 때만.
6. **API 키는 코드 · 화면 · 터미널 · 로그 · Git 에 절대 남기지 않는다.** `.env`(로컬) 또는 Streamlit Secrets(배포)로만 읽는다.
7. 화면 문구는 이 문서의 한국어 문구를 그대로 쓴다. 오류는 화면에 한국어 한 줄로 보여 준다.
8. 테스트를 통과시키려고 규칙을 바꾸거나 오류를 예외 처리로 숨기지 않는다. 확인하지 않은 것을 "완료"라고 보고하지 않는다.

---

## 1. 만들 것 — MVP1 한 줄 요약

신입 지원자를 위한 **AI 모의면접 코치** 웹앱 (Streamlit + OpenAI API, 서버 DB 없음).

**흐름:** 홈 → 새 면접 설정(회사 · 직군 · 면접 유형 · 산업 분야 · 내 경험, 면접관 자동 배정) → 면접 5문제(질문마다 꼬리 질문 최대 1개) → 평가 위원 4명 채점 → 평가 · 면접 기록 확인 → 낮은 답 재도전 · 재채점(형광펜 · 전략 가이드 보조) → Markdown 파일로 저장 → 다음에 복원해서 이어 하기.

### 1.1 MVP1 에 포함 (이것만 만든다)
| 영역 | 기능 |
|---|---|
| 시작 · 홈 | 시작(스플래시) 화면, 랜덤 닉네임 · 수정, 진행 중 면접 · 나의 면접 현황 3카드 · 최근 면접 · 빠른 시작 카드 |
| 면접 설정 | 회사 이름 · 설명(선택), 직군 4개, 공통 면접 / 분야별 면접, 산업 분야, 직군별 면접관 **자동 배정**(소개 카드), 내 경험(선택), 같은 회사 · 직군 기록이 있으면 질문 출제 방식(새로운 문제만 · 섞어서 · 똑같은 질문) |
| 면접 진행 | 채팅 화면, 질문 5개, 조건부 꼬리 질문(질문당 최대 1개 · 코드 강제), 이해도 0~100, 상태창(사이드바), 처음부터 다시, AI 실패 시 답 보관 · 다시 시도 · 답 수정 |
| 평가 | 평가 위원 4명(반론 먼저 · 0~10점), 답변별 기준 4개(0~5점) · 가장 약한 점, 종합 점수 · 위원 평균 · 판정(코드 계산), 모의 결과 메일 연출, 만점 예시 답안(질문 은행 데이터) |
| 기록 | 면접 데이터 목록(회사 → 직군), 회차별 평가 기록 · 면접 기록 · 전체 대화 · 회차 종합 차트 |
| 재도전 | 역전의 실마리(가장 낮은 답 2개), 질문 선택 · 다시 답하기 · 다시 채점(횟수 제한 없음 · 최고 점수 반영), 위원 코치 피드백(고정 문장), 형광펜 · 전략 가이드(누를 때만 AI 호출) |
| 저장 · 복원 | 데이터 저장하기(Markdown v2 한 파일 · 개인정보 확인 체크), Markdown 복원(여러 파일 · 같은 회차는 건너뜀) |
| 오류 · 상태 | AI 오류 분류 · 한국어 안내, 응답 검증 · 자동 재요청 1회, 오류 기록(민감정보 제외), 미저장 경고 |

### 1.2 만들지 않는 것
마지막에 할 질문(역질문) 추천 · 다듬기, 암기 · 말하기 연습, 사전 정보 탐색 체크리스트, 면접관 직접 선택 · 피드백형 면접관, 회차 리포트 단독 다운로드, 설문 링크, 경험 카드 · 퀘스트 · 경험 추천(2차 범위), 로그인 · 서버 DB · 영구 저장, AI 로 질문 새로 생성.

---

## 2. 기술 스택 · 폴더 구조 · 환경

### 2.1 스택
- Python **3.12 권장** (3.10 이상), Streamlit **1.66 이상**, `openai`(Responses API), `python-dotenv`, `pandas`. 테스트용 `jsonschema>=4.0,<5`, `numpy`.
- 테스트는 표준 `unittest` + `streamlit.testing.v1.AppTest`.

### 2.2 폴더 구조 (파일마다 역할을 지킨다)
```
interview-coach/
├─ app.py              # Streamlit 화면만 (프롬프트 문자열 · API 직접 호출 금지)
├─ coach.py            # 계산 · 규칙 · 저장 파일 만들기/읽기 (AI 호출 없음)
├─ llm.py              # OpenAI 호출은 여기 한 곳: ask_json()
├─ prompts.py          # 프롬프트 문자열 · JSON 스키마만 (부록 A 그대로)
├─ error_log.py        # 오류 기록 (민감정보 차단)
├─ data/
│  ├─ questions.csv    # 질문 은행 193개 (부록 C 그대로, UTF-8 BOM)
│  └─ 평가기준_근거.md  # 평가 기준 근거 안내 (부록 E 그대로)
├─ assets/             # logo.png · logo_dark.png · favicon.png (15장 확인 필요)
├─ .streamlit/config.toml   # 테마 (부록 B 그대로)
├─ tests/
│  ├─ fake_llm.py           # 가짜 ask_json
│  ├─ fixtures/ai/*.json    # 모의 응답 (부록 D 그대로)
│  └─ test_*.py
├─ requirements.txt · requirements-dev.txt
├─ .env.example · .gitignore
```

### 2.3 환경 파일
- `requirements.txt`: `streamlit>=1.66` · `openai` · `python-dotenv` · `pandas`
- `requirements-dev.txt`: `-r requirements.txt` · `jsonschema>=4.0,<5` · `numpy>=1.25,<3`
- `.env.example` (이름만, 값 없음):
  ```
  OPENAI_API_KEY=
  OPENAI_MODEL=
  ERROR_LOG_FILE_ENABLED=false
  ```
- `.gitignore`: `.env`, `.streamlit/secrets.toml`, `__pycache__/`, `logs/`, `.venv/`
- 키 읽기: `llm.py` 에서 `load_dotenv()` 후 `os.getenv("OPENAI_API_KEY")`. Streamlit Community Cloud 는 Secrets 최상위 값을 환경 변수로도 넣어 주므로 같은 코드로 동작한다.
- 모델: `os.getenv("OPENAI_MODEL") or DEFAULT_MODEL` (15장 확인 필요: 기본 모델 이름).

---

## 3. 데이터 모델

### 3.1 질문 은행 `data/questions.csv`
- 칸: `직군, 분야, 유형, 질문, 보는 점, 만점 예시, 회사 키워드, 질문 ID` · `pd.read_csv(..., encoding="utf-8-sig")`
- 직군: `공통`(모든 직군) · `개발` · `디자인` · `PO` · `마케팅`. 분야: `공통` 또는 산업 분야 8개(`FIELDS` 키와 같은 글). 유형: `공통`(직군=공통 행) · `직무` · `경험` · `상황`.
- `보는 점`: 이 질문으로 확인하려는 것. 면접관 · 평가 · 형광펜 지시문에 들어간다.
- `만점 예시`: 공통 4행 + 디자인 75행에만 있다. 화면에서 AI 없이 보여 준다.
- `회사 키워드`: `/` 로 나눈 단어. 비어 있으면 모든 회사, 있으면 `회사 이름 + " " + 회사 설명` 에 단어 하나라도 부분 문자열로 들어 있을 때만 출제.
- 행 → 질문 dict: `{type, question, point, field, example, question_id}` (분야 칸이 비면 "공통", 만점 예시 · 회사 키워드가 비면 "").
- 읽기 실패 시 화면: `질문 은행(data/questions.csv)을 읽지 못했어요.`

### 3.2 상수
| 이름 | 값 | 이름 | 값 |
|---|---|---|---|
| TOTAL_QUESTIONS | 5 | MAX_FOLLOW_UPS | 1 |
| CRITERIA | specific=구체성, relevance=직무 연관, structure=구조, evidence=근거 · 검증 (이 순서) | CRITERION_MAX | 5 |
| ANSWER_MAX | 20 | TOTAL_MAX | 100 |
| PANEL_MAX | 10 | REWRITE_BELOW | 14 |
| PASS_TOTAL / PASS_PANEL | 90 / 9.0 | CANDIDATE_TOTAL / CANDIDATE_PANEL | 70 / 7.0 |
| MAX_CLUES | 2 | MAX_TIPS_PER_CRITERION | 2 |
| MIX_KEEP | 2 | MAX_ROUND | 999 |
| MAX_ANSWER_CHARS | 1500 | MAX_EXPERIENCE_CHARS | 1000 |
| 회사 이름 / 회사 설명 / 닉네임 최대 | 40 / 100 / 20자 | DEFAULT_FIELD | "공통" |
| JOBS | 개발, 디자인, PO, 마케팅 (PERSONAS 키 순서) | OTHER_GROUP / NO_COMPANY | "기타" / "회사 미지정" |
| PANEL_ROLES | 실무 전문가, 논리 분석가, 커뮤니케이션 전문가, 채용 담당자 | 시간대 기본 | Asia/Seoul |

### 3.3 회차(round) 레코드 — 기록 보관함 `store_rounds` 의 원소
| 칸 | 내용 |
|---|---|
| `round_id` | `"r" + uuid4().hex[:16]` |
| `round_number` | 같은 (company_key, job) 그룹 안 최대 번호 + 1 (최대 999). 공통 · 분야별 면접이 번호를 같이 쓴다 |
| `company_key` | 회사 이름 앞뒤 공백만 제거. 빈 값이면 `None` (화면 그룹명 "기타") |
| `company_id` | `"c" + sha1(company_key)[:12]`, key 가 None 이면 None |
| `company_name` · `company_desc` | 회사 이름(=key 또는 "") · 회사 설명(strip) |
| `job` · `field` | 직군 · 분야("공통" 또는 산업 분야) |
| `interview_type` | field == "공통" 이면 `"common"`, 아니면 `"field"` |
| `question_mode` | `"new"` · `"mix"` · `"same"` |
| `date` | ISO `YYYY-MM-DD` (브라우저 시간대 `st.context.timezone`, 실패 시 Asia/Seoul) |
| `nickname` · `experience` | 닉네임 · 내 경험 원문 |
| `questions` | 질문 dict 5개 |
| `stage` | `"interview"`(진행 중) → `"done"`(5문제 끝). 평가 완료 여부는 `evaluation` 유무로 판단 |
| 작업 칸 | `messages`, `evaluation`, `retries`, `retry_history`, `retry_counts`, `retry_pending`, `retry_unreadable`, `evaluation_unreadable`, `understanding`, `clue_set`, `clue_round`, `verdict_open`, `q_index`, `follow_ups`, `pending_answer` |

- **면접을 시작하는 순간 회차를 `store_rounds` 에 추가**한다(stage="interview"). 세션 최상위 키(`messages`, `q_index` …)는 **지금 펼친 회차의 사본**이다. `sync_active()` 로 매 실행 시작 · 회차 전환 전 · 저장 전에 세션 → 레코드로 되돌려 쓰고, `load_round(id)` 로 레코드 → 세션에 펼친다(회차별 위젯 키는 지운 뒤 펼침).
- 회차 상태 글: `면접 진행 중`(stage=interview) / `평가 전`(done, 평가 없음) / `평가 완료`(done, 평가 있음).

### 3.4 메시지 · 평가 · 재도전 형태
- 메시지: `{"role": "assistant"|"user", "content": str, "q": 0~4 또는 없음, "kind": "question" 또는 없음}`
  - 시작 인사 `"{닉네임} 님, 면접을 시작하겠습니다."` (q 없음), 질문 메시지 `"**질문 {i}/5.**{태그} {질문}"` (q=i-1, kind="question", 분야 질문이면 태그 ` :material/explore: **{분야} 질문**`), 꼬리 질문 · 반응(q=i-1), 지원자 답(q=i-1), 끝 `"면접을 마치겠습니다."` (q 없음).
- 저장되는 평가(검증 · 보정 후): `{panel: [{role, against, good, score}] ×4 (PANEL_ROLES 순서), panel_average, conflict, agree, answers: [{no, question(질문 은행 글), scores{4기준}, score(합 0~20), weak, rewrite, check[], needs_rewrite}], next[]}`
- 재도전 시도(attempt): `{answer, scores{4기준}, score, weak, attempt_id}` — `attempt_id = "q{no}-a{n}"`, n 은 그 질문에서 쓴 최대 번호 + 1.
- `retry_history[no]` = 모든 시도 목록, `retries[no]` = 반영된 최고 시도(없으면 키 없음), `retry_counts[no]` = 시도 수, `retry_pending[no]` = 채점 못 한 답.

### 3.5 세션 전역 키 (`st.session_state`)
`page`(start/home/setup/interview/coaching/restore), `nickname`, `store_rounds`, `active_round_id`, `saved_fingerprint`, `stage`, `questions`, `round`, `coach_group`({key, job} 또는 None), `lnb` · `lnb_choice` · `lnb_target`, 이동 예약(`go_tab`, `go_retry_no`), 스크롤 플래그, `splash_done`, `nickname_editing`, `notice`, `restart_pending`, `eval_running`, `highlights` · `strategies`(세션 캐시 · 저장 안 함), `restore_results`, 설정 위젯(`f_company`, `f_company_desc`, `f_job`, `f_type`, `f_field`, `f_experience`, `f_mode`, `f_same_how`, `f_same_round`), `error_session_id`.
- 처음 접속(`"page" not in state`) → 초기화: `page="start"`, `store_rounds=[]`, 새 닉네임, `saved_fingerprint=None`.
- **브라우저 새로고침 = 모든 기록 사라짐**(의도된 동작). 다시 이어 하려면 저장 파일을 복원한다.

---

## 4. 기능 규칙 (coach.py — AI 없이 코드로)

### 4.1 질문 5개 고르기 `pick_questions(bank, job, field, company_text, avoid)`
1. 회사 키워드로 은행을 거른다.
2. 슬롯 5개를 이 순서로, 슬롯마다 1개 무작위:
   | # | 후보 |
   |---|---|
   | 1 | 직군=공통 이고 질문에 "자기소개" 포함 → **첫 질문은 항상 "1분 동안 자기소개를 해 주세요."** |
   | 2 | 직군=공통 이고 "자기소개" 미포함 |
   | 3 · 4 · 5 | 직군=job 이고 유형=직무 · 경험 · 상황 |
3. 같은 회차에서 이미 뽑은 질문은 제외. 분야별 면접이면 3~5번은 `분야==field` 행에서 고르고, 그 분야에 그 유형이 없으면 `분야==공통` 행에서 고른다. 공통 면접이면 `분야==공통` 행. 후보가 하나도 없으면 오류 `'{job}' 직군 질문이 질문 은행에 부족해요.`
4. `avoid`(같은 회사 · 직군 그룹의 지난 회차 질문 글)에 없는 질문을 우선. 다 나왔으면 같은 후보 안에서 다시 고른다.
- 결과: 공통 면접 = 공통 2 + 직군 공통 3, 분야별 면접 = 공통 2 + 분야 3.

### 4.2 질문 출제 방식 (같은 회사 · 직군 기록이 있을 때만 고를 수 있음, 없으면 `new`)
| 방식 | 규칙 |
|---|---|
| 새로운 문제만 (new) | `pick_questions(avoid=그룹의 지난 질문 전체)` |
| 섞어서 (mix) | new 로 뽑은 뒤, 그룹 **마지막 회차**의 2~5번 질문 중 은행에 있는 것을 무작위 최대 2개(MIX_KEEP) 골라 **같은 자리**에 되돌린다. 그 글이 이미 다른 자리에 있거나 분야가 다르면 건너뜀. 자기소개(1번)는 대상 아님 |
| 똑같은 질문 (same) | 하위 선택 `이전 회차 선택`: 같은 면접 유형(분야별이면 같은 분야) · 질문 5개 회차를 selectbox(기본 마지막)로 골라 질문 그대로 복사. `과거 출제 질문에서 무작위`: 그룹 모든 회차 질문을 글 기준 중복 제거 → 공통(field==공통) 풀 · 이 분야 풀에서 공통 면접은 공통 5개, 분야별은 공통 2 + 분야 3 을 무작위, "자기소개" 질문을 맨 앞으로 |
- same 이 불가능하면 안내 후 **시작 버튼을 그리지 않는다**: `같은 유형 · 분야의 이전 회차가 없어요. 다른 출제 방식을 골라 주세요.` / `과거 질문에서 무작위로 만들려면 {서로 다른 공통 질문 5개 | 서로 다른 공통 질문 2개 + 이 분야 질문 3개} 이상이 나온 기록이 필요해요.`
- new · mix 에서 안 나온 질문이 모자라 지난 질문이 다시 들어갔으면(2~5번 중, mix 로 일부러 남긴 것 제외) 면접 화면 위에 1회 안내: `질문 은행에서 아직 안 나온 질문이 모자라, 지난 회차에 나온 질문 {n}개를 다시 넣었어요. 질문 은행에 질문을 더하면 새 질문이 늘어나요.`

### 4.3 면접관 배정
- 직군마다 면접관 1명 자동 배정, 사용자가 고르지 않는다. 디자인은 `PERSONA_TYPES["디자인"]["디자인 팀장"]`(style `probe`), 나머지 직군은 `PERSONAS[job]` 을 probe 로 쓴다.
- 설정 화면 소개 카드는 페르소나 글을 **나누기만** 한다(글을 바꾸지 않음):
  - 직책 · 경력 = `(역할)` 앞 글
  - 핵심 평가 역량 = "꼭 본다" 문장을 ` · ` 로 나눈 항목 중 앞 3개 (괄호 안 ` · ` 는 나누지 않음)
  - 성격 · 질문 성향 = "말투는" 으로 시작하는 문장
  - 진행 방식 = `질문 5개를 진행하고, 답이 부족할 때만 꼬리 질문을 해요 (질문마다 1개까지)`
- 면접 화면 캡션의 면접관 한 줄 = 페르소나 글의 첫 문장.

### 4.4 면접 진행 · 꼬리 질문 (`send_answer`)
1. 빈 답 → `답을 적은 뒤 보내 주세요.` (버튼을 disabled 로 막지 않는다)
2. 답을 먼저 `pending_answer = {q, follow_ups, text}` 로 보관 → 면접관 AI 호출 (지시문 `build_interviewer`, 입력 `format_transcript(messages + [새 답])`).
3. 실패: 대화에 넣지 않는다. 다음 화면에 보관 답 + 오류 문구 + [다시 시도] · [답변 수정] (8.4).
4. 성공: 지원자 메시지 추가, `understanding = clamp(응답 understanding, 0, 100)`.
5. **꼬리 질문 결정은 코드:** `follow_up == true` 이고 이 질문의 `follow_ups < 1` 이면 → `follow_ups += 1`, AI reply 를 면접관 메시지로 추가(같은 질문에 머묾).
6. 아니면: AI 가 `follow_up == false` 였을 때만 reply(짧은 반응)를 추가한다. **AI 가 꼬리 질문을 원했는데 한도로 막힌 경우 그 문장은 버린다.** `q_index += 1`, `follow_ups = 0`, 다음 질문 메시지 추가. 5번째가 끝나면 `면접을 마치겠습니다.` 추가, `stage = "done"`.
7. 중복 반영 방지: 응답이 왔을 때 `pending_answer` 와 `(q_index, follow_ups)` 가 보낸 시점과 같을 때만 반영.

### 4.5 AI 로 보내는 글 형식
- 상황 블록 `build_context(profile, with_experience)`: `CONTEXT.format(company=이름 또는 "회사 미지정", company_desc=설명 또는 "-", field, field_desc=FIELDS[field], job, experience=경험 또는 "(입력 없음)")`. **평가 · 재도전 채점은 `with_experience=False` → experience 자리에 `(평가에는 쓰지 않음)`** (제출한 답만 평가 근거).
- 면접관 입력 `format_transcript`: 메시지마다 `[면접관] {글}` / `[지원자] {글}` 한 줄 (`:material/아이콘:` 코드는 지움).
- 평가 입력 `format_record`: 질문마다 블록, 블록 사이 빈 줄.
  ```
  [질문 {i} · {유형}] {질문}
  [보는 점] {보는 점}      ← 비어 있으면 이 줄 생략
  [지원자] {답}
  [면접관] {꼬리 질문}
  [지원자] {꼬리 답}
  ```
  (q == i 이고 kind 가 question 이 아닌 메시지만)
- 지원자 답 `answer_text(i)` = q==i 인 지원자 메시지를 줄바꿈으로 이은 것(본답 + 꼬리 답).
- 형광펜 입력 `build_highlight_input`: `[질문] …` / `[보는 점] …` / 문장마다 `{n}) {문장}` (n 은 1부터). 문장 나누기 `split_sentences`: `(?<=[.!?…。])\s+` 또는 줄바꿈.
- 전략 지시문 칸: scores = `- {기준명}({key}): {점수}` 4줄, opinion = `- 가장 약한 점: {weak}` + `- 다음 연습에서 고칠 것: {항목}` (평가 next 전체). 입력 = 답 글 또는 `(답 없음)`.
- 재도전 지시문 칸: persona, context(경험 제외), question, point, before = 면접 때 최초 답, weak = **최초 평가**의 weak. 입력 = 새 답.
- 평가자 `{panel_criteria}` = `- {역할}: {PANEL_CRITERIA[역할]}` 4줄.

### 4.6 평가 응답 검증 `validate_evaluation` → 문제 코드 목록 (비면 통과)
- 최상위: dict 아님 `not_object:evaluation`, 칸 없음 `field_missing:{panel|conflict|agree|answers|next}`.
- panel: list 아님 `field_type:panel`, 4명 아님 `panel_count:{n}`, 원소 dict 아님, role 모름 `panel_role_unknown`, 중복 `panel_role_duplicate`, 빠진 역할 `panel_role_missing`, score 없음/정수 아님 `field_missing`/`score_type` (**bool · float · "5" 는 정수가 아님**), against · good 없음/문자열 아님.
- conflict · agree 문자열 아님 `text_type`.
- answers: list 아님, **개수 ≠ 질문 수(5)** `answer_count`, no 없음/정수 아님/1~5 밖/중복/빠짐 (`answer_no_*`), 기준 4개 점수 없음/정수 아님, weak · rewrite 없음/문자열 아님, check 없음/list 아님/원소 문자열 아님.
- next: list 아님 / 원소 문자열 아님.
- **점수 범위는 검사하지 않는다**(정수면 통과 → 저장할 때 보정).
- 코드가 하나라도 있으면 아무것도 저장하지 않는다. 빠진 값을 0점으로 채우거나 순서로 번호를 추측하지 않는다.

### 4.7 평가 저장 · 계산 `checked_evaluation`
- panel: PANEL_ROLES 순서로 정렬, `score = clamp(score, 0, 10)`.
- answers: 질문 순서대로 `no` 로 매칭, 기준마다 `clamp(0, 5)`, `score = 4기준 합(0~20)`, `question` 은 질문 은행 글, `needs_rewrite = score < 14`.
- `panel_average` = 위원 4명 점수 산술평균. `clamp(v, lo, hi)`: int 변환 실패면 lo.
- 종합: `first` = 최초 답 점수 5개 합, `latest` = 반영된 재도전이 있는 질문은 그 점수로 바꾼 합 (0~100).
- 판정 (latest 기준): **합격** latest ≥ 90 **and** 위원 평균 ≥ 9.0 / **합격 후보** ≥ 70 and ≥ 7.0 / 그 밖 **재도전 필요**. 부족분 글 `short`: 다음 단계 목표까지 `종합 점수 {n}점` · `위원 평균 {gap:.1f}점` (gap 은 0.1 단위 올림). 위원 평균은 재도전으로 바뀌지 않는다.
- 평가 탭 소제목: `이제 남은 것은 연습입니다.`(합격 기준) / `한 걸음만 더 가면 됩니다.`(후보 기준) / `승부는 지금부터입니다.`
- `rewrite` 글은 평가 화면에 보이지 않는다(모든 답이 20점일 때 [힌트 확인하기] 에서만 `**힌트 답변**` 으로). `next` 는 화면에 보이지 않고 저장 파일에만.

### 4.8 재도전
- 모든 질문을 다시 답할 수 있다. **횟수 제한 없음**(버튼 비활성 · 카운터 없음).
- 질문 선택 순서: 지금 점수(반영된 재도전 포함) 오름차순, 같으면 번호 순. 라벨 `질문 {no} · {최초[ → 현재]}/20점 · {질문}`.
- 같은 답 재채점 방지: 면접 때 답 + 그 질문의 모든 재도전 답을 공백 정규화(`" ".join(s.split())`)한 집합에 새 답이 있으면 AI 를 부르지 않고 `이미 채점받은 답변이에요. 답변을 수정하면 다시 채점받을 수 있어요.` 빈 답은 `다시 쓴 답을 적은 뒤 눌러 주세요.`
- 재도전 응답 검증 `validate_retry`: dict, 기준 4개 정수, weak 문자열. 통과 → `{scores: clamp 0~5, score: 합, weak}`. 실패 → 저장 안 함, 쓴 답을 `retry_pending[no]` 에 보관(`채점하지 못한 답변이 남아 있어요. 다시 채점할 수 있어요.`).
- 반영 규칙 `reflected_retry`: **최초 점수보다 엄격히 높은** 시도 중 최고 점수(동점이면 먼저 받은 것). 없으면 최초 점수가 그대로 반영된다.
- 결과 비교 기준: 이번 시도 **직전까지의 최고**(없으면 최초 답).

### 4.9 코칭 보조 (AI 없음)
- **역전의 실마리** `pick_clues`: 최신 점수 < 20 인 답을 (점수, 번호) 오름차순으로 앞 2개. 각 답의 가장 약한 기준 = 최저 기준(같으면 CRITERIA 순서 앞). 처음 고른 목록을 `clue_set` 에 고정, `clue_round` 1부터. 각 실마리는 찾은 시점의 재도전 횟수보다 늘면 "재도전함", 최신 점수가 이전보다 오르면 "역전 성공". 전부 재도전해야 [역전의 실마리 찾기] 로 다음 실마리(최신 점수 기준 다시 고름, round+1). 아니면 비활성 버튼 `재도전을 진행해보세요.` (유일한 disabled 예외). 모두 20점이면 `모든 답이 20점 만점이에요.` + [힌트 확인하기].
- **위원 코치 피드백** `panel_coaching(before, after)`: 위원마다 주 기준의 변화(up/down/same)로 고정 문장 1개 + 두 기준 변화 `{이름} {전}→{후} · …`.
  | 위원 | 주 기준, 보조 기준 |
  |---|---|
  | 실무 전문가 | relevance, specific |
  | 논리 분석가 | evidence, structure |
  | 커뮤니케이션 전문가 | structure, relevance |
  | 채용 담당자 | specific, relevance |

  | 기준 | up | down | same (5점 미만) |
  |---|---|---|---|
  | specific | 상황 · 숫자가 더 구체적으로 보여요. | 구체적인 상황 · 숫자가 줄었어요. 지난 답의 숫자를 되살려 보세요. | 숫자나 사례를 하나 더 넣으면 올라가요. |
  | relevance | 직무와의 연결이 분명해졌어요. | 직무와의 연결이 약해졌어요. 이 경험을 회사 업무와 이어 주세요. | 회사 · 직무와 연결하는 한 문장을 더해 보세요. |
  | structure | 답의 흐름이 더 분명해졌어요. | 흐름이 흐려졌어요. 결론을 첫 문장에 두세요. | 결론 → 이유 → 결과 순서로 다시 배치해 보세요. |
  | evidence | 근거와 확인 방법이 더 생겼어요. | 근거가 줄었어요. 데이터나 테스트 결과를 한 줄 넣어 보세요. | 어떻게 확인했는지(테스트 · 데이터)를 넣어 보세요. |

  same 이고 5점이면 `{기준명}{은/는} 만점이에요. 이대로 지켜 주세요.` (마지막 글자 받침 유무로 은/는).
- **형광펜 결과 정리**: `sentences[]` 중 `no` 가 정수인 것만 → `{no: {tags: CRITERIA 순서 · 중복 제거 · 모르는 키 버림, why}}`. 범례(색 · 기준 · 설명)는 HIGHLIGHT 지시문의 `- key(이름): 설명` 줄을 정규식으로 읽어 만든다. 캐시 키 `eval:{no}` / `retry:{no}:{답}` (세션에만).
- **전략 가이드 정리**: gap = `{기준: 5 - 점수}`(5점 기준 제외, 비면 가이드 없음). 제목 `+{gap 합}점 전략 가이드`. AI tips 중 criterion 이 gap 에 있고 tip 이 빈칸이 아닌 것만, 기준마다 최대 2개, 기준 순서대로. 팁이 없으면 `이 기준에 대한 전략을 받지 못했어요.`
- **만점 예시**: 점수 < 20 이고 질문 은행 `만점 예시` 가 있을 때만. `**만점 예시 답안** · :material/person_book: 가상 지원자` + 문장마다 줄바꿈한 `st.info` + 캡션 `질문 은행에 미리 적어 둔 예시라 내 경험 · 숫자와 무관해요. 결론 → 상황 · 행동(숫자) → 확인 방법 → 직무 연결 흐름만 참고해서 내 경험으로 고쳐 보세요.`
- **회차 종합 안내** `overview_advice` (공통 · 분야 면접 각각의 최고 최신 종합):
  - 공통 기록 없음(info): `공통 면접 기록이 없어요. '공통 면접' 으로 한 번 진행해 어느 회사에서나 나오는 일반 역량도 점검해 보세요.`
  - 공통 < 90(warning): `공통 면접 최고 {n}점 · 합격선까지 {90-n}점 남았어요. 자기소개 · 협업 같은 일반 질문을 재도전으로 다듬어 보세요.`
  - 분야 기록 없음(info): `분야 면접 기록이 없어요. 다음 회차는 지원할 회사의 분야를 골라 그 분야만의 특수 질문에 대비해 보세요.`
  - 분야 < 90(warning): `분야 면접 최고 {n}점 · 합격선까지 {90-n}점 남았어요. 분야 질문은 회사 · 서비스 맥락을 넣어 답하면 점수가 잘 올라요.`
  - 둘 다 ≥ 90(success): `공통 · 분야 면접 모두 합격선(90점)을 넘었어요. 재도전으로 답을 계속 다듬으며 실전 감각을 유지하세요.`

### 4.10 그룹 · 닉네임
- 그룹 = (company_key, job). 같은 회사 판단은 앞뒤 공백만 뺀 이름이 정확히 같은지. 회사가 비면 화면 그룹명 "기타"(실제 회사명 "기타"와는 key 가 None 인지로 구분).
- 닉네임 `"{수식어} {동물} {100~999}"`, 첫 접속 때 1회.
  - 수식어: 합격을 예감한, 당당한 척 잘하는, 오늘도 성장하는, 기회를 낚아채는, 내일이 기대되는, 자신감을 충전한, 출근을 꿈꾸는, 역전을 준비하는, 꿈을 향해 달리는, 칭찬에 춤추는
  - 동물: 토끼, 수달, 판다, 펭귄, 쿼카, 햄스터, 고양이, 다람쥐, 여우, 고래, 부엉이, 사슴
  - 수정: 연속 공백을 하나로, 20자 자름, 빈칸이면 바꾸지 않음.

---

## 5. AI 연동 (llm.py · prompts.py)

### 5.1 `ask_json(instructions, user_input, schema, name) -> dict`
- 키가 없으면 호출하지 않고 `LLMError("API 키가 없어요. .env 에 OPENAI_API_KEY 를 넣어 주세요.", kind="api_auth", code="missing_api_key")`.
- `OpenAI(api_key=키).responses.create(model=..., instructions=instructions, input=user_input, text={"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}})` → `json.loads(response.output_text)`. SDK 기본 재시도(max_retries=2) 그대로.
- 지시문은 `instructions`, 지원자 글은 `input` 으로 **나눠** 보낸다.
- 오류는 모두 `LLMError(message, kind, http_status, exception, code)` 로 바꾼다. SDK 예외 원문은 담지 않는다(`from None`).

| 원인 | 화면 문구 | kind |
|---|---|---|
| AuthenticationError (401) | API 키가 틀렸어요. .env 의 OPENAI_API_KEY 를 확인해 주세요. | api_auth |
| RateLimitError, code=insufficient_quota | OpenAI 크레딧이 부족해요. 결제 · 사용 한도를 확인해 주세요. | api_quota |
| RateLimitError 그 밖 | 요청이 너무 많아요. 잠시 뒤 다시 시도해 주세요. | api_rate_limit |
| APITimeoutError (먼저 검사) | OpenAI 에 연결하지 못했어요. 인터넷 연결을 확인해 주세요. | api_timeout |
| APIConnectionError | (위와 같음) | api_connection |
| PermissionDeniedError (403) | AI 응답을 받지 못했어요. 잠시 뒤 다시 시도해 주세요. | api_auth |
| InternalServerError (5xx) | (위와 같음) | api_server |
| 그 밖 OpenAIError | (위와 같음) | api_other |
| output_text JSON 해석 실패 | AI 응답을 읽지 못했어요. 다시 시도해 주세요. | response_parse (code json_decode) |

- 앱 쪽 검증 실패(`EvaluationInvalid`) → kind `eval_validation`, 문구: 평가 `평가 결과를 확인하지 못했어요. 잠시 뒤 다시 평가받아 주세요.` / 재도전 `채점 결과를 확인하지 못했어요. 잠시 뒤 다시 채점해 주세요.`

### 5.2 AI 호출 목록
| name | 지시문 (부록 A) | 만드는 함수 | 입력 | 스키마 | 언제 |
|---|---|---|---|---|---|
| interviewer | INTERVIEWER | build_interviewer | format_transcript | INTERVIEWER_SCHEMA | 답을 보낼 때마다 |
| evaluation | EVALUATOR | build_evaluator | format_record | EVAL_SCHEMA | [평가 받기] |
| retry | RETRY | build_retry | 새 답 | RETRY_SCHEMA | [다시 채점] |
| highlight | HIGHLIGHT | build_highlight | build_highlight_input | HIGHLIGHT_SCHEMA | 형광펜을 켤 때 |
| strategy | STRATEGY | build_strategy | 답 글 | STRATEGY_SCHEMA | [전략 가이드 받기] |

- 지시문은 `str.format()` 으로 `{ }` 칸만 채운다. 프롬프트 원문 · 스키마는 **부록 A 를 그대로 `prompts.py` 로 저장**한다.

### 5.3 앱 수준 자동 재시도 (`run_ai` · `call_ai`)
- `kind ∈ {response_parse, eval_validation}` 이고 `source ∈ {interviewer, evaluation, retry}` 일 때만 **1번 더** 요청(최대 2번 시도). 두 번째 스피너 `응답을 한 번 더 확인하고 있어요.`
- 연결 · 시간 초과 · 서버 · 호출 제한은 SDK 가 이미 재시도하므로 앱은 다시 부르지 않는다. 형광펜 · 전략은 자동 재시도 없음.
- `call_ai` 는 스피너 안에서 `store(ask_json(...))` 를 바로 실행해 결과를 즉시 세션에 저장한다(재실행으로 버려지지 않게). 평가 · 재도전의 store 는 맨 앞에서 검증하고 실패하면 아무것도 바꾸지 않는다. 실패하면 `st.error(문구)`.

---

## 6. 화면 명세 (app.py)

### 6.1 진입 · 이동
- `st.set_page_config(page_title="역전 면접 코칭", page_icon="assets/favicon.png")` · 전역 CSS 주입(9장).
- 매 실행: `sync_active()` → 이동 예약 처리 → `page=="start"` 이면 시작 화면만 그리고 `st.stop()` → 아니면 공통 머리(로고 띠 + GNB) → 1회성 안내 → (`restart_pending` 이면 확인 창) → `PAGES[page]()` → 활성 회차가 있고 page 가 interview/coaching 이면 사이드바 상태창.
- URL 라우팅 · `st.navigation` 은 쓰지 않는다. 세션 키 + rerun. 이동 때 페이지 맨 위로 스크롤.

### 6.2 시작 화면 (start)
- 가운데 큰 로고(라이트/다크 로고 파일).
- 세션 첫 진입 때 한 번만 스플래시 문구 `질문을 파악하고, 전략을 강화하라!` / `합격을 향한 전세역전(戰勢逆轉) 취업 코칭 서비스` → 약 3초 뒤 본문 (9.6).
- 본문: `반가워요, **{닉네임}** 님.` + 버튼 `:material/add: 새 면접 시작`(primary → 설정) · `:material/upload_file: 기존 데이터 Markdown 복원`(→ 복원). 시작 화면에는 GNB · 홈 버튼이 없다.

### 6.3 공통 머리 (start 외 모든 화면)
1. 로고 띠: 로고 + 띠 전체를 덮는 투명 버튼 "홈으로 돌아가기" → 홈.
2. GNB 가로 버튼(순서 고정): `:material/home: 홈` · `:material/forum: 면접 코칭` (현재 화면이면 primary) · `:material/add: 새 면접 시작` · `:material/save: 데이터 저장하기`(모달) · `:material/upload_file: Markdown 복원`.
3. 마지막 저장 뒤 바뀐 기록이 있으면 캡션: `마지막 저장 뒤에 바뀐 기록이 있어요. 창을 닫거나 새로고침하면 사라지니 '데이터 저장하기' 로 받아 두세요.` (판단: 저장 대상 회차 데이터의 sha1 지문 ≠ `saved_fingerprint`)

### 6.4 홈 (home)
- 인사 카드: `반가워요, {닉네임} 님!` / `오늘도 합격을 향해 한 걸음 나아가 볼까요?` / 작은 버튼 `닉네임 수정`(→ 입력칸 `닉네임` 20자 + `저장` · `취소`). 제목 → 설명 → 버튼 순서, 왼쪽 정렬, 세로 가운데.
- 기록 0개: `첫 모의면접을 시작해 볼까요?` + 캡션 + `:material/add: 첫 면접 시작하기`.
- 기록 있음: 2열 [왼쪽 2 : 오른쪽 1].
  - 왼쪽 ① **진행 중인 면접**(stage=interview 회차가 있을 때): 행마다 `**{회사|기타} · {직군} · {n}회차**` / `질문 {q_index+1} / 5` + `이어서 하기`.
  - 왼쪽 ② **나의 면접 현황** 카드 3개: `면접 기록` = 전체 회차 수(칩 `전체 회차`) · `완료한 면접` = stage=done 수(칩 `질문 5개 완료 · 그중 평가 완료 {k}`) · `진행 중인 면접` = stage=interview 수(칩 `질문 5개를 마치기 전`).
  - 왼쪽 ③ **최근 면접**: 완료 회차를 (날짜, 생성순) 내림차순 3개. `**{회사|기타} · {직군} · {n}회차**` / `{날짜} · {상태}[ · 종합 {latest}/100]` + `기록 보기 >` → 면접 코칭 · 면접 기록 탭 · 그 회차.
  - 오른쪽 **빠른 시작 카드**(스크롤 고정): `새로운 면접을 준비해 볼까요?`, 정보 줄 `질문 수 · 5문항` / `꼬리 질문 · 질문당 최대 1개` / `평가 · 위원 4명`, 버튼 `:material/add: 새 면접 시작`(primary) · `:material/forum: 면접 기록 보기`.

### 6.5 면접 정보 설정 (setup)
| 순서 | 위젯 | 규칙 |
|---|---|---|
| 1 | text_input `회사 이름 (선택)` | 40자, placeholder `비워 두면 '기타' 그룹에 기록돼요`, help `같은 회사는 앞뒤 공백만 뺀 이름이 정확히 같은지로 판단해요.` 기록 있는 회사가 있으면 캡션 `기록이 있는 회사: A · B` |
| 2 | text_input `회사 설명 (선택)` | 100자, placeholder `예시: IT, 헬스케어 진단 서비스` |
| 3 | pills `직군` (required) | 개발 · 디자인 · PO · 마케팅, 기본 디자인 |
| 4 | radio `면접 유형` (가로) | `공통 면접` / `분야별 면접`, help `공통 면접: 공통 질문 5개 · 분야별 면접: 공통 2개 + 고른 분야 3개. 회차 번호는 함께 이어져요.` 그 직군에 분야 질문이 없으면 공통만 |
| 5 | pills `분야` (분야별일 때, required) | 은행에 그 직군 질문이 있는 분야만 FIELDS 순서로, 기본 첫 번째. 캡션 `{분야} · {분야 설명}` |
| 6 | 면접관 소개 카드 | 4.3 의 형식: `:material/support_agent: **{이름}** · {직책 · 경력}` + `성격 · 질문 성향` / `핵심 평가 역량` / `면접 진행 방식`(`… 면접 중에는 평가하지 않고, 끝난 뒤 위원 4명이 평가해요.`) + 펼침 `면접관 자세히 보기`(디자인은 PERSONA_CARDS 2열 카드, 다른 직군은 페르소나 문장 목록). 이름: 디자인 `디자인 팀장`, 그 외 `{직군} 면접관` |
| 7 | text_area `내 경험 (선택)` | 1000자, placeholder `면접관이 질문할 때 참고할 경험을 적어 주세요. 비워 둬도 면접을 시작할 수 있어요.`, help `면접관의 질문에만 참고해요. 평가는 실제로 제출한 답변으로만 해요.` |
| 8 | 회차 안내 | 기록 있음 info `**{그룹} · {직군}** 기록 {k}회차가 있어요. 이번 면접은 **{n}회차**예요.` / 없음 캡션 `**{그룹} · {직군}** 의 첫 회차예요 ({n}회차).` |
| 9 | radio `질문 출제 방식` (기록 있을 때) | 새로운 문제만 · 섞어서 · 똑같은 질문 (4.2) |
| 10 | 버튼 (primary) | 기록 있으면 `새로운 회차 시작하기`, 없으면 `면접 시작하기` |
- 시작: 질문 5개 결정 → 회차 레코드 생성 → messages = [시작 인사, 질문 1] → `store_rounds` 에 추가 → 펼침 → interview 화면.

### 6.6 면접 진행 (interview) + 사이드바 상태창
- 제목 `{회사|기타} · {직군} 신입 면접 · {n}회차`, 캡션 `{공통 면접|분야별 면접} · {분야} 분야 · {면접관 한 줄}`.
- `st.chat_message`(아바타 면접관 `:material/support_agent:`, 지원자 `:material/person:`) + `st.chat_input`(placeholder `답을 적어 주세요 (1,500자까지)`, 5번째 질문이면 앞에 `마지막 질문이에요. `, 1500자). 스피너 `면접관이 답을 읽고 있어요...`.
- 진행 중 회차가 없으면 info `진행 중인 면접이 없어요. '새 면접 시작' 으로 시작해 주세요.`
- 사이드바 `상태창`: `{회사|기타} · {직군} · {n}회차` / 캡션 `{유형} · {분야} 분야` / 진행 막대 `질문 {n}/5` / metric `면접관이 본 이해도` `-` 또는 `{x}/100` / (평가 뒤) `종합 점수 {latest}/100`(변화량) · `위원 평균 {x.x}/10` / 버튼 `:material/restart_alt: 처음부터 다시`.
- **처음부터 다시** 모달 `처음부터 다시 할까요?`: 진행 중 회차면 warning `지금 면접의 답이 사라지고, 면접 정보 설정부터 다시 시작해요.`(확인 시 그 회차 삭제), 끝난 회차면 `이 회차 기록은 그대로 두고, 같은 회사 · 직군으로 새 회차를 시작해요.` 버튼 `머무르기` / `다시 시작하기`(primary → 설정, 회사 · 설명 · 직군 · 경험 미리 채움).
- **완료 박스**: `**질문 5개를 모두 마쳤어요. 수고하셨습니다.**`
  - 평가 전: 캡션 `답변 {n}개를 기록했어요. [평가 받기] 를 누르면 위원 4명이 답변을 평가해요.` + `:material/gavel: 평가 받기` (클릭 → `eval_running` 깃발 → 다음 실행에서 깃발을 먼저 내리고 평가 호출, 스피너 `답변을 검토하겠습니다. 위원 4명이 면접 기록을 보고 있어요...`, 중복 호출 방지).
  - 평가 후: 캡션 `평가가 끝났어요. 이 회차의 면접 기록에서 위원 4명의 평가를 확인해 주세요.` + `:material/bar_chart: 평가 확인하기` → 면접 코칭 · 평가 기록 탭 · 이 회차.
  - 마지막 답 직후 한 번 이 박스로 스크롤.

### 6.7 면접 코칭 (coaching)
- `coach_group` 이 없으면 **면접 데이터 목록**: 제목 `면접 데이터 목록`. 기록 없으면 info `아직 면접 기록이 없어요. '새 면접 시작' 이나 'Markdown 복원' 으로 기록을 만들어 주세요.` 회사별 테두리 카드(`**:material/business: {회사|기타}**`, 회사 가나다 · 기타 맨 뒤), 직군마다 버튼 `{직군} · {k}회차 · 최근 {날짜} · {최근 상태}` → 그 그룹 열기.
- 그룹을 열면 머리줄 `{회사|기타} · {직군}` + 버튼 `:material/list: 면접 데이터 목록`, 그 아래 **LNB** `st.segmented_control`(라벨 숨김, 전체 폭): `:material/bar_chart: 평가 기록 (회차별)` · `:material/history: 면접 기록 (전체)` · `:material/replay: 재도전 (전체)`. 기본 탭 = 이동 요청 > 마지막 고른 탭 > 면접 기록. **위젯을 만든 뒤 같은 키의 상태를 직접 바꾸지 않는다**(StreamlitAPIException 방지 — 이동은 예약 키로 다음 실행 시작 때 처리).
- 회차 라벨 `{n}회차 · {공통 면접|분야별 면접}[ · 분야] · {날짜} · {상태}`. 세 탭은 같은 활성 회차를 공유한다.

**① 평가 기록 (회차별)**
- selectbox `회차`(질문 5개를 마친 회차). 없으면 info `평가할 수 있는 회차가 없어요. 질문 5개를 마친 회차가 생기면 여기서 평가 기록을 봐요.` 평가 전이면 info `이 회차는 아직 평가 전이에요. 위원 4명에게 평가받아 주세요.` + `:material/gavel: 평가 받기`.
- **모의 결과**: 판정 기준 캡션 → `:material/mail: 모의 결과 확인하기` → 연출(휴대폰 문자 2통 `최종 면접 결과가 도착했습니다.` → `{닉네임}님, {회사} {직군} 신입 모의면접 결과를 메일로 보내 드렸습니다. 메일함을 확인해 주세요.` → 메일 카드: 보낸이 `{회사} 모의면접 위원회`, 제목 `[{회사}] {직군} 신입 모의면접 결과 안내 ({n}회차)`, 판정 배지, 결과 제목 · 본문, 3칸 `최신 종합` · `최초 종합` · `위원 평균`, 면책 `※ … 이 앱에서만 보이는 시뮬레이션이에요.`).
  - 결과 제목 · 본문: 합격 `모의면접 합격입니다. 당신의 가능성을 증명했습니다.` / `실전처럼 소리 내어 답해 보며 감각을 유지하세요.` · 후보 `합격 후보로 선정되었습니다.` / `합격선(위원 평균 9.0 · 종합 90)까지 {short} 남았어요. …` · 재도전 필요 `재도전으로 대답을 수정해보세요.`(위원 평균이 부족하면 `재도전으로 대답을 수정하는 연습을 거친 후, {n+1}회차 면접을 통해 위원 평가 점수를 올려보세요.`) / `합격 후보까지 {short} 부족해요. 아직 역전의 기회가 남아 있어요.`
  - 공통 분야 회차면 팁 `다음 회차 추천 · 분야를 골라 면접 보기`. 버튼: (공통이면) `:material/explore: 분야를 골라 {n+1}회차 면접 진행하기` → 설정(같은 회사 · 직군, 분야별) · (합격 아니면) `:material/replay: 재도전으로 점수 올리기` · `:material/insights: 전체 회차 종합 보기`.
- **평가 본문**: 소제목(4.7) → metric `위원 평균 {x.x}/10` + AI 고지 캡션 `:material/smart_toy: AI가 쓴 의견이에요. 사실과 다를 수 있으니 직접 확인해 주세요.` → `위원별 의견` pills(`{역할} · {점수}`) → 고른 위원 카드(점수 `n/10` · 막대 · `평가 기준 · …` · 좋은 점 · 뽑지 말아야 할 이유) → 2열 `판단이 갈린 곳` / `모두 같은 판단` → 펼침 `전체 요약 · 위원 4명 한눈에 보기`(표) · `평가 기준과 근거 보기`(부록 E) → 같은 그룹 이전 평가 회차가 있으면 `지난 면접({r}회차 · {날짜})과 비교`(위원 평균 · 최신 종합 metric + 같은 질문 글 비교 표) → `답변별 점수`: 답마다 expander `질문 {no} · {score}/20점` (14점 미만이면 펼친 상태): 질문 · `구체성 a · 직무 연관 b · 구조 c · 근거 · 검증 d` · `**내 답**`(문장마다 줄바꿈) · `**가장 약한 점:**` · 만점 예시(4.9) · 20점 미만이면 `:material/replay: AI 코칭을 반영해 재도전으로 역전의 기회 잡기` → 재도전 탭 · 그 질문.

**② 면접 기록 (전체)**
- 표 `회차별 면접 기록`(회차 · 날짜 · 유형 · 분야 · 상태 · 최초 종합 · 최신 종합) → selectbox `확인할 회차` → 회차 요약 카드(최초/최신 종합, 질문 5개 목록 · 최초 점수, 진행 중이면 `:material/play_arrow: 면접 이어서 하기`) → 회차 종합(평가된 회차가 있을 때): 회차별 최신 종합 막대그래프(분야 색 · 합격선 90 점선), `공통 면접 최고` / `분야 면접 최고` metric, 진행도, 안내 문구(4.9) → 펼침 `전체 면접 대화 기록 · {n}회차`(chat_message).

**③ 재도전 (전체)**
- 평가된 회차가 없으면 info `평가받은 회차가 생기면 답변별로 재도전할 수 있어요.`
- 표 `전체 답변별 점수 · 변화`(회차 · 질문 · 최초 · 최고(반영) · 변화 · 재도전 횟수) → selectbox `회차`(평가된 회차).
- **역전의 실마리** (4.9): 소제목 `역전의 실마리를 찾았습니다.`, 배지 `실마리 {k}회차 · {N}개 중 {m}개 재도전 완료`, 카드 `질문 n · s/20점 · 가장 약한 기준 X a/5` + 상태(`역전 성공! b → a점 (+d)` / `재도전 완료 · b → a점 (±d). 한 번 더 도전해 볼 수 있어요.` / 가장 약한 점) + 버튼 `역전의 기회 잡기`(primary) 또는 `한 번 더 도전하기` → 그 질문 선택 · 아래로 스크롤.
- **답변 재도전**: selectbox `다시 답할 질문 (지금 점수 낮은 순)` → 지난 기록(metric `지난 점수`, `지난 약한 점`, 펼침 `지난 답 보기` + 토글 `형광펜 모드`, 20점 미만이면 `+N점 전략 가이드` + `전략 가이드 받기`) → `**이제, 당신의 차례입니다.**` text_area `다시 답하기`(1500자) + `다시 채점`(primary, 스피너 `다시 쓴 답을 채점하고 있어요...`) → 결과(비교 기준 캡션, metric `후 점수`(변화), 반영 여부, 기준별 전 · 후 표/막대, `이번 답의 약한 점`, 펼침 `다시 쓴 답 보기`(형광펜), 위원 코치 피드백 2×2 카드) → 펼침 `반영 안 된 재도전 k번 보기`.
  - 역전 성공(최신 > 최초)이면 결과 → 입력 → `역전 전 기록` 순서로 바꾸고 맨 위로 스크롤. "역전 성공!" 문구는 실마리 카드에만.
- **형광펜 표시**: 문장마다 기준 색 칠(구체성 노랑 `#FFE45C` · 직무 연관 하늘 `#8CCBFF` · 구조 연두 `#9BE89B` · 근거 · 검증 분홍 `#FFADD2`, 글자 `#171719`, 여러 기준이면 135° 6px 사선 줄무늬), 문장을 누르면 이유(why) 펼침, 색 범례 표. 실패하면 형광펜 없이 답만.
- **전략 가이드 카드**: 기준마다 `{기준명} {점수}/5 → +{gain}`, 팁마다 동작 아이콘(추가 add · 수정 edit · 축약 content_cut · 삭제 delete) + target 인용 + tip.

### 6.8 데이터 저장하기 모달
- `@st.dialog("데이터 저장하기", width="large")`, 먼저 `sync_active()`.
- 저장 대상 = stage=done 회차. 없으면 info `저장할 면접 기록이 없어요. 면접 질문 5개를 마치면 저장할 수 있어요.`
- `**회사 · 직군 {g}곳 · 회차 {k}개**를 파일 하나로 저장해요.` / 진행 중 회차가 있으면 캡션 `진행 중인 면접 {n}개는 저장되지 않아요. 질문 5개를 마친 뒤 저장해 주세요.`
- warning `:material/lock: 파일에는 닉네임 · 회사 · 내 경험 원문 · 면접 대화 · 답변이 들어가요. 다른 사람과 공유할 때 주의해 주세요.`
- checkbox `위 안내를 확인했어요. 개인정보가 들어간 파일이라는 걸 알고 내려받을게요.` — 체크 전에는 다운로드 버튼 disabled(유일한 disabled 예외) + 캡션 `위 안내를 확인하고 체크하면 다운로드 버튼이 켜져요.`
- `st.download_button(":material/download: {파일명} 다운로드", mime="text/markdown")`, 파일명 `{YYMMDD}-역전취업코칭-면접기록.md`, 클릭 시 `saved_fingerprint` 갱신. 캡션 `저장할 때마다 새 파일로 내려받아요. 컴퓨터에 있는 기존 파일은 바뀌지 않아요.`

### 6.9 Markdown 복원 (restore)
- 제목 `기존 데이터 Markdown 복원` + 안내 캡션. `st.file_uploader(type=["md"], accept_multiple_files=True)`. 파일별 `file_id` 로 결과를 캐시해 한 번만 처리.
- 결과: 오류 `st.error("{파일명}: {사유}")` / 성공 `{파일명} · 통합 저장(v2) · {회차 k개를 불러왔어요.|새로 불러온 회차는 없어요.}[ 이미 있던 회차 s개는 다시 만들지 않고 건너뛰었어요.]` + 부분 복원 경고(8장).
- 새로 더한 회차 **또는 건너뛴 회차**가 하나라도 있으면 버튼 `:material/forum: 면접 기록 보기` → 면접 코칭. (같은 파일을 다시 올려 전부 건너뛰어도 기록 보기로 갈 수 있어야 한다.)
- 업로드 칸에서 파일을 X 로 지워도 불러온 기록은 지우지 않는다.

---

## 7. Markdown v2 저장 파일

### 7.1 파일 모양
```markdown
# 역전 취업 코칭 — 면접 기록

- 닉네임: {닉네임}
- 저장 시각: YYYY-MM-DD HH:MM
- 회차 N개

> 점수는 모두 앱이 계산한 값이에요. **AI 의견** 표시가 붙은 글은 AI가 쓴 것이라 사실인지 직접 확인해 주세요.

## {회사|기타} · {직군} · {n}회차
(사람이 읽는 회차 본문 — 7.2)
...
<!-- interview-data {JSON 한 줄} -->
```
- 회차 순서: 회사 있는 회차(company_key 가나다) → 기타 → 직군 → 회차 번호.
- **기계 데이터는 파일 맨 끝 HTML 주석 한 줄**: `<!-- interview-data {JSON} -->`. JSON 은 `ensure_ascii=False`, 문자 `>` 를 `>` 로 바꿔 `-->` 가 주석을 끝내지 않게 한다. 읽을 때 정규식으로 이 줄을 찾는다.

### 7.2 사람이 읽는 회차 본문
- 평가 있음: `## 1. 점수`(최초 · 최신 종합, 위원 평균, 판정) · `## 2. 질문별 기록`(질문마다 `### 질문 i. {질문} ({점수}/20점)`, 내 답 인용, 기준 점수, 가장 약한 점, 만점 예시(4.9 조건), 재도전 기록 — 반영 안 된 재도전은 `<details>`) · `## 3. 위원회 의견 (AI 의견)` · `## 4. 다음 연습에서 고칠 것 (AI 의견)`(next 번호 목록, 없으면 `(없음)`).
- 평가 전: `- 상태: 평가 전`, `- 날짜: …`, 질문마다 `### 질문 i. {질문}` + `**내 답**` 인용.
- (15장 확인 필요: 사람이 읽는 본문의 세부 문구는 복원에 쓰이지 않으므로 위 구조만 지키면 된다.)

### 7.3 JSON 최상위
| 칸 | 내용 |
|---|---|
| `version` | `2` |
| `nickname` | 닉네임 (복원 때 40자로 자름, 화면 닉네임은 바꾸지 않음) |
| `saved_at` | `YYYY-MM-DD HH:MM` |
| `companies` | `[{company_id, company_name, company_key}]` 참고용 (복원 때 읽지 않음) |
| `rounds` | 회차 목록 (최대 500) |

### 7.4 회차 칸
| 칸 | 내용 |
|---|---|
| `round_id`, `round_number`, `company_id`, `company_name`, `company_key`(null 가능), `company_desc`, `job`, `field`, `interview_type`, `question_mode`, `date`, `experience` | 3.3 과 같음 |
| `questions` | 5개 `{question_id, type, question, point, field}` (만점 예시는 넣지 않고 복원 때 은행에서 다시 붙임) |
| `status` | `"evaluated"` 또는 `"evaluation_pending"` |
| `session.messages` | 대화 전체 (3.4 형태). 최초 답은 여기 |
| `session.evaluation` | 평가 전 `null`. 있으면 **AI 응답 모양** `{panel:[{role,against,good,score}], conflict, agree, answers:[{no, specific, relevance, structure, evidence, weak, rewrite, check[]}], next[]}` — 합계 · 평균은 넣지 않고 복원 때 다시 계산 |
| `session.retry_history` | `{"질문번호": [{attempt_id, answer, specific, relevance, structure, evidence, weak}, …]}` (질문당 500 초과 파일은 거부) |
| `session.retries` · `session.retry_counts` | 최고 시도 · 시도 수 (참고용, 복원 때 retry_history 로 다시 계산) |
| `session.clues` | `{round, set: [{no, score, retry_count}] 또는 null}` |
| `session.understanding` | 0~100 또는 null |
| `session.latest_unscored` (선택) | `{"no": {answer}}` 채점 못 한 최신 답 (이미 채점된 답과 같으면 넣지 않음) |
| `session.retry_unreadable` · `session.evaluation_unreadable` (선택) | 읽지 못한 원본 보존 (다시 저장해도 유지) |

### 7.5 복원 규칙 `parse_store_file(text, bank)`
1. UTF-8 5MB 초과 → `리포트 파일이 너무 커서 불러오지 않았어요 (5MB 초과).`
2. 데이터 주석 없음 → `이 파일에는 복원할 데이터가 없어요. 이 앱에서 받은 면접 기록 파일(.md)을 올려 주세요.`
3. JSON 깨짐 → `리포트의 이어 하기 데이터가 깨져 있어요.`
4. `version != 2` 또는 rounds 가 목록이 아니거나 500 초과 → `지원하지 않는 리포트 형식이에요.`
5. 회차 하나라도 아래에 걸리면 **파일 전체 거부**: 회차가 dict 아님 · round_id 문자열 아님 · job 이 JOBS 밖 → `면접 기록 파일의 회차 데이터를 읽지 못했어요.` / 질문이 정확히 5개 아님 → `면접 기록 파일의 질문 데이터를 읽지 못했어요.` / session 모양 이상 → `면접 기록 파일의 대화 데이터를 읽지 못했어요.` / 재도전 질문당 500 초과 → `재도전 기록이 너무 많은 리포트라 불러오지 않았어요 (질문당 500개 초과).`
6. 정리: 글 칸 2000자 자름, round_id 40자, round_number 1~999, 모르는 분야 → 공통, 질문 글이 은행과 같으면 만점 예시 등 보충.
7. 되살리기: `stage="done"`, `q_index=5`. 평가는 `checked_evaluation` 으로 다시 검증 · 보정 — 실패하면 `evaluation=None` + 원본을 `evaluation_unreadable` 에 보존(0점 채우기 금지) → 경고 `평가 데이터를 읽지 못해 질문과 답변만 불러왔어요. 다시 평가받을 수 있어요.` 재도전 기록은 하나씩 `checked_retry`, 실패한 것은 `retry_unreadable` 에 보존하고 점수에서 제외 → `일부 재도전 평가를 읽지 못했어요. 답변은 보존했지만 해당 점수는 반영하지 않았어요.` attempt_id 가 없거나 중복이면 순서대로 다시 매김. `latest_unscored` → `retry_pending`.
8. **같은 round_id 가 이미 있으면 건너뛴다(덮어쓰지 않음).** 없으면 `store_rounds` 에 추가. 복원 전에 미저장 변경이 없었으면 지문을 새 값으로 갱신.
- 저장 → 복원 → 다시 저장한 파일의 JSON 이 같아야 한다(왕복).

---

## 8. 오류 처리 · 상태 관리

### 8.1 원칙
- 오류는 화면에 한국어 한 줄(`st.error`). 키 · 요청 원문 · AI 응답 원문은 화면 · 터미널에 찍지 않는다.
- 버튼을 disabled 로 막지 않고, 누른 뒤 빈칸이면 안내한다. 예외는 두 곳뿐: 저장 모달 다운로드 버튼(체크 전), 역전의 실마리 `재도전을 진행해보세요.`
- 실패해도 사용자가 쓴 답은 잃지 않는다.

### 8.2 오류 기록 `error_log.py`
- 로거 `yeokjeon.errors`, JSON 한 줄. 항상 stderr, `ERROR_LOG_FILE_ENABLED` 가 true/1/yes/on 일 때만 `logs/errors.jsonl`(5MB × 백업 3개 회전).
- 칸: `error_id`(uuid) · `session_id`(화면 세션당 uuid) · `timestamp`(UTC ms) · `error_type`(kind 목록 + markdown_build, markdown_parse, restore_parse, restore_validation) · `source`(interviewer, evaluation, retry, highlight, strategy, restore) · `attempt` · `status`(retrying · recovered · failed) · `codes`(최대 20개, 정해진 형식) · `meta`(허용 칸만: model, exception, round_id, question_id, http_status, question_no, file_version, item_count).
- **금지:** 사용자 답 · 개인정보 · API 키 · 토큰 · AI 응답 원문 · 예외 메시지. `sk-` · bearer · `eyJ` · api_key · token · secret · password 가 보이는 값은 버린다. 형식이 틀린 이벤트는 기록하지 않는다. 기록 실패가 화면을 막지 않는다.

### 8.3 실패 시 화면
| 호출 | 보이는 것 · 보존 |
|---|---|
| 면접관 | 보관 답 말풍선 + 캡션 `아직 면접관에게 전달되지 않은 답변이에요.` + 오류 + info `답변을 보관했어요. 다시 보내거나 수정할 수 있어요.` + `:material/refresh: 다시 시도`(primary) · `:material/edit: 답변 수정`(→ text_area `답변 수정` + `수정한 답변 보내기` · `수정 취소`). 질문은 넘어가지 않는다. 보관 중에 입력창에 새로 쓰면 바로 보내지 않고 수정 칸으로 옮기고 캡션 `새로 쓴 답변은 아래 수정 칸에 옮겨 두었어요. '수정한 답변 보내기' 를 눌러야 바뀌어요.` |
| 평가 | 오류, 답 · 대화 그대로, [평가 받기] 다시 가능 |
| 재도전 | 오류, 쓴 답을 질문별 `retry_pending` 에 보관해 다른 질문에 갔다 와도 입력칸에 다시 채움, 기록 · 최고 점수 불변 |
| 형광펜 · 전략 | 오류, 형광펜 없이 답 표시 / 버튼 다시 누를 수 있음 |
| 복원 | 파일별 오류(7.5), 다른 파일은 계속 처리 |

---

## 9. 디자인 시스템 · 반응형

### 9.1 테마 · 글꼴
- `.streamlit/config.toml` 은 **부록 B 를 그대로** 쓴다(라이트 · 다크 팔레트, Pretendard Variable v1.3.9 를 `font = "이름:CSS URL"` 로 로드, baseRadius 8px, buttonRadius 10px, 제목 크기 30/24/20/18/16/14px).
- 브랜드 색 `#0252DE`(다크 `#3D7BFF`), 배경 `#FFFFFF`(다크 `#1B1C1E`), 글자 `#0B1020`, 보조 글자 `#444D63`(다크 캡션 `#AEB3C2`), 테두리 `#E1E2E4`.
- 다크 모드: Streamlit 테마 전환에 맡긴다. 앱은 매 실행 `st.context.theme.type == "dark"` 를 보고 CSS 팔레트 값과 로고 파일을 바꾼다(미디어 쿼리 안 씀).
- 그라데이션 · 그림자 · 강조 테두리는 줄인다(그라데이션은 시작 화면에만). 아이콘은 Material Symbols(`:material/…:`)만, 이모지 금지. 한국어는 `word-break: keep-all`.

### 9.2 전역 CSS (`st.markdown("<style>…", unsafe_allow_html=True)`, `.st-key-{키}` 로 컨테이너 지정)
- 글자: H1 30px/1.38/−0.6px(640px 이하 26px), H2 24px, H3 20px, 본문 16px/1.5.
- 본문 위 여백 76px. 테두리 컨테이너 radius 16px, expander · alert 12px.
- primary 버튼은 hover 때도 같은 색(홈 안에서만 `#0242B2`), 그 밖 버튼은 hover 때 배경만 `color-mix(in srgb, currentColor 6%, transparent)`.
- 상태창 · 면접 상세의 metric 값 28px.

### 9.3 홈
- 홈만 본문 최대 폭 1120px. 홈 팔레트(라이트/다크): point `#0252DE`/`#3D7BFF`, hero `#F5F8FE`/`#1E2230`, card `#FFFFFF`/`#212225`, line `#E6E9F0`/`#37383C`, title `#0B1020`/`#F7F7F8`, text `#444D63`/`#C2C4C8`, chip `#F4F5F8`/`#292A2D`.
- 인사 카드: radius 24px, padding 40px 44px, min-height 200px, 테두리 없음. 닉네임 수정 버튼은 작은 외곽선(min-height 32px, padding 4px 12px, radius 8px, 0.875rem).
- 진행 중 카드 `#EAF1FE` radius 20px. 현황 카드 흰 바탕 1px line radius 20px(아이콘 28px → 라벨 1.0625rem/700 → 값 2.25rem/700 브랜드 색 → 칩). 최근 면접은 카드 없이 줄 목록(아래 1px 선). 빠른 시작 카드 radius 24px, `position: sticky; top: 76px`, 정보 줄 아래 점선, 버튼 min-height 52px radius 12px.

### 9.4 공통 머리 · 기타
- 로고 띠: 흰 바탕(다크 `#0A1030`), 1px `#E6E9F0`, radius 12px, 로고 폭 200px 가운데, hover 테두리 `#B9C6F2`.
- 면접관 머리 카드 `#F7F7F8`(다크 `#212225`) radius 16px, 상세 카드 `#F5F6F8`. 면접 완료 박스 `#F5F8FE` + 1px line radius 20px.
- 분야 배지: 공통 gray, 헬스케어 하늘색(`#E0F2FE`/`#0369A1`), 그 밖 violet. 회차 종합 차트 색: 공통 `#AEB0B6`, 헬스케어 `#38BDF8`, 그 밖 보라.
- 모의 결과 연출: 다크 휴대폰(바탕 `#171719`, radius 28px) 문자 2통이 0.5s · 1.9s 에 등장 → 3s 에 흰 메일 카드(1px `#E1E2E4`, radius 16). 결과 박스 색: 합격 `#F2FFF6`/`#006E25`, 후보 `#F3F5FB`/`#0252DE`, 재도전 필요 `#FFF5F5`/`#B00C0C`. `prefers-reduced-motion` 이면 애니메이션 끔.

### 9.5 반응형
- **640px 하나만** 쓴다(`@media (max-width: 640px)`): 홈 2열 → 1열(sticky 해제), 인사 카드 padding 28px 22px · min-height 0 · 인사 2rem→1.5rem, 현황 카드 값 1.75rem, H1 26px.
- 확인 폭: 1280 · 768 · 420 · 390 · 360px 에서 가로 스크롤이 없어야 한다.

### 9.6 시작 화면
- 컨테이너 radius 16px, padding 56px 24px 40px, min-height 72vh, 가운데 정렬. 라이트 `linear-gradient(180deg, #FFFFFF 0%, #EEF6FF 50%, #D6EAFB 100%)`, 다크 `radial-gradient(ellipse at 50% 30%, #16307F 0%, #0A1030 45%, #05070F 100%)`.
- 로고 `max-width: min(560px,100%)`. 스플래시: 로고 0→1(1s), 문구 1(1.4rem/700, `#10256B`) 0.5s · 문구 2(1rem) 0.8s 에 떠오름, 2.5s 에 사라지고 3.0s 에 본문 등장. 문구와 본문을 같은 grid 칸에 겹쳐 로고가 움직이지 않게. 배경 "아지랑이"(radial-gradient + blur 14px, 3.4s/4.2s 반복, 3.0s 부터 사라짐). reduced-motion 이면 아지랑이 없음 · 1.8s 뒤 본문.
- 메뉴 폭 `min(340px,100%)`, 버튼 min-height 56px. [새 면접 시작] 바탕 `#1F255C`(hover `#2B3378`), [복원] 흰 바탕 · 테두리 `#B9C6F2` · 글자 `#10256B`.

---

## 10. 보안 · 개인정보

- API 키는 `OPENAI_API_KEY` 하나. 로컬은 `.env`(Git 제외), 배포는 Streamlit Secrets. 코드 · 브라우저(HTML · JS) · 화면 · 터미널 · 로그에 키를 쓰지 않는다. `.env.example` 에는 이름만.
- 서버에 사용자 데이터를 저장하지 않는다(DB · 파일 없음). 기록은 브라우저 세션에만 있고, 사용자가 내려받은 Markdown 파일이 유일한 보관본이다.
- 저장 파일에는 닉네임 · 회사 · 내 경험 원문 · 대화 · 답이 들어가므로 내려받기 전에 확인 체크를 받는다(6.8).
- 오류 기록에는 답 · 개인정보 · 키 · 토큰 · AI 응답 원문 · 예외 메시지를 남기지 않는다(8.2).
- AI 가 쓴 글 옆에는 `:material/smart_toy: … 사실과 다를 수 있으니 직접 확인해 주세요.` 고지를 붙이고, 점수는 연습용 모의 평가이며 실제 채용 결과와 무관하다고 표시한다.
- 테스트 · 개발 중에는 실제 API 를 부르지 않는다(키를 빈 값으로 두고 가짜 AI 사용).

---

## 11. 가짜 AI · 테스트

### 11.1 가짜 AI `tests/fake_llm.py`
- `FakeAskJson(script: {name: [응답 dict 또는 LLMError, …]})` — `ask_json` 과 같은 시그니처 `(instructions, user_input, schema, name)`.
- 호출마다 그 name 의 큐에서 앞부터 하나 꺼낸다. `LLMError` 면 그 차례에 raise(실패 흐름 시험).
- 꺼낸 응답을 **그 호출의 schema 로 `jsonschema.Draft202012Validator` 검증** — 맞지 않으면 테스트 실패.
- 준비 안 된 name 이 불리면 `AssertionError("가짜 AI 응답이 준비되지 않은 호출이에요: '{name}'")`.
- `calls` 에 `{name, instructions, user_input}` 기록, `remaining()`.
- 헬퍼: `load(kind)`, `response(kind, case)`(cases 또는 edge_cases, 매번 깊은 사본), `sequence(name)`(interviewer sequences → 응답 목록).
- 모의 응답 데이터: **부록 D 를 `tests/fixtures/ai/{interviewer,evaluation,retry}.json` 으로 그대로 저장**. 형광펜 · 전략용 모의 응답은 테스트에서 dict 로 직접 만든다(HIGHLIGHT_SCHEMA · STRATEGY_SCHEMA 에 맞게).

### 11.2 화면 테스트 패턴 (AppTest)
```python
def setUp(self):
    self.real = llm.ask_json
    os.environ["OPENAI_API_KEY"] = ""          # 진짜가 불려도 '키 없음' 으로 실패하게
def open_app(self, script):
    self.fake = FakeAskJson(script); llm.ask_json = self.fake
    self.at = AppTest.from_file("app.py", default_timeout=60); self.at.run()
def tearDown(self):
    llm.ask_json = self.real
```
- `app.py` 는 `from llm import ask_json` 을 **함수 안이 아니라 모듈 맨 위에서** 하므로 AppTest 가 다시 실행할 때마다 바뀐 `llm.ask_json` 을 가져온다(앱 코드를 테스트용으로 고치지 않는다).
- 화면용 가짜 서버(수동 확인): 별도 실행 파일에서 `llm.ask_json` 을 FakeAskJson 으로 바꾼 뒤 같은 프로세스에서 `streamlit.web.cli.main()` 으로 app.py 를 실행한다(앱 코드 수정 없음, `OPENAI_API_KEY=""`).
- AppTest 로 못 보는 것(대화 상자 안 다운로드, 브라우저 스크립트 · 스크롤 · 애니메이션)은 수동 점검표로 분리한다.

### 11.3 실행
```bash
pip install -r requirements-dev.txt
python -m unittest discover tests      # 실제 OpenAI 호출 없음
```

---

## 12. 단계별 개발 절차

각 단계: **구현 → 완료 조건 확인 → 검증 결과 보고 → 사용자 승인 → 다음 단계.** 앞 단계 테스트가 계속 통과해야 한다.

### 1단계. 개발 환경 · 프로젝트 초기화
- 구현: 2장 폴더 구조, `requirements*.txt`, `.env.example`, `.gitignore`, `.streamlit/config.toml`(부록 B), `prompts.py`(부록 A 그대로), `data/questions.csv`(부록 C, UTF-8 BOM), `data/평가기준_근거.md`(부록 E), `tests/fixtures/ai/*.json`(부록 D), `llm.py`(5.1), `tests/fake_llm.py`(11.1), 빈 `app.py`(제목만).
- 완료 조건: 가상환경 설치 성공, `streamlit run app.py` 로 빈 화면이 뜸, 질문 은행 193행 · 8칸을 읽음, `.env` 가 `.gitignore` 에 있음.
- 검증: `test_fake_ai.py` — 부록 D 의 모든 응답이 해당 스키마(strict)를 통과 · FakeAskJson 큐/실패 주입/미준비 name 동작. `test_llm_errors.py` — `OpenAI` 를 가짜로 바꿔 5.1 표의 예외 → 문구 · kind 확인, 키 없음은 호출 안 함. `test_bank.py` — 칸 · 직군별 분야 · 질문 ID 중복 없음.

### 2단계. 데이터 모델 · 기본 화면
- 구현: 3장 상수 · 회차 레코드 · 세션 초기화, `sync_active` · `load_round`, 닉네임(4.10), 시작 화면(6.2 · 스플래시는 8단계에서 다듬어도 됨), 공통 머리 · GNB(6.3), 홈(6.4, 기록 0개 상태), 화면 이동.
- 완료 조건: 시작 → [새 면접 시작] / [복원] 이동, GNB 5개 버튼 이동, 로고 띠 → 홈, 새로고침하면 시작 화면 · 새 닉네임, 닉네임 수정 규칙.
- 검증: AppTest — 첫 화면 문구 · 버튼, GNB 이동, 닉네임 저장(공백 정규화 · 20자 · 빈칸 무시).

### 3단계. 면접 설정 · 질문 관리
- 구현: 4.1 · 4.2 · 4.3, 그룹 · 회차 번호(4.10 · 3.3), 설정 화면(6.5) 전체, `start_interview`.
- 완료 조건: 공통 면접 = 자기소개 + 공통 1 + 직군 직무 · 경험 · 상황, 분야별 = 공통 2 + 분야 3, 회차 안에 중복 없음, 같은 그룹 지난 질문 회피, mix 는 지난 질문 최대 2개를 같은 자리에, same 두 방식과 불가 안내, 회차 번호가 그룹마다 1부터 이어짐, 회사 키워드 필터, 분야 질문이 없는 직군은 공통만.
- 검증: 단위 테스트(무작위는 numpy 시드 · 여러 번 반복으로 규칙만 확인) + AppTest(설정 → 시작 → 면접 화면에 질문 1).

### 4단계. AI 면접 진행
- 구현: 4.4 · 4.5, 면접 화면 · 사이드바 상태창(6.6), 처음부터 다시, 자동 재시도(5.3), 전달 실패 UI(8.3).
- 완료 조건: 5문제 진행, 꼬리 질문은 질문당 최대 1개(AI 가 계속 true 여도), 막힌 꼬리 질문 문장은 대화에 없음, 이해도 clamp, 끝나면 `면접을 마치겠습니다.` + 완료 박스, 실패하면 답 보관 · 다시 시도 · 답 수정, 처음부터 다시 규칙.
- 검증: AppTest + 가짜 AI 시퀀스 — `probe_one_follow_up`(첫 답만 꼬리 질문), follow_up 항상 true(한도 확인), understanding 150 → 100, `LLMError` 주입 후 [다시 시도] 성공, response_parse 1회 실패 후 자동 재시도로 회복(호출 2번).

### 5단계. 4인 평가 · 결과 화면
- 구현: 4.6 · 4.7 · 평가 요청(`eval_running` 중복 방지), 면접 코칭 · 면접 데이터 목록 · LNB, 평가 기록 탭(6.7 ①: 모의 결과 연출 · 위원 카드 · 답변별 점수 · 만점 예시 · 지난 회차 비교).
- 완료 조건: 검증 실패 응답(위원 누락 · no 0부터 · `"5"` 점수)은 저장 안 됨 + 자동 재시도 1회 + 안내, 범위 밖 정수만 보정, 합계 · 평균 · 판정이 코드 계산, 평가 입력에 질문별 `[보는 점]` 5개, 평가 · 재도전 상황 블록에 경험 대신 `(평가에는 쓰지 않음)`, [평가 확인하기] → 평가 기록 탭 · 그 회차.
- 검증: `validate_evaluation` 코드 단위 테스트(부록 D edge_cases), 판정 경계값(89/90, 8.9/9.0, 69/70), AppTest 로 mixed 평가(종합 65) 화면 · LNB 순서.

### 6단계. 면접 기록 · 재도전
- 구현: 면접 기록 탭 · 회차 종합(6.7 ②), 재도전 탭(6.7 ③), 4.8 · 4.9 전부(실마리 · 위원 코치 피드백 · 형광펜 · 전략 가이드).
- 완료 조건: 재도전 횟수 제한 없음, 최초보다 높은 최고 점수만 종합에 반영, 같은 답 재채점 시 AI 미호출, 채점 실패 답 보관, 실마리 고정 · 다음 실마리, 형광펜 · 전략은 누를 때만 호출하고 세션 캐시, 실패 시 안내.
- 검증: 단위 — `reflected_retry`(낮은 · 같은 · 높은 점수 순서), `pick_clues`, `panel_coaching` 문장, 전략 기준당 2개. AppTest — improved → same → perfect 재도전 흐름, 같은 답 두 번(호출 1번).

### 7단계. Markdown 저장 · 복원
- 구현: 7장 전부, 저장 모달(6.8), 복원 화면(6.9), 미저장 경고(6.3).
- 완료 조건: 진행 중 회차는 저장되지 않음, 저장 → 새로고침 → 복원 시 회차 · 평가 · 재도전 기록 · 점수가 같음, 같은 파일을 다시 올리면 전부 건너뛰고 [면접 기록 보기] 가 보임, 업로드 파일을 X 로 지워도 기록 유지, 손상 파일은 7.5 문구로 거부, 평가 · 재도전 일부 손상은 부분 복원 + 경고, 저장 → 복원 → 저장 JSON 동일.
- 검증: 단위 — 왕복 · 5MB · 데이터 없음 · JSON 깨짐 · 질문 4개 · 모르는 직군 · 재도전 501개 · attempt_id 재부여. AppTest — 복원 후 목록 · 회차 수.

### 8단계. UI 디자인 · 반응형
- 구현: 9장 전부(테마, 전역 CSS, 홈 카드, 로고 띠, 시작 화면 스플래시 · 아지랑이, 모의 결과 연출, 형광펜 색, 다크 모드 팔레트 전환, 640px 규칙).
- 완료 조건: 라이트 · 다크 모두 글자가 읽힘, 1280 · 768 · 420 · 390 · 360px 에서 가로 스크롤 없음 · 홈 2열 ↔ 1열, 이모지 없음, reduced-motion 존중.
- 검증: 가짜 AI 서버(11.2)로 각 화면을 열어 폭별 스크린샷(Playwright 등) — 결과를 사용자에게 보여 주고 승인받는다.

### 9단계. 오류 처리 · 통합 테스트
- 구현: `error_log.py`(8.2), 모든 AI 호출 · 복원의 오류 기록 연결, 8.3 표 점검, 수동 점검표(`tests/manual_checklist.md`: 화면별 확인 방법 · 기대 결과 · 자동/수동 구분).
- 완료 조건: 오류 기록에 답 · 키 · 응답 원문이 없음, 파일 기록은 환경 변수가 켜졌을 때만, 기록 실패가 화면을 막지 않음, 전체 흐름(설정 → 면접 → 평가 → 재도전 → 저장 → 새로고침 → 복원) 통과.
- 검증: `python -m unittest discover tests` 전체 통과(실제 API 호출 0회), 민감정보 차단 테스트, 통합 AppTest 1개 이상, 수동 점검표 실시 결과를 사용자에게 보고(실시하지 않은 항목은 "미실시").

---

## 13. 실행 · 배포

### 13.1 로컬
```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # Windows: copy .env.example .env
# .env 에 OPENAI_API_KEY=… 를 넣는다 (키는 공유 · 커밋 금지)
streamlit run app.py                 # http://localhost:8501
```
- 실제 AI 로 확인할 때는 호출 수를 정하고 사용자가 직접 실행한다(면접 1회 ≈ 면접관 5~10번 + 평가 1번).

### 13.2 Streamlit Community Cloud
1. 저장소를 GitHub 에 올린다(`.env` 제외 확인).
2. share.streamlit.io → Create app → 저장소 · 브랜치 · Main file path(`app.py` 위치) · Python 3.12.
3. Secrets 에 최상위 값으로:
   ```toml
   OPENAI_API_KEY = "sk-..."
   OPENAI_MODEL = "..."
   ```
4. Deploy. 인증 오류 문구가 보이면 키가 틀렸거나 만료된 것(Secrets 값의 따옴표 · 공백 · 줄바꿈 확인 후 Reboot).

---

## 14. 최종 완료 기준

| # | 기준 | 확인 |
|---|---|---|
| 1 | 1.1 표의 기능이 모두 동작하고 1.2 의 기능은 없다 | 화면 점검 |
| 2 | OpenAI 호출은 `llm.ask_json` 한 곳뿐 | `OpenAI(` 검색 결과 1곳 |
| 3 | 프롬프트 · 스키마는 `prompts.py` 에만, 부록 A 와 글자까지 같다 | 비교 |
| 4 | 질문 5개 · 꼬리 질문 최대 1개 · 합계 · 평균 · 판정 · 범위 보정은 코드가 한다 | 단위 테스트 |
| 5 | 평가 · 재도전 채점 입력에 사전 경험이 들어가지 않는다 | 테스트 |
| 6 | 검증 실패 평가는 저장되지 않고 자동 재요청은 1번뿐 | 테스트 |
| 7 | 재도전 횟수 제한 없음 · 최고 점수만 반영 | 테스트 |
| 8 | 저장 → 새로고침 → 복원 왕복이 같고, 같은 파일 재업로드는 건너뛴다 | 테스트 + 수동 |
| 9 | AI 실패 때 사용자의 답이 사라지지 않는다 | 테스트 |
| 10 | 키 · 답 · AI 응답 원문이 화면 · 터미널 · 로그 · Git 에 없다 | 검색 · 테스트 |
| 11 | 자동 테스트가 실제 API 없이 모두 통과 | `unittest` |
| 12 | 라이트 · 다크, 360~1280px 에서 깨지지 않는다 | 스크린샷 |

---

## 15. 확인 필요 항목 (임의로 정하지 말고 사용자에게 묻는다)

1. **로고 · 파비콘 이미지**: 원본 이미지는 이 문서에 넣을 수 없다. 사용자에게 `logo.png`(라이트, 960×360) · `logo_dark.png`(다크) · `favicon.png`(256×256) 를 받거나, 받기 전에는 글자 로고 "역전 취업코칭" 으로 임시 표시해도 되는지 묻는다.
2. **기본 모델 이름**: 원본은 `gpt-6-luna` 를 기본으로 쓴다. 사용할 계정에서 쓸 수 있는 모델인지 사용자에게 확인하고 `OPENAI_MODEL` 로 정한다(비싼 모델로 바꾸려면 먼저 묻는다).
3. **개발 · PO · 마케팅 면접관 글, 분야 설명(`FIELDS`), 형광펜 · 전략 지시문**: 원본에서도 "사용자 확인 필요" 초안이다. 그대로 쓸지 사용자에게 확인한다(문장은 바꾸지 않는다).
4. **"면접관 선택"**: MVP1 은 직군별 **자동 배정**이다(사용자가 고르는 UI 없음). 선택 UI 가 필요하다는 요청이 있으면 범위 밖이므로 확인한다.
5. **옛 v1 리포트 파일 복원**: 원본 앱은 이전 버전(v1) 리포트 파일도 읽지만, 새로 만드는 앱에는 v1 파일이 없으므로 이 문서는 v2 만 다룬다. 원본 앱에서 저장한 v1 파일을 옮겨 와야 하는지 확인한다.
6. **원본 앱 저장 파일과의 호환**: 원본 v2 파일에는 이 문서에서 뺀 옛 기능 칸(`last_suggest`, `last_question`, `practice`, `past_hidden`, `extra`)이 들어 있을 수 있다. 원본 앱 파일을 복원해야 하면 이 칸들을 **무시하되 다시 저장할 때 보존할지** 확인한다.
7. **회사 · 회차 ID 규칙**: `company_id`(sha1) · `round_id`(uuid) 규칙은 원본에서도 "임시 규칙"으로 표시되어 있다. 그대로 쓸지 확인한다.
8. **모의 결과 연출 · 회차 종합 차트의 세부 모양**: 이 문서는 구조 · 문구 · 색 · 타이밍만 정한다. 픽셀 단위로 원본과 같아야 하는지 확인한다.
9. **사람이 읽는 저장 본문의 세부 문구**(7.2): 복원에는 쓰이지 않는다. 구조만 맞추면 되는지 확인한다.
10. **실제 AI 응답 품질**: 원본에서도 실제 API 품질 점검 결과 기록이 없다. 완성 후 실제 API 로 몇 번 확인할지(호출 수 · 비용) 사용자가 정한다.

---

## 부록 안내
- **부록 A** `prompts.py` — MVP1 에서 쓰는 프롬프트 · 스키마 원문 (그대로 저장)
- **부록 B** `.streamlit/config.toml` — 테마 (그대로 저장)
- **부록 C** `data/questions.csv` — 질문 은행 193행 (그대로 저장, UTF-8 BOM)
- **부록 D** `tests/fixtures/ai/*.json` — 모의 AI 응답 (그대로 저장)
- **부록 E** `data/평가기준_근거.md` — 평가 기준 근거 (그대로 저장, 평가 화면 펼침에서 보여 줌)

---

## 부록 A — `prompts.py` (그대로 저장)

원본 `prompts.py` 에서 MVP1 이 쓰는 값만 원문 그대로 옮겼다 (주석 한 줄씩은 설명용).

```python
# 프롬프트 문자열과 JSON 스키마만 둔다. 문장은 바꾸지 않는다.

# 직군별 면접관 글. {persona} 에 들어간다. (개발 · PO · 마케팅은 원본에서도 '사용자 확인 필요' 초안)
PERSONAS = {
    # 개발 · PO · 마케팅: Claude Code 초안 — 사용자 확인 필요 (MVP1 직군별 대표 면접관 1명, 디자인 문장과 같은 꼴)
    "개발": "6년 차 백엔드 · 프론트엔드 개발 팀장 (역할). 문제 해결 과정 · 코드 품질과 테스트 습관 · 기술 선택의 근거 · "
            "협업(코드 리뷰 · 기획 · 디자인과의 소통) · 장애나 버그를 끝까지 추적한 경험 · 자신의 업무에 대한 ownership 을 꼭 본다. "
            "말투는 차분하고 담백하며, 사용한 기술을 왜 골랐는지와 결과를 숫자나 근거로 확인할 수 있는지를 자주 묻는다.",
    "디자인": "7년 차 디자인 팀장 (역할). 사용자 경험 · 사용성 · UI 디자인 툴 숙련도(Figma, Photoshop, illustrator) · 모바일 앱/웹 프론트 프로토타이핑 역할 · 컨셉과 맥락에 맞는 완성도있는 그래픽 역량 능력 · 디자인 트렌드를 꾸준히 연구하고 영감을 줄 수 있는지 · 다양한 팀의 조직원들과 원활한 소통이 가능한지 · 자신의 업무에 대한 ownership 을 꼭 본다. 말투는 딱딱한 말투 이고 생성형 AI 능력과 앱/웹 기반 사용 서비스 경험과 사용자조사 데이터를 근거로 꾸준하고 적극적인 서비스 개선 경험 을 자주 묻는다.",
    "PO": "7년 차 프로덕트 오너 (역할). 사용자 문제 정의 · 데이터와 근거로 우선순위를 정하는 능력 · 가설과 지표 설정 · "
          "개발 · 디자인 · 비즈니스 이해관계자와의 조율 · 출시 뒤 결과를 확인하고 개선한 경험 · 자신의 업무에 대한 ownership 을 꼭 본다. "
          "말투는 논리적이고 정중하며, 어떤 근거로 그 결정을 했는지와 성과를 어떤 지표로 확인했는지를 자주 묻는다.",
    "마케팅": "6년 차 퍼포먼스 · 브랜드 마케팅 팀장 (역할). 타깃 고객 이해 · 캠페인 기획과 실행 · 채널별 성과 지표 해석 · "
              "실험(A/B 테스트)으로 개선한 경험 · 예산과 일정 관리 · 유관 부서와의 협업 · 자신의 업무에 대한 ownership 을 꼭 본다. "
              "말투는 밝지만 단호하며, 캠페인 결과를 숫자로 설명할 수 있는지와 실패에서 무엇을 바꿨는지를 자주 묻는다.",
}

# 직군별 대표 면접관 (MVP1: 직군마다 1명 자동 배정). 타입이 없는 직군은 PERSONAS 글을 probe 로 쓴다.
PERSONA_TYPES = {
    "디자인": {
        "디자인 팀장": {"persona": PERSONAS["디자인"], "style": "probe"},
    },
}

# 설정 화면 '면접관 자세히 보기' 카드 (화면 표시용 · AI 에 들어가지 않음)
PERSONA_CARDS = {
    "디자인": {
        "디자인 팀장": {
            "평가 항목": [
                "사용자 경험 · 사용성 · UI 디자인 툴 숙련도",
                "컨셉과 맥락에 맞는 완성도있는 그래픽 역량 능력",
                "모바일 앱/웹 프론트 프로토타이핑 역할",
            ],
            "주목하는 인재상": [
                "트렌드를 꾸준히 연구해 영감을 발굴하는 역량",
                "다양한 팀의 조직원들과 원활한 소통 역량",
                "자신의 업무에 대한 ownership",
            ],
            "성격": [
                "원리 원칙을 중시해 첫 인상은 딱딱해 보일 수 있으나 알고보면 다정한 성격, 불필요한 말은 하지 않고 그냥 넘어가는 편이다.",
            ],
            "평가 포인트": [
                "실제 서비스 개선 경험 과정 확인",
                "협업을 위한 생성형 AI, 바이브코딩 능력은 기초 능력이라고 생각하며 문제정의 능력을 중시한다.",
            ],
        },
    },
}

# 분야 설명. CONTEXT 의 {field_desc}
FIELDS = {
    "공통": "특정 분야를 정하지 않음",
    "헬스케어": "병원 · 환자 · 건강 데이터를 다루는 서비스. 개인정보 · 의료 규제와 안전성을 중요하게 본다",
    "핀테크 · 금융": "송금 · 결제 · 투자처럼 돈을 다루는 서비스. 보안 · 신뢰 · 규제 준수를 중요하게 본다",
    "커머스": "상품 탐색 · 구매 · 배송을 다루는 서비스. 전환율 · 재구매 같은 지표를 중요하게 본다",
    "에듀테크": "학습 · 교육 콘텐츠를 다루는 서비스. 학습 효과와 꾸준한 사용을 중요하게 본다",
    "모빌리티 · 여행": "이동 · 예약 · 위치를 다루는 서비스. 실시간성 · 안전 · 현장 경험을 중요하게 본다",
    "콘텐츠 · 미디어": "영상 · 음악 · 글 같은 콘텐츠를 다루는 서비스. 몰입 · 추천 · 창작자 생태계를 중요하게 본다",
    "B2B · SaaS": "기업 고객의 업무를 돕는 서비스. 생산성 · 도입 과정 · 운영 효율을 중요하게 본다",
    "게임": "게임 플레이와 운영을 다루는 서비스. 재미 · 리텐션 · 커뮤니티를 중요하게 본다",
}

# 상황 블록. 평가 · 재도전 채점에서는 {experience} 에 '(평가에는 쓰지 않음)'
CONTEXT = """- 회사: {company} ({company_desc})
- 분야: {field} ({field_desc})
- 지원 직군: {job} 신입
- 지원자가 직접 적은 경험: {experience}"""

# 면접관 지시문. user_input = format_transcript(대화)
INTERVIEWER = """너는 아래 페르소나의 면접관이야. 지금은 모의면접이고, 지원자를 돕는 게 아니라 실제처럼 확인하는 역할이야.
페르소나: {persona}
{context}
[이번 질문] {question}
[이 질문에서 보는 점] {point}
[규칙]
1. 지원자의 마지막 답에 대한 반응은 지원자가 실제로 말한 내용에 근거한 짧은 문장만. 칭찬이나 정답 알려 주기는 하지 마.
2. 답이 [보는 점]을 충분히 보여 주지 않으면 follow_up 을 true 로, 꼬리 질문 1개를 reply 에. 충분하면 false.
3. 꼬리 질문은 한 번에 하나, 200 자 이내.
4. 꼬리 질문은 [이번 질문]의 [보는 점]에서 벗어나지 마. 페르소나가 자주 묻는 주제도 [보는 점]과 관련 있을 때만 묻는다.
5. 실제로 해 본 경험과 가정형 대응('~하겠습니다', '~할 것 같습니다')을 구분해. 가정형 답을 실제 경험으로 보지 마.
   가정형 답에는 판단 기준 · 실행 방법 · 예상되는 어려움을 구체화하는 꼬리 질문을 먼저 고려해.
   실제 경험을 확인하는 꼬리 질문은 [보는 점]을 확인하는 데 필요할 때만.
6. 수치 · 성과는 [보는 점]과 관련 있을 때만 묻는다. 지원자가 실제 결과를 말했으면 그 결과를 어떻게 확인했는지,
   결과 없이 계획만 말했으면 앞으로 어떻게 검증할지를 묻는다. 실제 결과와 검증 계획을 섞지 마.
7. 지원자가 말하지 않은 경험 · 결과 · 성과 · 수치를 사실처럼 말하거나 이미 있는 것처럼 전제하지 마.
8. 지원자가 질문 뜻을 되물으면 정답은 알려 주지 말고, 이 질문이 무엇을 확인하려는지([보는 점])를 쉬운 말로 다시 설명해.
9. understanding 은 지금까지 답으로 본 직무 이해도 0~100.
출력은 JSON 하나만: reply(글), follow_up(참/거짓), understanding(숫자)"""

INTERVIEWER_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "follow_up": {"type": "boolean"},
        "understanding": {"type": "integer"},
    },
    "required": ["reply", "follow_up", "understanding"],
    "additionalProperties": False,
}

# 평가 위원회 지시문. user_input = format_record(질문 · 보는 점 · 대화)
EVALUATOR = """너는 모의면접 평가 위원회야. 아래 면접 기록을 4명의 눈으로 따로 본 뒤 합쳐.
위원: 실무 전문가 · 논리 분석가 · 커뮤니케이션 전문가 · 채용 담당자
[위원별 평가 기준]
{panel_criteria}
{context}
[평가 순서 — 이 순서를 지켜]
1. 위원마다: 먼저 '이 지원자를 뽑지 말아야 할 이유' 1문장(반론 먼저), 그다음 좋은 점 1문장, 0~10점.
2. 4명을 비교해 conflict(판단이 갈린 곳) · agree(모두 같은 판단) 각 1문장.
3. 답변마다 기준 4개(구체성 / 직무 연관 / 구조 / 근거 · 검증)를 각각 0~5점. 가장 약한 점 하나를 weak 에.
4. 답변마다 rewrite: 같은 경험으로 더 좋은 답 300자 문장 이내.
   지원자가 쓰지 않은 숫자 · 회사 · 성과는 넣지 마. 꼭 필요하면 [확인 필요: ○○].
   check 에 사람이 확인할 사실 0~2개.
5. next 에 다음 연습에서 고칠 것 3개.
[보는 점] 면접 기록의 질문마다 붙은 [보는 점]은 질문의 평가 의도를 이해하기 위한 참고 기준입니다.
특정 키워드의 포함 여부만으로 판단하지 말고, 답변의 내용과 근거, 문제 해결 접근 방식의 타당성을 종합적으로 평가하세요.
출력은 JSON 하나만. 점수 합계는 쓰지 마 (앱이 계산해)."""

# 재도전 채점 지시문. user_input = 다시 쓴 답
RETRY = """너는 모의면접 채점자야. 지원자가 같은 질문에 다시 쓴 답을 채점해.
페르소나: {persona}
{context}
[질문] {question}
[이 질문에서 보는 점] {point}
[지난 답] {before}
[지난 답의 약한 점] {weak}
[규칙]
1. 다시 쓴 답만 채점한다. 지난 답은 무엇이 바뀌었는지 비교할 때만 본다.
2. 기준 4개(구체성 / 직무 연관 / 구조 / 근거 · 검증)를 각각 0~5점. 평가 위원회와 같은 기준으로 본다.
3. 지난 답보다 나아졌다는 이유만으로 점수를 올리지 마. 다시 쓴 답 자체로 판단해.
4. 다시 쓴 답에서 가장 약한 점 하나를 weak 에 1문장.
5. 지원자가 쓰지 않은 경험 · 숫자를 사실처럼 말하지 마.
6. weak 는 위 페르소나의 말투로 쓴다.
출력은 JSON 하나만. 점수 합계는 쓰지 마 (앱이 계산해)."""

RETRY_SCHEMA = {
    "type": "object",
    "properties": {
        "specific": {"type": "integer"},
        "relevance": {"type": "integer"},
        "structure": {"type": "integer"},
        "evidence": {"type": "integer"},
        "weak": {"type": "string"},
    },
    "required": ["specific", "relevance", "structure", "evidence", "weak"],
    "additionalProperties": False,
}

# 형광펜 지시문. user_input = build_highlight_input(번호 붙인 문장). 화면 범례도 [기준] 줄을 읽어 만든다
HIGHLIGHT = """너는 모의면접 답변 분석가야. 지원자 답의 문장마다 어떤 평가 기준과 연결되는지 표시해.
{context}
[기준]
- specific(구체성): 상황 · 행동 · 숫자 · 사례가 구체적인 문장
- relevance(직무 연관): 지원 직군 · 회사 업무와 연결되는 문장
- structure(구조): 답의 흐름을 잡는 문장 (결론 먼저, 순서, 정리)
- evidence(근거 · 검증): 데이터 · 테스트 · 피드백 · 확인 방법을 말하는 문장
[규칙]
1. 입력의 [질문] 과 [보는 점] 을 기준으로, 번호 붙은 문장을 하나도 빠짐없이 본다. no 는 입력의 번호 그대로.
2. tags 는 해당하는 기준 0~4개. 해당하는 기준이 없으면 빈 목록.
3. why 에 그렇게 본 이유 1문장.
4. 지원자가 쓰지 않은 내용을 지어내지 마.
출력은 JSON 하나만."""

HIGHLIGHT_SCHEMA = {
    "type": "object",
    "properties": {
        "sentences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "no": {"type": "integer"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["specific", "relevance", "structure", "evidence"]},
                    },
                    "why": {"type": "string"},
                },
                "required": ["no", "tags", "why"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["sentences"],
    "additionalProperties": False,
}

# 전략 가이드 지시문. user_input = 지원자 답
STRATEGY = """너는 모의면접 코치야. 지원자의 답이 20점 만점에 가까워지도록 고칠 전략을 알려 줘.
지원자의 답은 입력으로 줄게.
{context}
[질문] {question}
[이 질문에서 보는 점] {point}
[기준별 점수 (각 0~5)]
{scores}
[위원회 종합 의견]
{opinion}
[규칙]
1. 5점이 아닌 기준마다 전략 1~2개. 5점인 기준은 쓰지 마.
2. action 은 추가 · 수정 · 축약 · 삭제 중 하나.
3. target 에 내 답에서 고칠 부분을 짧게 그대로 옮겨 적어. 추가라면 빈 글.
4. tip 은 "~을 추가해 보세요" · "~을 수정해 보세요" · "~을 축약해 보세요" 처럼 한 문장, 120 자 이내.
5. 지원자가 쓰지 않은 경험 · 숫자를 지어내지 마. 꼭 필요하면 [확인 필요: ○○].
출력은 JSON 하나만. 점수는 쓰지 마 (앱이 계산해)."""

STRATEGY_SCHEMA = {
    "type": "object",
    "properties": {
        "tips": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string", "enum": ["specific", "relevance", "structure", "evidence"]},
                    "action": {"type": "string", "enum": ["추가", "수정", "축약", "삭제"]},
                    "target": {"type": "string"},
                    "tip": {"type": "string"},
                },
                "required": ["criterion", "action", "target", "tip"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["tips"],
    "additionalProperties": False,
}

PANEL_ROLES =["실무 전문가", "논리 분석가", "커뮤니케이션 전문가", "채용 담당자"]

# 위원별 평가 기준. EVALUATOR 의 {panel_criteria} 와 화면이 같이 쓴다
PANEL_CRITERIA = {
    "실무 전문가": "직무 지식 · 툴 숙련도, 실제 업무에 바로 쓸 수 있는 경험인가",
    "논리 분석가": "문제 → 원인 → 해결 → 결과 흐름이 맞고, 주장과 근거가 연결되는가",
    "커뮤니케이션 전문가": "결론부터 간결하게 말하고, 질문 의도에 맞게 답하는가",
    "채용 담당자": "회사 · 직무 적합성, 협업 태도, 성장 가능성",
}

EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "panel": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "enum": PANEL_ROLES},
                    "against": {"type": "string"},
                    "good": {"type": "string"},
                    "score": {"type": "integer"},
                },
                "required": ["role", "against", "good", "score"],
                "additionalProperties": False,
            },
        },
        "conflict": {"type": "string"},
        "agree": {"type": "string"},
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "no": {"type": "integer"},
                    "specific": {"type": "integer"},
                    "relevance": {"type": "integer"},
                    "structure": {"type": "integer"},
                    "evidence": {"type": "integer"},
                    "weak": {"type": "string"},
                    "rewrite": {"type": "string"},
                    "check": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "no", "specific", "relevance", "structure",
                    "evidence", "weak", "rewrite", "check",
                ],
                "additionalProperties": False,
            },
        },
        "next": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["panel", "conflict", "agree", "answers", "next"],
    "additionalProperties": False,
}
```

---

## 부록 B — `.streamlit/config.toml` (그대로 저장)

```toml
# 몽타주(Montage) 디자인 시스템 — 원티드랩, MIT 라이선스
# 출처: https://github.com/wanteddev/montage-web (packages/theme/src/theme/atomic · semantic)
# 바탕 · 글자 · 테두리 · 상태 색 · 글꼴 · 모서리는 몽타주 값 그대로, 이름 옆 괄호는 팔레트 번호.
# 2026-11 MVP1 디자인 시스템 (prd/design.md): 브랜드 #0252DE · 글자 #0B1020 · 보조 글자 #444D63 · Pretendard.
# 글꼴: Pretendard (SIL OFL 1.1) — https://github.com/orioncactus/pretendard (가변 글꼴, 동적 서브셋)

[theme]
font = "Pretendard Variable:https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
headingFont = "Pretendard Variable:https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
# 글자 체계: 당근(about.daangn.com) 크기 · 굵기.
# 줄간격 · 자간 · 좁은 화면 H1 크기는 app.py hover_css 에 있다.
headingFontSizes = ["30px", "24px", "20px", "18px", "16px", "14px"]  # 서비스 안 H1 24~32px
headingFontWeights = [700, 700, 700, 600, 600, 600]  # H1 ~ H3 700 (당근은 제목을 모두 Bold), H4 이하 600
baseFontSize = 16
baseRadius = "8px"      # radius md
buttonRadius = "10px"   # 버튼 medium
showWidgetBorder = true

[theme.light]
primaryColor = "#0252DE"              # 브랜드 블루 · 흰 글자 대비 6.0
backgroundColor = "#FFFFFF"           # common 100
secondaryBackgroundColor = "#F7F7F8"  # coolNeutral 99
textColor = "#0B1020"                 # 기본 글자
linkColor = "#0252DE"
borderColor = "#E1E2E4"               # coolNeutral 96
blueColor = "#0252DE"                 # 안내 상자도 브랜드 블루 계열로
blueBackgroundColor = "#EAF1FE"
blueTextColor = "#0242B2"
greenColor = "#00BF40"                # green 50
greenBackgroundColor = "#D9FFE6"      # green 95
greenTextColor = "#006E25"            # green 30
orangeColor = "#FF9200"               # orange 50
orangeBackgroundColor = "#FEF4E6"     # orange 95
orangeTextColor = "#9C5800"           # orange 30
redColor = "#FF4242"                  # red 50
redBackgroundColor = "#FEECEC"        # red 95
redTextColor = "#B00C0C"              # red 30
grayColor = "#70737C"                 # coolNeutral 50
grayBackgroundColor = "#F4F4F5"       # coolNeutral 98
grayTextColor = "#444D63"             # 보조 글자

[theme.dark]
primaryColor = "#3D7BFF"              # 브랜드 블루를 어두운 바탕용으로 밝힘
backgroundColor = "#1B1C1E"           # coolNeutral 15
secondaryBackgroundColor = "#212225"  # coolNeutral 17
textColor = "#F7F7F8"                 # coolNeutral 99
linkColor = "#8DB4FF"
borderColor = "#37383C"               # coolNeutral 25
blueColor = "#6E9DFF"
blueBackgroundColor = "#14244A"
blueTextColor = "#A9C6FF"
greenColor = "#1ED45A"                # green 60
greenBackgroundColor = "#1C3928"
greenTextColor = "#49E57D"            # green 70
orangeColor = "#FFA938"               # orange 60
orangeBackgroundColor = "#403322"
orangeTextColor = "#FFC06E"           # orange 70
redColor = "#FF6363"                  # red 60
redBackgroundColor = "#3F2729"
redTextColor = "#FF8C8C"              # red 70
grayColor = "#878A93"                 # coolNeutral 60
grayBackgroundColor = "#292A2D"       # coolNeutral 20
grayTextColor = "#C2C4C8"             # coolNeutral 90

[theme.dark.sidebar]
backgroundColor = "#0F0F10"           # coolNeutral 5
```

---

## 부록 C — `data/questions.csv` (그대로 저장 · UTF-8 BOM · 헤더 + 193행)

이 블록 안의 글을 `encoding="utf-8-sig"` 로 저장한다. 칸 안 쉼표 · 따옴표는 CSV 규칙대로 큰따옴표로 감싸져 있다.

```csv
직군,분야,유형,질문,보는 점,만점 예시,회사 키워드,질문 ID
공통,공통,공통,1분 동안 자기소개를 해 주세요.,핵심 경험 1~2개를 직무와 연결하는가,"저는 '관찰로 문제를 찾고 숫자로 확인하는' 프로덕트 디자이너입니다. 졸업 프로젝트에서 동네 병원 예약 앱의 이탈 지점을 사용성 테스트 8명으로 찾았고, 예약 단계를 5개에서 3개로 줄여 완료율을 58%에서 79%로 올렸습니다. 인턴 때는 디자인 시스템 버튼 컴포넌트 12종을 정리해 개발 문의를 주 9건에서 3건으로 줄였습니다. 이 두 경험으로 [회사]의 핵심 흐름을 더 쉽게 만드는 데 기여하고 싶습니다.",,Q0001
공통,공통,공통,우리 회사에 지원한 이유가 무엇인가요?,회사·서비스를 알고 있는가 · 내 경험과 연결하는가,"[회사]의 [핵심 서비스]가 '처음 쓰는 사람도 막히지 않는 흐름'을 가장 중요하게 다루는 서비스라서 지원했습니다. 지원 전에 앱을 2주 동안 직접 쓰며 가입부터 결제까지 14단계를 기록했고, 리뷰 300개를 분류해 보니 불만의 40%가 [특정 단계]에 몰려 있었습니다. 저는 예약 앱 프로젝트에서 비슷한 이탈 문제를 테스트로 찾아 완료율을 21%p 올린 경험이 있습니다. 이 방식으로 [특정 단계]를 개선하는 일을 맡고 싶습니다.",,Q0002
공통,공통,공통,AI를 업무에 쓴 경험을 하나 말해 주세요. AI가 틀린 적은 없었나요?,AI 결과를 확인·검증하는 습관이 있는가,"네, 사용성 테스트 결과 정리에 AI를 쓰다가 틀린 요약을 잡아낸 적이 있습니다. 인터뷰 10명분 메모를 AI로 요약했더니 '가격 불만'이 1순위로 나왔지만, 원문을 다시 세어 보니 가격은 3명이고 '메뉴를 못 찾음'이 7명이었습니다. 그 뒤로는 AI 요약마다 원문 번호를 붙이게 하고, 상위 3개 주장은 원문과 직접 대조합니다. 덕분에 개선 우선순위를 바로잡아 메뉴 구조부터 고쳤고, 재테스트에서 과제 성공률이 60%에서 90%가 됐습니다.",,Q0003
공통,공통,공통,팀원과 의견이 크게 달랐던 경험과 어떻게 풀었는지 말해 주세요.,갈등을 사실 · 대화 · 결과로 설명하는가,"팀 프로젝트에서 개발 팀원과 '탭 구조냐, 한 화면 스크롤이냐'로 크게 부딪혔고, 테스트로 결정해 풀었습니다. 먼저 서로의 근거를 표로 적어 보니 저는 탐색성, 팀원은 구현 일정을 걱정하고 있었습니다. 그래서 두 안을 프로토타입으로 만들어 5명에게 같은 과제 3개를 줬고, 탭 구조가 과제 시간 평균 42초로 스크롤안보다 18초 빨랐습니다. 구현은 팀원 제안대로 기존 컴포넌트를 재사용해 일정도 지켰고, 이후 의견이 갈리면 '작게 테스트하기'를 팀 규칙으로 정했습니다.",,Q0004
개발,공통,직무,최근에 만든 서비스에서 가장 어려웠던 기술 문제와 해결 과정을 설명해 주세요.,문제 → 원인 → 시도 → 결과가 구체적인가,,,Q0005
개발,공통,직무,API 키 같은 비밀 값을 코드에서 어떻게 관리하나요?,.env · Secrets · gitignore 를 이해하는가,,,Q0006
개발,공통,직무,AI가 짜 준 코드를 그대로 쓰지 않고 확인하는 방법은 무엇인가요?,실행 · 테스트 · 리뷰 기준이 있는가,,,Q0007
개발,공통,직무,코드 리뷰에서 지적을 받았을 때 어떻게 반영하나요?,피드백 수용 · 근거 있는 반론,,,Q0008
개발,공통,경험,Git으로 협업하면서 충돌(conflict)을 해결한 경험이 있나요?,브랜치 · PR · 충돌 해결 흐름을 아는가,,,Q0009
개발,공통,경험,버그를 찾느라 오래 걸렸던 경험과 다음부터 바꾼 습관을 말해 주세요.,재발 방지 · 학습,,,Q0010
개발,공통,상황,배포 직전에 다른 팀원의 코드에서 큰 버그를 발견했다면 어떻게 하나요?,우선순위 · 소통 · 일정 판단,,,Q0011
개발,공통,상황,기획자가 이틀 안에 불가능해 보이는 기능을 요청하면 어떻게 대화하나요?,대안 제시 · 범위 조정,,,Q0012
디자인,공통,직무,포트폴리오에서 가장 자신 있는 화면 하나를 골라 설계 과정을 설명해 주세요.,문제 정의 → 리서치 → 시안 → 검증 흐름,"가장 자신 있는 화면은 동네 병원 예약 앱의 '시간 선택' 화면입니다. 문제는 사용자가 빈 시간을 찾으려고 날짜를 평균 6번 넘겨 본다는 것이었고, 로그와 인터뷰 6명으로 확인했습니다. 그래서 날짜별 남은 자리 수를 달력에 바로 보여 주는 안 등 시안 3개를 만들었고, 정보가 많은 안과 아이콘만 쓴 안은 테스트에서 오해가 많아 버렸습니다. 최종안은 과제 시간을 51초에서 23초로 줄였고, 출시 후 예약 완료율이 58%에서 79%로 올랐습니다.",,Q0013
디자인,공통,직무,사용성 테스트를 어떻게 준비하고 결과를 어떻게 반영했나요?,과제 설계 · 관찰 · 우선순위,"사용성 테스트는 '무엇을 결정하려는지'를 먼저 정하고, 결과는 심각도와 빈도로 우선순위를 매겨 반영합니다. 예약 앱 테스트에서는 '예약 완료까지 막히는 곳'을 결정 질문으로 두고, 실제 상황을 담은 과제 4개와 참가자 8명을 준비했습니다. 관찰 중에는 말보다 행동을 기록했고, 문제 11개를 '과제 실패 · 지연 · 불편' 3단계로 나눴습니다. 과제 실패를 만든 3개를 먼저 고쳐 재테스트했고, 성공률이 62%에서 94%로 올랐습니다.",,Q0014
디자인,공통,직무,디자인 시스템이나 컴포넌트를 만들거나 써 본 경험이 있나요?,일관성 · 재사용 · 협업 관점,"네, 인턴 때 흩어져 있던 버튼을 컴포넌트로 정리해 디자인 시스템에 넣은 경험이 있습니다. 화면 40개를 점검하니 같은 역할의 버튼이 27가지 모양으로 쓰이고 있었고, 이를 크기 3개 · 종류 4개, 총 12종으로 줄였습니다. 이름과 상태(기본 · 눌림 · 비활성)를 개발자와 같은 용어로 맞추고 문서에 쓰임 예시를 붙였습니다. 그 뒤 버튼 관련 개발 문의가 주 9건에서 3건으로 줄었고, 새 화면 시안 시간도 평균 30% 빨라졌습니다.",,Q0015
디자인,공통,직무,AI 도구로 시안을 만들 때 어떤 부분은 사람이 꼭 판단해야 한다고 보나요?,AI 활용 기준 · 저작권 · 브랜드 감각,"AI는 시안의 폭을 넓히는 데 쓰고, 문제 정의 · 브랜드 적합성 · 저작권 · 접근성은 사람이 꼭 판단해야 한다고 봅니다. 실제로 배너 작업에서 AI로 시안 20개를 빠르게 만들었지만, 그중 6개는 브랜드 색 규칙을 벗어났고 2개는 실존 캐릭터와 비슷해 저작권 위험이 있었습니다. 그래서 '브랜드 가이드 · 출처 확인 · 대비 4.5:1' 체크리스트를 통과한 시안만 검토에 올렸습니다. 이렇게 하니 시안 준비 시간은 절반으로 줄고, 검토에서 반려되는 시안은 없었습니다.",,Q0016
디자인,공통,경험,개발자와 구현 방식 때문에 부딪힌 경험과 해결 방법을 말해 주세요.,협업 · 타협 · 근거,"구현이 어렵다는 개발자 의견을 먼저 구체적으로 듣고, 디자인의 목적은 지키면서 구현 방법을 바꿔 해결했습니다. 화면 전환 애니메이션이 일정 안에 어렵다고 해서, 어디가 어려운지 물어보니 커스텀 경로 계산이 문제였습니다. 저는 이 전환의 목적이 '사용자가 어디로 이동했는지 알게 하기'라고 공유하고, 기본 슬라이드 전환에 위치 표시를 더하는 안을 함께 골랐습니다. 구현 시간은 3일에서 반나절로 줄었고, 사용성 테스트 6명 모두 이동 위치를 바로 이해했습니다.",,Q0017
디자인,공통,경험,데이터나 사용자 피드백 때문에 내 디자인을 크게 바꾼 경험이 있나요?,근거 기반 의사결정,"네, 필터 디자인을 데이터와 사용자 피드백을 보고 크게 바꾼 경험이 있습니다. 화면을 깔끔하게 하려고 필터를 아이콘만으로 만들었는데, 출시 2주 동안 필터 사용률이 3%에 그쳤습니다. 사용자 5명을 인터뷰하니 4명이 아이콘 뜻을 몰랐고, 저는 제 가정이 틀렸다고 판단했습니다. 글자 라벨을 붙이고 자주 쓰는 필터 2개를 밖으로 꺼냈더니 2주 뒤 사용률이 19%로 올랐고, 검색 후 이탈도 12% 줄었습니다.",,Q0018
디자인,공통,상황,대표님이 근거 없이 '더 고급스럽게'만 요청하면 어떻게 하나요?,모호한 요청을 구체화하는 질문,"먼저 '고급스럽다'를 구체적인 기준으로 바꾸는 질문을 하고, 비교 시안으로 합의합니다. 대표님께 '고급스럽게 느끼는 브랜드 3개', '지금 화면에서 가장 아쉬운 곳', '이 변화로 기대하는 결과'를 묻습니다. 답이 '여백과 사진 품질'로 모이면 여백 · 글꼴 · 사진 톤만 바꾼 A/B 시안 2개를 만들어 고객 5명에게 인상 평가를 받습니다. 실제 프로젝트에서 이렇게 해서 수정 요청 횟수를 6번에서 2번으로 줄였고, 랜딩 체류 시간도 15% 늘었습니다.",,Q0019
디자인,공통,상황,출시 3일 전에 접근성(글자 대비) 문제가 발견되면 어떻게 하나요?,우선순위 · 최소 수정안,"꼭 거쳐야 하는 화면부터 우선순위를 매기고, 색 토큰을 바꾸는 최소 수정으로 3일 안에 막습니다. 먼저 대비 검사 도구로 전체 화면을 돌려 기준 4.5:1에 못 미치는 곳을 목록으로 만들고, 가입 · 결제처럼 출시 기능의 핵심 경로를 1순위로 둡니다. 문제의 대부분이 회색 글자 토큰 하나에서 나왔다면, 그 토큰만 바꿔 여러 화면을 한 번에 고칠 수 있는지 개발자와 확인합니다. 남은 곳은 다음 배포 일정과 함께 팀에 공유해 출시 후 1주 안에 마무리합니다.",,Q0020
PO,공통,직무,최근 서비스나 프로젝트에서 우선순위를 어떻게 정했는지 설명해 주세요.,기준(RICE 등) · 데이터 · 트레이드오프,,,Q0021
PO,공통,직무,VOC가 서로 반대되는 요청을 할 때(알림을 늘려 달라 vs 줄여 달라) 어떻게 판단하나요?,세그먼트 · 근본 원인 · 실험,,,Q0022
PO,공통,직무,기능의 성공을 어떤 숫자로 판단하나요? 예를 들어 설명해 주세요.,지표 정의 · 목표 수치 · 측정 방법,,,Q0023
PO,공통,직무,PRD에 꼭 들어가야 한다고 생각하는 항목과 이유를 말해 주세요.,문제 · 목표 · 범위 · 완료 기준,,,Q0024
PO,공통,경험,계획대로 되지 않은 프로젝트에서 무엇을 배웠나요?,회고 · 책임 · 개선,,,Q0025
PO,공통,경험,개발 · 디자인 · 마케팅 사이에서 의견을 조율한 경험을 말해 주세요.,이해관계자 관리 · 결정 방법,,,Q0026
PO,공통,상황,출시 일정이 2주 밀릴 것 같다는 걸 알게 됐다면 무엇부터 하나요?,범위 조정 · 소통 순서,,,Q0027
PO,공통,상황,대표가 경쟁사 기능을 그대로 따라 만들자고 하면 어떻게 하나요?,문제 중심 사고 · 근거 있는 반론,,,Q0028
마케팅,공통,직무,가장 성과가 좋았던 캠페인이나 콘텐츠를 숫자와 함께 설명해 주세요.,목표 · 지표 · 결과 · 배운 점,,,Q0029
마케팅,공통,직무,광고 카피에 '1위' '100%' 같은 표현을 쓰고 싶다는 요청이 오면 어떻게 하나요?,근거 · 표시광고 감각 · 대안 표현,,,Q0030
마케팅,공통,직무,우리 서비스의 핵심 타깃을 한 명의 페르소나로 설명해 주세요.,구체성 · 근거 · 행동 패턴,,,Q0031
마케팅,공통,직무,A/B 테스트를 설계한다면 무엇을 바꾸고 어떤 숫자로 승자를 정하나요?,변수 하나 · 지표 · 기간,,,Q0032
마케팅,공통,경험,반응이 나빴던 콘텐츠와 그 이유를 어떻게 분석했나요?,원인 가설 · 데이터 확인,,,Q0033
마케팅,공통,경험,AI로 콘텐츠를 만들 때 브랜드 톤을 지키는 방법이 있었나요?,가이드 · 검수 기준,,,Q0034
마케팅,공통,상황,캠페인 예산이 갑자기 절반으로 줄면 어떻게 계획을 바꾸나요?,채널 우선순위 · 효율 판단,,,Q0035
마케팅,공통,상황,인플루언서 협업 콘텐츠에 사실과 다른 표현이 들어갔다면 어떻게 하나요?,빠른 대응 · 정정 · 재발 방지,,,Q0036
디자인,헬스케어,직무,환자나 보호자처럼 건강 정보에 민감한 사용자를 위한 화면을 설계할 때 무엇을 가장 먼저 확인하나요?,개인정보 노출 · 오해 가능성 · 접근성을 고려하는가,"가장 먼저 '정보가 잘못 보이거나 남에게 보일 위험'이 없는지 확인합니다. 화면마다 건강 정보가 잠금 화면 알림 · 공유 화면 · 최근 기록에 노출되는지 점검표 12항목으로 봅니다. 다음으로 수치나 결과를 오해할 수 있는 표현을 찾고, 글자 크기 · 대비 4.5:1 같은 접근성 기준을 확인합니다. 졸업 프로젝트에서 이 순서로 검사 결과 화면을 고쳐, 보호자 6명 테스트에서 결과를 잘못 읽은 사람이 3명에서 0명이 됐습니다.",,Q0037
디자인,헬스케어,상황,진료 예약 화면에서 고령 사용자의 이탈이 많다는 데이터가 나왔다면 어떻게 개선하나요?,데이터 해석 · 사용자 특성 · 개선 검증 방법,"데이터로 이탈 지점을 먼저 좁히고, 고령 사용자와 직접 테스트해 원인을 확인한 뒤 고칩니다. 퍼널을 보면 어느 단계에서 나가는지 알 수 있어서, 예를 들어 '시간 선택' 단계 이탈이 45%라면 그 화면부터 봅니다. 60대 이상 5명에게 예약 과제를 주고 관찰하면 작은 글자 · 작은 버튼 · 낯선 용어 같은 원인이 나옵니다. 글자 18pt · 버튼 48px 이상 · 쉬운 말로 바꾼 뒤 A/B 테스트로 2주간 완료율을 비교해 효과를 확인합니다.",진료/병원/예약/클리닉/의원/검사,Q0038
디자인,핀테크 · 금융,직무,송금이나 결제처럼 실수가 돈과 바로 이어지는 흐름을 설계할 때 어떤 장치를 두나요?,오류 예방 · 확인 단계 · 신뢰감 설계,"실수를 막는 장치, 되돌릴 수 있는 장치, 결과를 확실히 알려 주는 장치 세 가지를 둡니다. 받는 사람 이름 · 은행 · 금액을 큰 글자로 다시 보여 주는 확인 화면을 두고, 평소보다 10배 큰 금액이면 한 번 더 묻습니다. 보낸 직후 짧은 시간 안에 취소할 수 있는 길이나, 그게 어렵다면 문의 경로를 바로 보여 줍니다. 마지막으로 완료 화면에 처리 상태와 거래 번호를 남겨, 프로젝트 테스트에서 '보내졌는지 모르겠다'는 반응을 5명 중 4명에서 0명으로 줄였습니다.",,Q0039
디자인,핀테크 · 금융,상황,보안 인증 단계를 늘리자는 요청과 이탈률이 오른다는 데이터가 부딪히면 어떻게 하나요?,보안과 편의의 균형 · 근거 있는 대안 제시,"보안을 낮추지 않으면서 이탈을 줄이는 대안을 데이터로 비교해 제안합니다. 먼저 이탈이 인증 단계 수 때문인지, 특정 인증 방식(예: 문자 입력) 때문인지 단계별 이탈률로 나눠 봅니다. 그다음 위험도가 높은 거래에만 추가 인증을 거는 방식, 생체 인증으로 입력을 줄이는 방식 같은 안을 보안 담당자와 함께 검토합니다. 두 안을 일부 사용자에게 2주간 실험해 이탈률과 부정 거래 지표를 같이 보고, 둘 다 기준을 지키는 안으로 결정합니다.",,Q0040
디자인,커머스,직무,상품 상세 페이지에서 구매 전환을 높이기 위해 무엇을 먼저 살펴보나요?,전환 지표 이해 · 정보 우선순위 · 실험 설계,"구매를 막는 질문에 답이 바로 보이는지부터 봅니다. 상세 페이지 스크롤 깊이와 클릭 데이터를 보고, 고객 문의 상위 5개(사이즈 · 배송일 · 반품 등)가 화면 어디에 있는지 확인합니다. 예를 들어 배송일 문의가 30%인데 정보가 맨 아래에 있으면, 가격 옆으로 올리는 시안을 만듭니다. 이 변경을 A/B 테스트로 2주간 비교해 구매 전환율과 문의 수가 함께 개선되는지 확인한 뒤 적용합니다.",,Q0041
디자인,커머스,상황,장바구니 이탈률이 갑자기 올랐다면 디자이너로서 원인을 어떻게 찾나요?,퍼널 분석 · 가설 세우기 · 협업,"퍼널 데이터로 언제 · 누구에게서 올랐는지 좁히고, 가설을 세워 하나씩 확인합니다. 먼저 이탈이 오른 날짜와 최근 배포 · 가격 정책 변경을 맞춰 보고, 기기 · 결제 수단별로 나눠 봅니다. 예를 들어 특정 날 배포 뒤 모바일에서만 올랐다면 화면 오류나 배송비 표시 변경을 가설로 두고, 직접 재현하면서 고객센터 문의도 같이 봅니다. 원인을 찾으면 개발 · CS와 공유해 고치고, 1주간 이탈률이 원래 수준으로 돌아왔는지 확인합니다.",,Q0042
디자인,에듀테크,직무,학습자가 꾸준히 다시 찾아오게 만드는 화면 요소를 어떻게 설계하나요?,동기 부여 · 학습 효과 · 과한 장치 경계,"학습자가 '오늘 할 일'과 '쌓인 성과'를 바로 느끼게 설계하되, 압박을 주는 장치는 경계합니다. 첫 화면에 오늘 할 분량을 10분 단위로 작게 보여 주고, 끝내면 지난주보다 늘어난 학습량을 보여 줍니다. 연속 학습 표시는 하루 빠져도 끊기지 않는 방식으로 만들어, 실패감 때문에 그만두지 않게 합니다. 학습 앱 프로젝트에서 이렇게 바꿔 4주 재방문율을 31%에서 44%로 올렸고, 설문에서 '부담스럽다'는 답은 늘지 않았습니다.",,Q0043
디자인,에듀테크,상황,학생과 학부모처럼 사용자가 둘인 서비스에서 두 쪽의 요구가 부딪히면 어떻게 하나요?,이해관계자 구분 · 우선순위 판단,"두 사용자가 각각 이루려는 목표를 나누고, 서비스의 핵심 목표인 학습 효과를 기준으로 우선순위를 정합니다. 예를 들어 학부모는 자세한 기록을, 학생은 간섭받지 않는 화면을 원한다면 각각 3명씩 인터뷰해 꼭 필요한 정보가 무엇인지 확인합니다. 학부모에게는 주간 요약 알림을, 학생에게는 자세한 기록 대신 스스로 보는 진도만 보여 주는 식으로 화면을 나눕니다. 이 안을 양쪽 5명씩 테스트해 만족도를 비교하고 결정합니다.",,Q0044
디자인,모빌리티 · 여행,직무,이동 중이거나 급한 상황의 사용자를 위한 화면은 무엇이 달라야 하나요?,사용 맥락 · 한 손 조작 · 실시간 정보,"짧은 시간에 한 손으로 핵심 정보 하나를 확인할 수 있어야 합니다. 그래서 화면마다 '지금 가장 중요한 정보'를 하나로 정해 가장 크게 두고, 자주 누르는 버튼은 엄지가 닿는 아래쪽에 48px 이상으로 둡니다. 출발 시간 · 도착 예정처럼 바뀌는 정보는 실시간으로 갱신하고, 마지막 갱신 시각을 함께 보여 줍니다. 프로젝트에서 실제로 걸으면서 5명에게 테스트해, 정보 확인 시간을 평균 6초에서 3초로 줄였습니다.",,Q0045
디자인,모빌리티 · 여행,상황,예약 취소와 환불 화면에 고객 문의가 몰린다면 어떻게 개선하나요?,문제 정의 · 안내 문구 · 개선 검증,"문의 내용을 분류해 사용자가 무엇을 모르는지 정의하고, 안내를 바꾼 뒤 문의 수로 효과를 확인합니다. 먼저 최근 한 달 문의 200건을 나눠 보면 '환불 금액', '환불 시점', '취소 수수료' 같은 유형이 나옵니다. 예를 들어 환불 시점 문의가 50%라면 취소 화면에 '언제 · 얼마가 · 어디로' 돌아오는지 미리 보여 주는 요약을 넣습니다. 바꾼 뒤 2주간 같은 유형 문의가 얼마나 줄었는지 CS 팀과 같이 확인합니다.",,Q0046
디자인,콘텐츠 · 미디어,직무,추천 콘텐츠를 보여 줄 때 사용자가 '이게 왜 나왔지' 하고 느끼지 않게 하려면 어떻게 하나요?,추천 이유 전달 · 탐색 경험 · 개인화,"추천 옆에 '왜 추천했는지'를 짧게 보여 주고, 사용자가 추천을 고칠 수 있게 합니다. 예를 들어 '최근 본 다큐와 비슷해요'처럼 근거를 한 줄로 붙이고, '관심 없음'을 누르면 비슷한 추천이 줄어들게 합니다. 이유 문구는 개인정보가 드러나지 않는 수준으로 정합니다. 프로젝트에서 이유 문구를 넣은 안을 테스트했더니 추천 클릭률이 9%에서 13%로 오르고, '이상한 추천' 피드백은 절반으로 줄었습니다.",,Q0047
디자인,콘텐츠 · 미디어,상황,창작자와 시청자의 요구가 다를 때 화면을 어떻게 설계하나요?,양쪽 사용자 이해 · 균형 잡힌 판단,"양쪽이 서비스에서 얻으려는 핵심 가치를 나눠 보고, 둘 다 지키는 지점을 찾습니다. 창작자는 노출과 수익을, 시청자는 원하는 콘텐츠를 빨리 찾는 것을 원한다면 각각 인터뷰 4명씩으로 확인합니다. 예를 들어 창작자 홍보 영역은 두되, 시청자 피드에서는 관련성이 높을 때만 보이게 합니다. 이 안을 일부 사용자에게 실험해 창작자 노출 수와 시청자 만족도를 함께 보고 결정합니다.",,Q0048
디자인,B2B · SaaS,직무,매일 오래 쓰는 업무 도구 화면을 설계할 때 일반 앱과 무엇이 달라야 하나요?,업무 효율 · 정보 밀도 · 숙련 사용자 배려,"업무 도구는 '처음 쓰기 쉬움'보다 '매일 빠르게 많이 처리하기'가 더 중요합니다. 그래서 한 화면에 필요한 정보를 더 많이 보여 주되, 표 정렬 · 필터 저장 · 단축키로 반복 작업을 줄입니다. 실제 사용자의 하루 업무를 관찰해 가장 자주 하는 작업 3개를 찾고, 그 작업의 클릭 수를 측정합니다. 인턴 때 관리자 화면에서 이렇게 주문 처리 클릭을 7번에서 3번으로 줄였고, 한 건 처리 시간이 40% 줄었습니다.",,Q0049
디자인,B2B · SaaS,상황,고객사마다 기능 요청이 다를 때 디자인 시스템의 일관성을 어떻게 지키나요?,확장성 · 일관성 · 우선순위,"공통으로 쓰일 요청만 시스템에 넣고, 고객사별 요청은 설정으로 해결하는 기준을 둡니다. 요청이 오면 '3개 이상 고객사가 필요로 하는가', '기존 컴포넌트로 만들 수 있는가'로 분류합니다. 공통 요청은 컴포넌트로 만들어 문서에 추가하고, 개별 요청은 색 · 로고 · 메뉴 노출 같은 설정값으로 바꿀 수 있게 합니다. 인턴 때 요청 18건을 이렇게 나눠 새 컴포넌트를 4개만 만들고, 나머지는 설정으로 처리해 일관성을 지켰습니다.",,Q0050
디자인,게임,직무,게임 UI에서 몰입을 깨지 않으면서 필요한 정보를 전달하려면 어떻게 하나요?,몰입 유지 · 정보 계층 · 플레이 맥락,"플레이 흐름을 끊지 않도록 정보에 순서를 정하고, 필요한 순간에만 보여 줍니다. 체력 · 남은 시간처럼 계속 봐야 하는 정보는 화면 가장자리에 작게 고정하고, 퀘스트 안내 같은 정보는 전투가 끝난 뒤에 띄웁니다. 위험 신호는 글자보다 색 · 소리 · 진동으로 먼저 알립니다. 팀 프로젝트에서 이렇게 바꾼 뒤 테스트 6명이 화면 정보를 확인하려고 멈춘 횟수가 판당 4번에서 1번으로 줄었습니다.",,Q0051
디자인,게임,상황,업데이트 뒤 커뮤니티에 UI 불만이 쏟아지면 어떻게 대응하나요?,피드백 분류 · 데이터 확인 · 소통,"불만을 분류해 실제 문제를 찾고, 데이터로 확인한 뒤 고칠 계획을 먼저 알립니다. 커뮤니티 글 100개를 '위치가 바뀜', '버튼이 작음', '취향' 같은 유형으로 나누고, 같은 기간 해당 버튼의 사용 데이터를 봅니다. 예를 들어 위치가 바뀐 버튼의 사용률이 30% 줄었다면 실제 문제로 보고, 이전 위치로 돌리거나 설정을 주는 안을 만듭니다. 고칠 내용과 일정을 공지로 먼저 알리고, 다음 업데이트 뒤 불만 글 수를 다시 확인합니다.",,Q0052
디자인,헬스케어,직무,의료 용어가 많은 화면을 일반 사용자도 이해하게 만들려면 어떻게 하나요?,쉬운 말 · 정보 위계 · 오해 방지,"의료 용어를 쉬운 말로 바꾸되, 정확한 용어도 함께 남겨 오해와 신뢰 문제를 같이 막습니다. 먼저 화면의 용어 목록을 만들어 일반 사용자 5명에게 뜻을 물어보고, 3명 이상이 모르는 용어를 바꿀 대상으로 정합니다. 예를 들어 '공복 혈당' 옆에 '아침 식사 전 혈당'을 먼저 쓰고, 정상 범위를 색과 글자로 함께 보여 줍니다. 바꾼 문구는 의료진 검토를 받고, 재테스트에서 결과를 바르게 이해한 비율이 40%에서 90%로 오른 것을 확인했습니다.",,Q0053
디자인,헬스케어,직무,의료진이 쓰는 화면과 환자가 쓰는 화면은 설계할 때 무엇이 달라야 하나요?,사용자 구분 · 업무 맥락 · 정확성,"의료진 화면은 빠르고 정확한 처리, 환자 화면은 안심과 이해가 가장 중요합니다. 의료진은 짧은 시간에 여러 환자를 보니, 핵심 수치와 이상 신호를 한 화면에 밀도 있게 보여 주고 입력 실수를 막는 확인 장치를 둡니다. 환자는 같은 정보를 쉬운 말과 다음 행동 위주로 보여 주고, 불안을 줄이는 설명을 붙입니다. 프로젝트에서 두 화면을 나눠 설계하고 각각 4명에게 테스트해, 의료진 처리 시간과 환자 이해도를 따로 확인했습니다.",,Q0054
디자인,헬스케어,경험,건강이나 생활 습관과 관련된 서비스를 써 보며 불편했던 점과 개선 아이디어를 말해 주세요.,관찰 · 개선 아이디어의 근거,"수면 기록 앱을 한 달 쓰면서 '기록이 왜 그렇게 나왔는지 몰라서' 그만두고 싶었던 경험이 있습니다. 수면 점수가 62점으로 나와도 이유가 없어서, 무엇을 바꿔야 할지 알 수 없었습니다. 그래서 점수 옆에 '늦게 잠듦 · 자주 깸' 같은 원인 2개와 내일 해 볼 행동 하나를 보여 주는 개선안을 만들었습니다. 같은 앱을 쓰는 지인 5명에게 시안을 보여 주니 4명이 '계속 쓰고 싶다'고 답했고, 이 피드백으로 문구를 한 번 더 다듬었습니다.",,Q0055
디자인,헬스케어,경험,민감한 정보를 다루는 화면을 만들며 고민했던 경험을 말해 주세요.,개인정보 · 신뢰 · 판단 과정,"상담 예약 서비스 프로젝트에서 상담 사유를 어디까지 받을지 고민했습니다. 처음 시안은 사유를 자세히 적게 했지만, 사용자 6명 중 4명이 '남이 볼까 봐' 입력을 망설였습니다. 그래서 사유는 선택 항목으로 바꾸고, '상담사만 볼 수 있어요'라는 안내와 언제든 지울 수 있는 기능을 넣었습니다. 바꾼 뒤 테스트에서 입력을 망설인 사람이 1명으로 줄었고, 예약 완료율도 15%p 올랐습니다.",,Q0056
디자인,헬스케어,상황,규제 때문에 원하는 기능이나 표현을 쓸 수 없다고 하면 디자인을 어떻게 바꾸나요?,제약 안에서의 대안 · 협업,"규제의 목적을 먼저 이해하고, 그 안에서 같은 사용자 목표를 이루는 다른 방법을 찾습니다. 예를 들어 '효과 보장' 같은 표현을 못 쓴다면, 법무 · 의료 담당자에게 허용되는 표현 범위를 먼저 받습니다. 그다음 효과를 약속하는 대신 '이용자 후기 수'나 '연구 출처 보기'처럼 확인 가능한 정보를 보여 주는 시안 2개를 만듭니다. 담당자 검토를 거친 안을 사용자 5명에게 테스트해 신뢰도와 이해도를 비교하고 결정합니다.",,Q0057
디자인,헬스케어,상황,복약 시간을 알려 주는 알림을 끄는 사용자가 늘었다면 어떻게 하나요?,원인 가설 · 알림 피로 · 개선 검증,"알림을 끄는 이유를 데이터와 인터뷰로 나눠 보고, 알림 피로를 줄이는 방향으로 바꾼 뒤 복약률로 확인합니다. 알림 끄기 직전의 알림 횟수 · 시간대를 보면, 하루 4번 이상 받는 사용자가 많이 끈다는 식의 패턴이 나옵니다. 사용자 5명 인터뷰로 '시간이 안 맞음', '같은 알림 반복' 같은 원인을 확인합니다. 원하는 시간 설정과 놓친 알림만 한 번 더 보내는 안을 실험해, 알림 끄기 비율과 실제 복약 기록률을 2주간 비교합니다.",복약/약/처방/약국/복용,Q0058
디자인,핀테크 · 금융,직무,숫자와 금액이 많은 화면을 읽기 쉽게 만드는 방법은 무엇인가요?,숫자 표기 · 정보 위계 · 강조,"가장 중요한 숫자 하나를 크게, 나머지는 같은 규칙으로 정렬해 비교하기 쉽게 만듭니다. 금액은 천 단위 쉼표와 단위를 항상 붙이고, 같은 열의 숫자는 오른쪽 정렬과 고정폭 숫자로 맞춥니다. 증가 · 감소는 색만 쓰지 않고 +/- 기호와 화살표를 함께 써서 색을 구분하기 어려운 사용자도 알 수 있게 합니다. 가계부 프로젝트에서 이렇게 바꿔 '이번 달 지출 찾기' 과제 시간을 14초에서 5초로 줄였습니다.",,Q0059
디자인,핀테크 · 금융,직무,처음 쓰는 사용자도 안심하고 계좌를 연결하게 하려면 어떤 화면이 필요한가요?,신뢰 요소 · 단계 안내 · 불안 해소,"왜 연결이 필요한지, 무엇이 안전한지, 지금 몇 단계인지를 차례로 보여 줘서 불안을 줄입니다. 첫 화면에 연결하면 얻는 것 한 줄과 '비밀번호는 저장하지 않아요' 같은 보안 사실을 보여 주고, 전체 단계를 1/3 · 2/3처럼 표시합니다. 개인정보를 묻는 단계마다 왜 필요한지 짧게 설명하고, 중간에 나가도 이어서 할 수 있게 합니다. 프로젝트 테스트에서 처음 쓰는 사용자 6명 중 연결을 포기한 사람이 3명에서 1명으로 줄었습니다.",,Q0060
디자인,핀테크 · 금융,경험,송금 · 가계부 · 투자 같은 서비스를 쓰며 불안하거나 헷갈렸던 경험과 개선 아이디어를 말해 주세요.,사용자 관점 · 구체적인 개선안,"더치페이 송금을 하다 받는 사람을 잘못 골라 불안했던 경험이 있습니다. 이름이 같은 친구가 두 명이었는데 목록에 이름만 나와서, 보내고 나서야 틀린 걸 알았습니다. 그래서 받는 사람 목록에 프로필 사진 · 최근 송금일을 같이 보여 주고, 처음 보내는 상대에게는 확인 단계를 한 번 더 두는 개선안을 만들었습니다. 지인 5명에게 시안으로 같은 상황을 테스트하니 5명 모두 올바른 사람을 골랐습니다.",,Q0061
디자인,핀테크 · 금융,경험,숫자나 데이터를 그래프 · 표로 보여 주는 화면을 만들어 본 경험이 있나요?,시각화 선택 근거 · 정확성,"네, 동아리 회비 사용 내역을 보여 주는 대시보드를 만든 경험이 있습니다. 처음엔 원 그래프로 항목별 비율을 보여 줬는데, 회원 6명에게 물어보니 '지난달보다 늘었는지'를 가장 궁금해했습니다. 그래서 월별 막대 그래프로 바꾸고, 항목별 금액은 표로 정확히 보여 줬습니다. 숫자는 원본 장부와 하나씩 맞춰 오류 2건을 고쳤고, 바꾼 뒤 회비 관련 질문이 한 달 12건에서 3건으로 줄었습니다.",,Q0062
디자인,핀테크 · 금융,상황,송금 완료 화면에서 '정말 보내졌나요?' 라는 문의가 많다면 어떻게 하나요?,결과 피드백 · 상태 표시 · 검증,"완료 화면에서 '처리가 끝났다'는 사실을 확실한 증거와 함께 보여 줍니다. 먼저 문의 내용을 보고, 사용자가 의심하는 지점이 '보내졌는지'인지 '상대가 받았는지'인지 나눕니다. 완료 화면에 받는 사람 · 금액 · 시각 · 거래 번호를 크게 보여 주고, 상대 계좌 입금까지 걸리는 시간을 안내하며, 내역 화면으로 바로 가는 버튼을 둡니다. 바꾼 뒤 2주간 같은 유형 문의가 얼마나 줄었는지 CS 팀과 함께 확인합니다.",,Q0063
디자인,핀테크 · 금융,상황,꼭 넣어야 하는 고지 문구 때문에 화면이 복잡해졌다면 어떻게 하나요?,필수 정보와 사용성의 균형,"고지 문구는 빼지 않고, 핵심만 먼저 보여 주고 전문은 펼쳐 볼 수 있게 정리합니다. 법무 담당자와 '꼭 첫 화면에 보여야 하는 문장'과 '링크로 둬도 되는 문장'을 나눕니다. 핵심 문장은 쉬운 말로 3줄 안에 쓰고, 전문은 '자세히 보기'로 두며, 동의가 필요한 항목은 체크박스로 따로 분리합니다. 이 안을 사용자 5명에게 테스트해 핵심 내용을 기억하는지와 과제 완료 시간을 함께 확인하고, 법무 검토로 다시 확인합니다.",,Q0064
디자인,커머스,직무,검색 결과에 상품이 너무 많을 때 원하는 상품을 빨리 찾게 하려면 어떻게 하나요?,필터 · 정렬 · 정보 구조,"사용자가 빨리 범위를 좁힐 수 있게 필터와 정렬을 검색어에 맞춰 보여 줍니다. 검색 로그를 보면 '원피스'를 찾는 사람은 가격 · 사이즈를, '노트북'을 찾는 사람은 용도 · 무게를 많이 고르는 식의 차이가 있습니다. 그래서 검색어 종류마다 자주 쓰는 필터 3개를 맨 위에 꺼내 두고, 고른 필터는 칩으로 보여 바로 지울 수 있게 합니다. 이 안을 A/B 테스트해 검색 후 상품 클릭까지 걸리는 시간과 구매 전환율을 비교합니다.",,Q0065
디자인,커머스,직무,할인과 쿠폰 정보를 보여 줄 때 사용자를 오해하게 만들지 않으려면 무엇을 주의하나요?,다크 패턴 경계 · 정확한 표기,"사용자가 최종으로 내는 금액을 가장 정확하고 눈에 띄게 보여 주는 것이 원칙입니다. 할인율만 크게 보여 주지 않고, 쿠폰 적용 조건 · 기간 · 최종 결제 금액을 같은 화면에 함께 적습니다. 남은 시간이나 재고처럼 압박을 주는 표시는 실제 데이터일 때만 쓰고, 조건이 있는 쿠폰은 적용 전에 미리 알립니다. 프로젝트에서 이 기준으로 바꾼 뒤 '쿠폰이 안 돼요' 문의가 한 달 40건에서 15건으로 줄었습니다.",,Q0066
디자인,커머스,경험,온라인 쇼핑 중 구매를 포기했던 경험을 하나 골라 원인과 개선안을 말해 주세요.,문제 발견 · 근거 · 개선안,"운동화를 사려다 결제 직전에 배송비와 도착일을 보고 포기한 경험이 있습니다. 상품 화면에는 무료 배송으로 보였는데, 결제 단계에서 지역 추가 배송비 3,000원과 5일 뒤 도착이 처음 나왔습니다. 원인은 중요한 조건이 마지막에야 보인다는 점이라고 봤고, 상품 화면에서 주소 기준 배송비 · 도착일을 미리 보여 주는 개선안을 만들었습니다. 지인 5명에게 두 화면을 비교하게 하니 4명이 '결제까지 가겠다'고 답했습니다.",,Q0067
디자인,커머스,경험,상품 이미지나 배너를 만들어 본 경험과 그 결과를 말해 주세요.,목표 설정 · 결과 확인,"네, 동아리 공연 홍보 배너를 목표를 정해 만들고 결과를 확인한 경험이 있습니다. 목표는 예매 페이지 클릭 수를 지난 공연보다 늘리는 것이었고, 시안 2개(공연 사진형 · 날짜 강조형)를 만들었습니다. 같은 기간 SNS에 두 배너를 나눠 올렸더니 날짜 강조형의 클릭률이 4.1%로 사진형 2.3%보다 높았습니다. 그 배너로 통일해 예매 수가 지난 공연보다 35% 늘었고, 이 결과를 다음 홍보 가이드로 남겼습니다.",,Q0068
디자인,커머스,상황,메인 배너를 더 키우자는 요청이 왔는데 데이터로는 클릭이 낮다면 어떻게 하나요?,데이터 기반 설득 · 대안 제시,"요청의 목적을 먼저 묻고, 데이터를 보여 주며 목적을 더 잘 이루는 대안을 함께 제안합니다. 배너를 키우려는 이유가 신상품 노출이라면, 현재 배너 클릭률이 0.8%로 다른 영역보다 낮다는 데이터를 공유합니다. 그 대신 신상품을 첫 화면 상품 목록 위쪽에 넣는 안과, 배너를 키우는 안을 함께 A/B 테스트하자고 제안합니다. 2주간 신상품 클릭 수와 전체 구매 전환을 비교해, 결과로 결정합니다.",,Q0069
디자인,커머스,상황,모바일에서만 결제 오류 문의가 많다면 원인을 어떻게 찾나요?,문제 재현 · 협업 · 우선순위,"문의 데이터로 조건을 좁히고 직접 재현한 뒤, 개발자와 함께 원인을 확인합니다. 먼저 문의를 기기 · 운영체제 · 앱 버전 · 결제 수단별로 나눠 보고, 예를 들어 특정 안드로이드 버전에 몰려 있는지 확인합니다. 같은 조건의 기기로 직접 결제를 시도해 화면을 녹화하고, 버튼이 키보드에 가려지는 것 같은 화면 문제인지 시스템 오류인지 나눕니다. 결과를 개발 · CS와 공유해 결제 매출 영향이 큰 순서로 고치고, 배포 후 문의 수로 확인합니다.",,Q0070
디자인,에듀테크,직무,학습 진도와 성취를 화면에 어떻게 보여 줘야 동기가 생기나요?,진도 시각화 · 동기 부여 · 부담 조절,"목표 대비 진도와 '어제보다 나아진 점'을 함께 보여 줘서, 남은 양보다 쌓인 성과가 먼저 보이게 합니다. 전체 진도는 막대 하나로, 이번 주 목표는 작게 나눠 체크하게 하고, 끝낼 때마다 익힌 개념 수를 보여 줍니다. 다른 사람과 비교하는 순위는 기본으로 숨기고 원하는 사람만 켜게 해서 부담을 줄입니다. 학습 앱 프로젝트에서 이렇게 바꿔 주간 목표 달성률을 38%에서 55%로 올렸습니다.",,Q0071
디자인,에듀테크,직무,어린 학습자와 성인 학습자를 위한 화면은 무엇이 달라야 하나요?,연령별 특성 · 접근성,"어린 학습자는 글보다 그림과 소리로 바로 이해하게, 성인 학습자는 시간 효율과 스스로 조절하는 기능을 중심으로 설계합니다. 어린 학습자에게는 큰 버튼, 읽어 주는 음성, 한 화면 한 과제로 실수를 줄이고, 결제나 외부 링크는 보호자 확인을 거치게 합니다. 성인에게는 배속 · 건너뛰기 · 이어 보기처럼 시간을 아끼는 기능을 앞에 둡니다. 두 그룹 각각 4명에게 테스트해, 과제 성공률과 학습 시간을 따로 확인합니다.",,Q0072
디자인,에듀테크,경험,공부하며 써 본 앱 중 계속 쓴 앱과 그만둔 앱의 차이를 설명해 주세요.,관찰 · 원인 분석,"계속 쓴 단어 앱은 하루 5분 분량이 정해져 있었고, 그만둔 앱은 매번 무엇을 할지 제가 골라야 했습니다. 계속 쓴 앱은 열자마자 오늘 할 20개가 나오고, 끝나면 일주일 동안 외운 단어 수를 보여 줬습니다. 그만둔 앱은 강의가 300개나 있어 고르다가 지쳤고, 진도를 놓치면 다시 시작할 지점을 찾기 어려웠습니다. 그래서 학습 서비스의 핵심은 '결정 부담을 줄이고 작은 성취를 보여 주는 것'이라고 보고, 제 프로젝트에도 적용했습니다.",,Q0073
디자인,에듀테크,경험,누군가에게 무언가를 가르치거나 설명 자료를 만들어 본 경험이 있나요?,학습자 이해 · 전달 구조,"네, 신입 동아리원 15명에게 디자인 툴 기초를 가르치는 자료를 만든 경험이 있습니다. 처음엔 기능 설명 위주로 만들었는데, 1회차 뒤 설문에서 '배운 걸 어디에 쓰는지 모르겠다'는 답이 60%였습니다. 그래서 자료를 '명함 하나 완성하기'처럼 결과물 하나를 만드는 순서로 다시 짰고, 단계마다 따라 할 화면을 넣었습니다. 2회차 뒤에는 15명 중 13명이 과제를 끝냈고, 만족도가 5점 중 3.2점에서 4.5점으로 올랐습니다.",,Q0074
디자인,에듀테크,상황,강의 영상 중간에 나가는 학습자가 많다면 어떻게 개선하나요?,데이터 확인 · 가설 · 개선 실험,"이탈이 몰리는 구간을 먼저 찾고, 원인 가설을 세워 작은 실험으로 확인합니다. 재생 데이터를 보면 예를 들어 8분 지점에서 이탈이 급하게 늘 수 있고, 그 구간이 긴 이론 설명인지 화면 문제인지 확인합니다. 학습자 5명에게 그 구간을 보여 주고 인터뷰해 '너무 길다', '어디까지 남았는지 모른다' 같은 원인을 찾습니다. 강의를 챕터로 나누고 남은 시간을 표시하는 안을 일부 학습자에게 실험해, 완강률과 이탈 구간을 2주간 비교합니다.",,Q0075
디자인,에듀테크,상황,선생님은 기능을 더 원하고 학생은 복잡하다고 하면 어떻게 하나요?,사용자 구분 · 우선순위 판단,"두 사용자의 목표를 나눠 보고, 학생이 쓰는 화면은 단순하게 지키면서 선생님 기능은 선생님 화면에 둡니다. 선생님 5명 인터뷰로 요청 기능 중 실제로 매주 쓰는 것과 가끔 쓰는 것을 구분하고, 학생 5명 테스트로 어디서 복잡하다고 느끼는지 확인합니다. 매주 쓰는 기능만 선생님 기본 화면에 두고, 나머지는 '더 보기'로 넣으며, 학생 화면에는 과제와 진도만 남깁니다. 바꾼 안을 양쪽에 테스트해 선생님 작업 시간과 학생 과제 완료율을 함께 확인합니다.",,Q0076
디자인,모빌리티 · 여행,직무,지도 위에 많은 정보를 겹쳐 보여 줄 때 무엇을 먼저 고려하나요?,정보 우선순위 · 가독성,"지금 사용자가 해야 하는 일에 필요한 정보만 가장 위에, 나머지는 단계적으로 보여 줍니다. 예를 들어 길 찾기 중에는 경로와 다음 회전만 크게 보이고, 주변 가게 정보는 멈췄을 때나 확대했을 때 보여 줍니다. 겹치는 아이콘은 묶어서 숫자로 표시하고, 지도 위 글자는 배경과 대비 4.5:1 이상을 지킵니다. 프로젝트에서 이 기준으로 지도 화면을 정리해, 테스트 6명이 목적지 표시를 찾는 시간을 평균 9초에서 4초로 줄였습니다.",,Q0077
디자인,모빌리티 · 여행,직무,예약 과정에서 날짜 · 인원 · 옵션 선택을 쉽게 만들려면 어떻게 하나요?,입력 단계 설계 · 오류 예방,"자주 고르는 값을 기본값으로 두고, 한 번에 하나씩 묻고, 틀린 선택은 미리 막습니다. 예약 데이터를 보고 가장 많은 인원(예: 2명)과 가까운 주말을 기본값으로 두고, 달력에서는 예약할 수 없는 날을 처음부터 흐리게 표시합니다. 옵션은 가격이 바뀌는 것만 먼저 보여 주고, 고를 때마다 총액을 바로 갱신합니다. 프로젝트 테스트에서 이렇게 바꿔 예약 입력 오류를 5명 중 3명에서 0명으로, 입력 시간을 1분 40초에서 55초로 줄였습니다.",,Q0078
디자인,모빌리티 · 여행,경험,여행이나 이동 중에 앱 때문에 곤란했던 경험과 개선 아이디어를 말해 주세요.,사용 맥락 이해 · 개선안,"해외 공항에서 앱으로 체크인하려다 데이터가 끊겨 탑승권을 못 띄운 경험이 있습니다. 와이파이가 불안정한 곳에서 앱이 계속 로딩만 했고, 미리 받아 둔 탑승권도 오프라인에서 열리지 않았습니다. 그래서 체크인을 마치면 탑승권을 자동으로 기기에 저장하고, 오프라인일 때도 저장된 탑승권을 첫 화면에 바로 보여 주는 개선안을 만들었습니다. 지인 5명에게 비행기 모드로 시안을 테스트하니 모두 10초 안에 탑승권을 찾았습니다.",,Q0079
디자인,모빌리티 · 여행,경험,실제 사용 환경(야외 · 이동 중)에서 화면을 확인해 본 경험이 있나요?,현장 검증 · 발견한 점,"네, 버스 도착 알림 화면을 실제 정류장에서 확인해 보고 크게 고친 경험이 있습니다. 사무실에서는 잘 보였던 회색 글자가 햇빛 아래에서는 거의 보이지 않았고, 한 손에 짐을 든 채로는 위쪽 버튼에 손이 닿지 않았습니다. 그래서 글자 대비를 4.5:1에서 7:1 수준으로 올리고, 자주 누르는 버튼을 화면 아래로 옮겼습니다. 다시 정류장에서 5명에게 테스트해 도착 시간 확인 시간이 평균 7초에서 3초로 줄었습니다.",,Q0080
디자인,모빌리티 · 여행,상황,배차나 일정이 늦어질 때 사용자 불만을 줄이려면 화면에서 무엇을 할 수 있나요?,상태 안내 · 기대 관리,"늦어지는 이유와 새 예상 시각을 바로 알리고, 사용자가 할 수 있는 선택지를 함께 줍니다. 상태가 바뀌면 '기사님이 교통 체증으로 7분 늦어요'처럼 이유와 새 도착 시각을 알림과 화면 맨 위에 보여 줍니다. 예상 시각은 범위로 보여 주고 갱신될 때마다 바꿔, 기대와 실제의 차이를 줄입니다. 기다리기 · 취소 · 다른 차량 찾기 같은 선택지를 함께 두고, 바꾼 뒤 지연 상황의 불만 문의와 취소율을 비교해 효과를 확인합니다.",,Q0081
디자인,모빌리티 · 여행,상황,해외 사용자가 늘면서 다국어 화면이 깨진다는 문의가 오면 어떻게 하나요?,현지화 · 글자 길이 · 우선순위,"깨지는 화면과 언어를 목록으로 만들고, 많이 쓰이는 언어와 핵심 화면부터 고치면서 글자 길이에 강한 레이아웃 규칙을 만듭니다. 문의와 사용 데이터를 보고 사용자가 많은 언어 2~3개를 정한 뒤, 그 언어로 가입 · 예약 · 결제 화면을 직접 점검합니다. 버튼과 제목은 고정 너비 대신 글자에 따라 늘어나게 하고, 가장 긴 언어(예: 독일어) 기준으로 줄바꿈 규칙을 정합니다. 고친 뒤 해당 언어 사용자 문의와 예약 완료율을 비교해 확인합니다.",,Q0082
디자인,콘텐츠 · 미디어,직무,처음 들어온 사용자가 볼 만한 콘텐츠를 빨리 찾게 하려면 어떻게 하나요?,온보딩 · 탐색 구조,"처음 몇 번의 선택으로 취향을 빨리 파악하고, 그 결과를 바로 첫 화면에 보여 줍니다. 가입 직후 관심 분야를 3개만 고르게 하고, 고르기 싫은 사람은 '인기 콘텐츠로 시작하기'로 건너뛸 수 있게 합니다. 첫 화면은 고른 분야별로 짧은 콘텐츠를 먼저 보여 줘서, 부담 없이 하나를 눌러 보게 합니다. 프로젝트에서 이 흐름을 테스트해 첫 콘텐츠를 누르기까지 걸린 시간을 평균 48초에서 15초로 줄였습니다.",,Q0083
디자인,콘텐츠 · 미디어,직무,썸네일과 제목이 클릭을 부르면서도 과장되지 않게 하려면 어떻게 하나요?,신뢰 · 정확성 · 가이드 설계,"썸네일과 제목이 실제 내용과 맞는지 확인하는 가이드를 만들고, 그 기준 안에서 눈에 띄게 설계합니다. 가이드에는 '영상에 없는 장면은 쓰지 않기', '제목의 숫자는 실제와 같게'처럼 확인 가능한 규칙 5개를 둡니다. 눈에 띄는 것은 과장 대신 큰 인물 얼굴 · 대비가 높은 색 · 짧은 제목으로 해결하고, 업로드 화면에서 가이드를 미리 보여 줍니다. 이 기준을 적용한 썸네일을 테스트해 클릭률과 '기대와 달랐다' 피드백을 함께 비교합니다.",,Q0084
디자인,콘텐츠 · 미디어,경험,자주 쓰는 콘텐츠 앱에서 불편한 점을 하나 골라 개선안을 말해 주세요.,관찰 · 근거 · 개선안,"자주 쓰는 동영상 앱에서 '나중에 볼 영상'을 다시 찾기 어려운 점이 불편했습니다. 저장한 영상이 50개가 넘자 저장 순서로만 쌓여서, 원하는 영상을 찾는 데 1분 넘게 걸렸습니다. 그래서 저장할 때 주제 태그를 하나 고르게 하고, 저장함 위쪽에 태그별 묶음과 '오래 안 본 영상'을 보여 주는 개선안을 만들었습니다. 같은 앱을 쓰는 지인 5명에게 테스트하니 찾는 시간이 평균 65초에서 12초로 줄었습니다.",,Q0085
디자인,콘텐츠 · 미디어,경험,영상 · 이미지 · 글 같은 콘텐츠를 직접 만들어 운영해 본 경험이 있나요?,창작자 관점 · 결과 확인,"네, 디자인 팁을 알려 주는 짧은 영상 채널을 6개월 동안 운영한 경험이 있습니다. 처음 10편은 조회수가 평균 200회였는데, 시청 지속 데이터를 보니 첫 5초에 40%가 나갔습니다. 그래서 첫 장면에 '완성된 결과'를 먼저 보여 주는 구성으로 바꾸고, 썸네일에 결과 화면을 넣었습니다. 바꾼 뒤 평균 조회수가 1,100회로 늘었고, 이 경험으로 창작자가 데이터를 보고 콘텐츠를 고치는 과정에 무엇이 필요한지 알게 됐습니다.",,Q0086
디자인,콘텐츠 · 미디어,상황,시청 시간은 늘었는데 만족도 점수가 떨어졌다면 어떻게 해석하나요?,지표 해석 · 균형 잡힌 판단,"두 지표가 다르게 움직인 이유를 나눠 보고, 오래 보는 것이 좋은 경험인지 확인합니다. 먼저 시청 시간이 늘어난 사용자와 만족도가 떨어진 사용자가 같은 그룹인지, 어떤 기능 변경 뒤부터인지 데이터로 봅니다. 예를 들어 자동 재생을 늘린 뒤라면 '보고 싶지 않은 영상이 계속 나온다'는 가설을 세우고, 사용자 5명 인터뷰로 확인합니다. 만족도를 함께 지키는 지표로 정하고, 자동 재생 설정을 바꾼 실험으로 두 지표를 같이 확인합니다.",,Q0087
디자인,콘텐츠 · 미디어,상황,신고 기능을 더 잘 보이게 해 달라는 요청이 오면 어떻게 설계하나요?,안전 · 사용성의 균형,"신고가 필요한 사람은 쉽게 찾되, 실수로 누르거나 남용하지 않게 설계합니다. 신고 버튼은 콘텐츠마다 같은 자리(더 보기 메뉴의 첫 항목)에 두고, 위험한 콘텐츠 유형일 때는 화면에서 바로 보이게 합니다. 신고 사유는 4~5개 중 고르게 해서 처리를 빠르게 하고, 신고 뒤에는 '검토 중' 상태와 차단 같은 다음 행동을 보여 줍니다. 바꾼 뒤 신고까지 걸리는 시간과 잘못된 신고 비율을 운영팀과 함께 확인합니다.",,Q0088
디자인,B2B · SaaS,직무,기능이 많은 관리자 화면에서 자주 쓰는 기능을 빨리 찾게 하려면 어떻게 하나요?,정보 구조 · 사용 빈도 반영,"실제 사용 빈도를 데이터로 보고, 자주 쓰는 기능을 가장 가까운 곳에 둡니다. 메뉴별 클릭 로그를 보면 보통 전체 기능의 20% 정도가 사용의 대부분을 차지하므로, 그 기능을 첫 화면 바로가기와 검색으로 꺼냅니다. 드물게 쓰는 설정은 하위 메뉴로 묶고, 사용자가 즐겨찾기를 직접 고를 수 있게 합니다. 인턴 때 이렇게 바꿔 주요 기능까지의 클릭 수를 평균 4번에서 2번으로 줄였고, 관련 문의도 절반으로 줄었습니다.",,Q0089
디자인,B2B · SaaS,직무,새로 도입한 고객사 직원이 빨리 익히게 하려면 무엇을 설계하나요?,온보딩 · 도움말 · 빈 화면 설계,"처음 해야 할 일을 순서대로 안내하고, 빈 화면마다 다음 행동을 알려 줍니다. 첫 로그인 때 '팀원 초대 → 첫 데이터 올리기 → 보고서 보기' 같은 체크리스트 3단계를 보여 주고, 끝낼 때마다 표시합니다. 데이터가 없는 빈 화면에는 무엇을 하면 되는지와 예시 데이터를 넣어, 막히지 않게 합니다. 이 흐름을 새 고객사 직원 5명에게 테스트해 첫 보고서를 만들기까지 걸리는 시간과 문의 수를 확인합니다.",,Q0090
디자인,B2B · SaaS,경험,업무용 도구를 쓰며 비효율을 느끼고 개선해 본 경험이 있나요?,문제 발견 · 개선 과정,"네, 동아리 회비 관리를 엑셀에서 신청 폼과 자동 정리 시트로 바꿔 시간을 줄인 경험이 있습니다. 매달 총무가 메시지로 받은 입금 내역을 손으로 옮기느라 3시간씩 걸렸고, 누락도 한 달 평균 4건 있었습니다. 입금 신청을 폼으로 받고 시트에서 자동으로 미납자를 표시하게 만든 뒤, 총무와 2주간 함께 써 보며 칸 이름을 고쳤습니다. 바꾼 뒤 정리 시간은 30분으로, 누락은 0건으로 줄었습니다.",,Q0091
디자인,B2B · SaaS,경험,표나 대시보드처럼 데이터가 많은 화면을 만들어 본 경험이 있나요?,정보 밀도 · 가독성,"네, 판매자용 주문 대시보드를 만든 경험이 있습니다. 처음 시안은 지표 12개를 모두 같은 크기로 보여 줘서, 판매자 4명 테스트에서 '오늘 처리할 주문'을 찾는 데 평균 20초가 걸렸습니다. 그래서 오늘 할 일(새 주문 · 배송 지연) 2개를 맨 위 크게, 나머지는 표로 정렬 · 필터를 할 수 있게 바꿨습니다. 표는 숫자 오른쪽 정렬과 줄 간격을 맞췄고, 재테스트에서 같은 과제가 6초로 줄었습니다.",,Q0092
디자인,B2B · SaaS,상황,큰 고객사를 위해 맞춤 화면을 빨리 만들어 달라는 요청이 오면 어떻게 하나요?,범위 조정 · 제품 일관성,"요청의 진짜 목적을 확인하고, 제품 전체에 쓸 수 있는 범위로 줄여 빠르게 만드는 안을 제안합니다. 고객사가 원하는 것이 맞춤 화면 자체인지, 특정 업무를 빠르게 처리하는 것인지 영업 · PM과 함께 확인합니다. 기존 컴포넌트로 조합할 수 있는 최소 버전을 먼저 만들고, 다른 고객사도 쓸 수 있는 기능이면 정식 기능으로 일정을 잡습니다. 이렇게 하면 납기를 지키면서 디자인 시스템의 일관성도 지킬 수 있고, 적용 후 고객사 사용 데이터로 확장 여부를 결정합니다.",,Q0093
디자인,B2B · SaaS,상황,권한이 다른 사용자(관리자 · 일반)가 같은 화면에서 헷갈린다면 어떻게 하나요?,권한 표시 · 정보 구분,"지금 내가 어떤 권한인지와 무엇을 할 수 없는지를 화면에서 바로 알 수 있게 합니다. 화면 위에 '관리자로 보는 중' 같은 표시를 두고, 권한이 없는 기능은 숨기지 않고 이유와 요청 방법을 짧게 보여 줍니다. 관리자만 바꿀 수 있는 설정은 색과 아이콘으로 구분해, 일반 사용자가 헷갈리지 않게 합니다. 바꾼 안을 두 권한의 사용자 4명씩 테스트해 잘못된 작업 시도와 관련 문의가 줄었는지 확인합니다.",,Q0094
디자인,게임,직무,처음 하는 사용자에게 게임 규칙을 부담 없이 알려 주는 튜토리얼은 어떻게 설계하나요?,온보딩 · 점진적 안내,"규칙을 한 번에 설명하지 않고, 직접 해 보면서 하나씩 배우게 합니다. 첫 판은 이동 · 공격처럼 꼭 필요한 동작 2개만 화면 안내로 알려 주고, 사용자가 해냈을 때 바로 다음 규칙을 엽니다. 글 설명은 한 번에 한 문장으로 줄이고, 건너뛰기와 나중에 다시 보기를 둡니다. 팀 프로젝트에서 이렇게 바꿔 튜토리얼 완료율을 52%에서 81%로 올렸고, 첫날 다시 접속한 비율도 함께 늘었습니다.",,Q0095
디자인,게임,직무,상점이나 결제 화면에서 사용자를 오해하게 만들지 않으려면 무엇을 주의하나요?,투명한 표기 · 다크 패턴 경계,"사용자가 실제로 내는 돈과 받는 것을 가장 분명하게 보여 주는 것이 원칙입니다. 게임 재화로 사는 상품도 실제 금액을 함께 보여 주고, 확률형 아이템은 확률을 구매 버튼 가까이에 적습니다. 남은 시간 같은 압박 장치는 실제 이벤트일 때만 쓰고, 구매 직전에 수량과 금액을 한 번 더 확인합니다. 이 기준으로 상점 화면을 바꾼 뒤 결제 관련 환불 문의와 구매 만족도를 함께 확인합니다.",,Q0096
디자인,게임,경험,즐겨 한 게임에서 잘 만들었다고 느낀 UI와 그 이유를 말해 주세요.,분석력 · 근거,"즐겨 한 퍼즐 게임의 '힌트' UI를 잘 만들었다고 느꼈습니다. 막혔을 때만 화면 구석의 전구가 살짝 빛나서, 혼자 풀고 싶을 때는 방해하지 않고 필요할 때만 눈에 들어왔습니다. 힌트도 한 번에 답을 주지 않고 3단계로 조금씩 알려 줘서, 스스로 풀었다는 느낌을 지켜 줬습니다. 이 방식을 제 학습 앱 프로젝트의 도움말에 적용했고, 테스트에서 도움말을 쓴 사용자의 과제 완료율이 30% 높았습니다.",,Q0097
디자인,게임,경험,게임이나 인터랙티브 작업물을 만들어 본 경험이 있나요?,구현 이해 · 협업,"네, 팀원 3명과 2주 동안 간단한 모바일 퍼즐 게임을 만든 경험이 있습니다. 저는 UI와 인터랙션을 맡았고, 개발자와 매일 15분씩 화면을 직접 돌려 보며 맞췄습니다. 처음엔 버튼 효과를 화려하게 넣었다가 저사양 기기에서 프레임이 30 아래로 떨어져서, 효과를 가벼운 애니메이션으로 바꿨습니다. 완성 뒤 친구 10명에게 플레이 테스트를 받아 '조작이 쉽다'는 평가를 8명에게 받았고, 받은 피드백 5개를 반영했습니다.",,Q0098
디자인,게임,상황,작은 모바일 화면에서 버튼을 잘못 누른다는 불만이 많다면 어떻게 하나요?,터치 영역 · 테스트,"잘못 누르는 버튼을 데이터로 찾고, 터치 영역과 간격을 넓힌 뒤 테스트로 확인합니다. 클릭 데이터에서 바로 취소되는 터치나 인접 버튼 오입력이 많은 곳을 찾습니다. 그 버튼은 터치 영역을 최소 44~48px로 넓히고, 버튼 사이 간격을 두며, 되돌리기 어려운 버튼은 더 멀리 둡니다. 작은 화면 기기로 5명에게 같은 상황을 테스트해 오입력 횟수가 줄었는지 확인하고, 배포 뒤 관련 불만 글도 다시 봅니다.",,Q0099
디자인,게임,상황,화려한 연출을 원하는 기획과 로딩 중 이탈이 늘었다는 데이터가 부딪히면 어떻게 하나요?,성능과 연출의 균형 · 근거,"로딩 데이터로 연출의 비용을 보여 주고, 연출 의도는 지키면서 가볍게 만드는 안을 함께 찾습니다. 먼저 로딩 시간과 이탈률을 구간별로 보고, 예를 들어 로딩이 5초를 넘는 순간 이탈이 크게 늘어난다는 사실을 기획과 공유합니다. 연출이 꼭 보여 줘야 하는 장면이 무엇인지 묻고, 그 장면만 남기거나 로딩 뒤에 보여 주는 안을 만듭니다. 두 안을 실험해 로딩 시간 · 이탈률 · 연출 만족도를 함께 보고 결정합니다.",,Q0100
디자인,헬스케어,직무,측정 기기나 센서로 얻은 몸 데이터(자세 · 근력 · 관절 각도 등)를 사용자에게 보여 줄 때 무엇을 가장 조심하나요?,수치 해석 · 오해 방지 · 다음 행동으로 잇기,"숫자만 보여 주지 않고 '이게 좋은 건지, 다음에 뭘 하면 되는지'를 함께 보여 주는 것을 가장 조심합니다. 관절 각도 120도처럼 낯선 수치는 정상 범위 막대와 지난주 기록을 나란히 두고, 색만으로 좋고 나쁨을 말하지 않도록 글자를 함께 씁니다. 의학적 판단처럼 읽힐 문장은 '전문가와 상담하세요'로 이어지게 하고, 화면 아래에 오늘 할 운동 하나를 바로 연결합니다. 학교 과제에서 결과 화면을 이렇게 바꿨더니, 사용자 6명 테스트에서 수치를 잘못 해석한 사람이 4명에서 1명으로 줄었습니다.",재활/운동/근골격/물리치료/통증/자세/관절/진단기기/의료기기/센서/측정/웨어러블,Q0101
디자인,헬스케어,상황,집에서 하는 재활 운동을 2주 안에 그만두는 사용자가 많다면 어떻게 개선하나요?,이탈 원인 가설 · 동기 부여 · 검증 방법,"먼저 언제 그만두는지 데이터로 좁히고, 그만둔 사용자에게 이유를 직접 물어 원인을 나눈 뒤 하나씩 고칩니다. 예를 들어 3일째 이탈이 가장 많고 '운동이 맞게 하는 건지 모르겠다'는 답이 많다면, 동작마다 자세 확인 피드백과 짧은 시범 영상을 먼저 넣습니다. 매일 목표는 10분 이하로 작게 잡고, 치료사가 진행 기록을 보고 한마디 남기는 기능으로 혼자 하는 느낌을 줄입니다. 바꾼 뒤에는 2주 지속률을 기존 그룹과 비교해, 예를 들어 30%에서 45%로 올랐는지 확인하고 다음 개선을 정합니다.",재활/운동/근골격/물리치료/통증/자세/관절/진단기기/의료기기/센서/측정/웨어러블,Q0102
디자인,헬스케어,직무,치료사(전문가)가 쓰는 관리 화면과 환자가 쓰는 운동 화면을 어떻게 연결해 설계하겠어요?,사용자 구분 · 정보 흐름 · 신뢰,"치료사가 정한 계획이 환자 화면에 쉬운 말로 그대로 이어지고, 환자의 기록은 치료사 화면에 판단하기 좋은 형태로 돌아오게 설계합니다. 치료사 화면은 여러 환자를 빨리 훑도록 '이번 주 수행률 · 통증 변화 · 확인 필요' 순서의 표로 보여 주고, 환자 화면은 오늘 할 운동 3개와 남은 횟수만 크게 보여 줍니다. 환자가 남긴 통증 점수나 메모는 치료사 화면에 표시를 띄워 놓치지 않게 합니다. 이 흐름을 치료사 2명 · 환자 4명과 종이 프로토타입으로 시험해, 계획을 다시 묻는 문의가 줄어드는지 확인하겠습니다.",재활/운동/근골격/물리치료/통증/자세/관절/진단기기/의료기기/센서/측정/웨어러블,Q0103
개발,핀테크 · 금융,직무,송금 요청이 네트워크 오류로 두 번 들어와도 돈이 한 번만 빠져나가게 하려면 어떻게 설계하나요?,중복 요청 처리(멱등성) · 트랜잭션 이해,,,Q0104
개발,핀테크 · 금융,직무,금액을 계산할 때 소수점 오차가 생기지 않게 하려면 어떤 점을 주의하나요?,숫자 자료형 이해 · 정확성 검증 방법,,,Q0105
개발,핀테크 · 금융,상황,결제사는 승인했는데 우리 서비스 기록에는 실패로 남은 건이 발견됐다면 어떻게 대응하나요?,데이터 정합성 · 원인 추적 · 사용자 보호,,,Q0106
개발,핀테크 · 금융,상황,계좌번호 같은 개인정보가 로그에 그대로 남고 있는 것을 발견했다면 어떻게 하나요?,보안 감수성 · 대응 우선순위 · 공유,,,Q0107
개발,핀테크 · 금융,경험,"써 본 금융 앱에서 '안전하게 만들어졌다'고 느낀 기능을 하나 골라, 개발자 입장에서 어떻게 구현됐을지 설명해 주세요.",사용자 관점의 보안 이해 · 기술적 추론,,,Q0108
개발,커머스,직무,한정 판매처럼 주문이 한꺼번에 몰릴 때 재고보다 많이 팔리지 않게 하려면 어떻게 하나요?,동시성 처리 · 재고 정합성,,,Q0109
개발,커머스,직무,상품 목록 화면이 느리다는 문의가 왔을 때 어디부터 확인하나요?,성능 병목 찾기 · 측정 방법,,,Q0110
개발,커머스,상황,할인 쿠폰이 조건과 다르게 중복 적용되는 버그를 운영 중에 발견했다면 어떻게 대응하나요?,장애 대응 순서 · 영향 범위 파악 · 재발 방지,,,Q0111
개발,커머스,상황,다음 주 기획전에 맞춰 새 기능을 요청받았는데 일정이 빠듯하다면 어떻게 조율하나요?,범위 조율 · 리스크 공유,,,Q0112
개발,커머스,경험,"쇼핑 앱이나 쇼핑몰에서 불편했던 기능 하나를 골라, 개발자로서 어떻게 고칠지 말해 주세요.",문제 발견 · 구현 방안의 구체성,,,Q0113
개발,헬스케어,직무,진료 기록 같은 민감한 건강 정보를 저장하고 보여 줄 때 어떤 보호 장치를 두나요?,접근 권한 · 암호화 · 접근 기록 이해,,,Q0114
개발,헬스케어,직무,웨어러블 기기에서 들어오는 측정값이 가끔 비어 있거나 튀는 값일 때 어떻게 처리하나요?,데이터 검증 · 예외 처리,,,Q0115
개발,헬스케어,상황,복약 알림이 일부 사용자에게 오지 않는다는 문의가 들어왔다면 원인을 어떻게 찾나요?,재현 · 로그 확인 · 사용자 안전 우선,,,Q0116
개발,헬스케어,상황,의료진은 기능을 빨리 원하고 보안 검토에는 시간이 걸린다면 어떻게 진행하겠어요?,안전성과 속도의 균형 · 소통,,,Q0117
개발,헬스케어,경험,병원 예약이나 건강 관리 앱을 쓰며 믿음이 갔거나 불안했던 점을 하나 골라 기술적으로 설명해 주세요.,사용자 관점 · 신뢰와 기술의 연결,,,Q0118
개발,B2B · SaaS,직무,여러 회사가 같은 서비스를 쓸 때 한 회사의 데이터가 다른 회사에 보이지 않게 하려면 어떻게 설계하나요?,데이터 분리(멀티 테넌시) · 권한 설계,,,Q0119
개발,B2B · SaaS,직무,관리자와 일반 직원처럼 역할마다 할 수 있는 일을 다르게 하려면 권한을 어떻게 나누나요?,권한 모델 · 확장성,,,Q0120
개발,B2B · SaaS,상황,한 고객사에서만 데이터 내보내기가 아주 느리다는 문의가 왔다면 어떻게 확인하나요?,문제 범위 좁히기 · 데이터 양 고려,,,Q0121
개발,B2B · SaaS,상황,큰 고객사가 자기 회사만을 위한 기능을 요청했다면 개발자로서 무엇을 함께 검토하나요?,제품 전체 영향 · 유지보수 비용,,,Q0122
개발,B2B · SaaS,경험,"메신저 · 문서 · 일정 관리 같은 협업 도구를 쓰며 느낀 불편을 하나 골라, 어떤 기술로 개선할지 말해 주세요.",문제 정의 · 기술적 해결 방안,,,Q0123
개발,게임,직무,여러 명이 함께 플레이할 때 서로의 화면이 어긋나 보이는 문제를 줄이려면 어떤 방법이 있나요?,동기화 · 지연 처리 이해,,,Q0124
개발,게임,직무,아이템이나 재화를 조작하는 부정 행위를 막으려면 어디에서 검증해야 하나요?,서버 검증 · 보안 감수성,,,Q0125
개발,게임,상황,새 이벤트 시작 직후 접속자가 몰려 서버 응답이 느려졌다면 무엇부터 하나요?,장애 대응 우선순위 · 모니터링,,,Q0126
개발,게임,상황,업데이트 뒤 특정 기기에서만 게임이 꺼진다는 제보가 이어진다면 어떻게 대응하나요?,재현 · 기기 환경 분석 · 공지 협업,,,Q0127
개발,게임,경험,즐겨 한 게임에서 인상 깊었던 시스템(매칭 · 랭킹 · 저장 등)을 하나 골라 어떻게 구현됐을지 설명해 주세요.,구조적 사고 · 기술 추론,,,Q0128
개발,모빌리티 · 여행,직무,실시간 위치를 지도에 보여 줄 때 배터리와 데이터 사용을 줄이려면 어떻게 하나요?,실시간 처리 · 자원 효율,,,Q0129
개발,모빌리티 · 여행,직무,요금이 거리와 시간에 따라 계산될 때 그 계산이 맞는지 어떻게 검증하고 테스트하나요?,계산 로직 검증 · 테스트 설계,,,Q0130
개발,모빌리티 · 여행,상황,외부 지도나 결제 서비스가 갑자기 응답하지 않으면 우리 서비스는 어떻게 동작해야 하나요?,외부 의존성 장애 대비 · 사용자 안내,,,Q0131
개발,모빌리티 · 여행,상황,통신이 불안정한 여행지에서 예약 확인이 안 된다는 문의가 많다면 어떻게 개선하나요?,오프라인 대응 · 사용 환경 이해,,,Q0132
개발,모빌리티 · 여행,경험,지도 · 택시 · 숙소 앱에서 위치나 시간이 실제와 달라 불편했던 경험을 하나 골라 기술적으로 분석해 주세요.,문제 분석 · 원인 추론,,,Q0133
PO,커머스,직무,구매 전환율이 떨어졌을 때 어떤 지표를 어떤 순서로 확인하나요?,퍼널 이해 · 지표 해석,,,Q0134
PO,커머스,직무,신규 고객 늘리기와 재구매 늘리기 중 이번 분기 목표를 하나만 정해야 한다면 무엇을 근거로 정하나요?,우선순위 근거 · 비즈니스 이해,,,Q0135
PO,커머스,상황,"영업팀은 대형 할인 기획전을, 개발팀은 결제 안정화를 먼저 하자고 한다면 어떻게 결정하나요?",이해관계자 조율 · 리스크 판단,,,Q0136
PO,커머스,상황,반품이 늘었는데 이유의 대부분이 '사진과 다름'이라면 어떤 문제로 정의하고 무엇을 하겠어요?,문제 정의 · 해결안 설계,,,Q0137
PO,커머스,경험,"자주 쓰는 쇼핑 서비스에서 다시 사게 만드는 장치를 하나 골라, 왜 효과가 있는지 설명해 주세요.",사용자 행동 이해 · 서비스 분석,,,Q0138
PO,핀테크 · 금융,직무,"가입 단계의 본인 인증에서 이탈이 많을 때, 규제를 지키면서 개선할 방법을 어떻게 찾나요?",규제와 사용성의 균형 · 퍼널 분석,,,Q0139
PO,핀테크 · 금융,직무,새 금융 기능을 출시할 때 성공 지표와 함께 꼭 지켜봐야 할 위험 지표는 무엇인가요?,지표 설계 · 리스크 관점,,,Q0140
PO,핀테크 · 금융,상황,이상 거래 차단을 강화하자 정상 사용자의 결제 실패 문의도 늘었다면 어떻게 판단하나요?,트레이드오프 판단 · 데이터 기반 결정,,,Q0141
PO,핀테크 · 금융,상황,출시 직전에 법무팀이 안내 문구를 고쳐야 한다고 한다면 일정과 범위를 어떻게 조정하나요?,이해관계자 조율 · 일정 관리,,,Q0142
PO,핀테크 · 금융,경험,"써 본 금융 앱에서 '믿을 수 있다'고 느끼게 한 요소를 하나 골라, 제품 관점에서 설명해 주세요.",신뢰 요소 이해 · 분석력,,,Q0143
PO,에듀테크,직무,학습 서비스의 성과를 접속 수가 아니라 학습 효과로 확인하려면 어떤 지표를 쓰겠어요?,지표 설계 · 학습 효과 이해,,,Q0144
PO,에듀테크,직무,학습자와 결제하는 사람(학부모 · 회사)이 다를 때 누구의 문제를 먼저 풀지 어떻게 정하나요?,사용자와 구매자 구분 · 우선순위,,,Q0145
PO,에듀테크,상황,무료 체험 뒤 유료 전환은 높은데 한 달 뒤까지 학습을 이어 가는 사람이 적다면 무엇을 하겠어요?,리텐션 문제 정의 · 가설 수립,,,Q0146
PO,에듀테크,상황,강사 · 콘텐츠팀이 원하는 기능과 학습자 데이터가 가리키는 문제가 다르다면 어떻게 조율하나요?,데이터와 이해관계자 조율,,,Q0147
PO,에듀테크,경험,"공부할 때 써 본 앱이나 강의 중 끝까지 하게 만든 장치가 있었다면, 그 이유를 제품 관점에서 분석해 주세요.",동기 부여 이해 · 분석력,,,Q0148
PO,헬스케어,직무,건강 관리 앱에서 사용자가 꾸준히 기록하게 하려면 어떤 문제부터 정의하겠어요?,문제 정의 · 행동 변화 이해,,,Q0149
PO,헬스케어,직무,의료 정보와 관련된 기능을 기획할 때 일반 서비스보다 더 확인해야 할 것은 무엇인가요?,규제 · 안전 · 개인정보 감수성,,,Q0150
PO,헬스케어,상황,"의사는 정확한 정보를, 환자는 쉬운 설명을 원할 때 화면에 담을 정보를 어떻게 정하겠어요?",사용자 간 요구 조율,,,Q0151
PO,헬스케어,상황,병원 예약 기능을 출시한 뒤 예약을 지키지 않는 노쇼가 늘었다면 원인을 어떻게 찾고 개선하겠어요?,데이터 분석 · 가설 검증,,,Q0152
PO,헬스케어,경험,"병원 · 약국 · 건강 앱을 이용하며 불편했던 순간을 하나 골라, 어떤 제품 문제인지 정의해 주세요.",문제 발견 · 정의력,,,Q0153
PO,B2B · SaaS,직무,고객사에서 구매를 결정하는 사람과 실제로 쓰는 사람이 다를 때 각자의 요구를 어떻게 파악하나요?,고객 구조 이해 · 요구 수집,,,Q0154
PO,B2B · SaaS,직무,여러 고객사에서 들어온 기능 요청 중 무엇을 먼저 만들지 어떤 기준으로 정하나요?,우선순위 기준 · 근거,,,Q0155
PO,B2B · SaaS,상황,계약 갱신을 앞둔 큰 고객사의 사용률이 낮다면 무엇을 확인하고 어떻게 하겠어요?,사용 데이터 분석 · 고객 성공 관점,,,Q0156
PO,B2B · SaaS,상황,영업팀이 아직 없는 기능을 고객에게 약속했다면 어떻게 대응하겠어요?,이해관계자 조율 · 기대 관리,,,Q0157
PO,B2B · SaaS,경험,"학교나 팀 프로젝트에서 쓴 협업 도구 중 잘 자리 잡은 것과 그렇지 않은 것을 비교해, 그 차이를 설명해 주세요.",도입 과정 이해 · 비교 분석,,,Q0158
PO,모빌리티 · 여행,직무,예약 취소율이 높아졌을 때 이용자 쪽 문제와 공급자(숙소 · 기사) 쪽 문제를 어떻게 나눠 보나요?,양면 시장 이해 · 문제 분해,,,Q0159
PO,모빌리티 · 여행,직무,성수기와 비수기의 수요 차이가 큰 서비스에서 어떤 지표로 성과를 보겠어요?,지표 설계 · 계절성 고려,,,Q0160
PO,모빌리티 · 여행,상황,배차 대기 시간이 길다는 불만이 많을 때 기사 쪽 개선과 승객 쪽 개선 중 무엇부터 하겠어요?,우선순위 판단 · 근거,,,Q0161
PO,모빌리티 · 여행,상황,날씨나 교통 때문에 일정이 바뀐 여행자를 서비스가 어떻게 도와야 할지 어떻게 정하겠어요?,현장 맥락 이해 · 기능 범위 정의,,,Q0162
PO,모빌리티 · 여행,경험,"여행이나 이동 중 앱 때문에 곤란했던 경험을 하나 골라, 어떤 제품 문제였고 어떻게 고칠지 말해 주세요.",문제 정의 · 해결안,,,Q0163
마케팅,커머스,직무,같은 광고비로 첫 구매 고객을 늘리려면 어떤 채널과 지표를 보며 운영하겠어요?,채널 이해 · 성과 지표,,,Q0164
마케팅,커머스,직무,장바구니에 담고 사지 않은 고객에게 어떤 메시지를 언제 보내 구매를 유도하겠어요?,타깃 세분화 · 리타기팅 설계,,,Q0165
마케팅,커머스,상황,할인 행사로 매출은 늘었는데 이익이 줄었다면 다음 행사를 어떻게 바꾸겠어요?,매출과 수익성 구분 · 개선안,,,Q0166
마케팅,커머스,상황,상품 리뷰에 부정적인 글이 갑자기 늘었다면 마케터로서 무엇부터 하겠어요?,위기 대응 · 유관 부서 협업,,,Q0167
마케팅,커머스,경험,"최근 사고 싶어졌던 상품 광고나 콘텐츠를 하나 골라, 왜 효과가 있었는지 분석해 주세요.",소비자 심리 이해 · 분석력,,,Q0168
마케팅,콘텐츠 · 미디어,직무,새 콘텐츠(영상 · 웹툰 · 음악)를 공개하는 첫 주에 관심을 모으려면 어떤 계획을 세우겠어요?,출시 캠페인 설계 · 채널 선택,,,Q0169
마케팅,콘텐츠 · 미디어,직무,구독형 서비스에서 신규 가입보다 해지 방지가 더 중요할 때 어떤 마케팅을 하겠어요?,리텐션 마케팅 · 지표 이해,,,Q0170
마케팅,콘텐츠 · 미디어,상황,공들인 홍보 영상의 조회수는 높은데 가입으로 이어지지 않는다면 무엇을 확인하겠어요?,퍼널 분석 · 가설 수립,,,Q0171
마케팅,콘텐츠 · 미디어,상황,함께 일한 크리에이터가 논란에 휘말렸다면 마케터로서 어떻게 대응하겠어요?,위기 대응 · 브랜드 보호,,,Q0172
마케팅,콘텐츠 · 미디어,경험,"즐겨 보는 콘텐츠를 처음 알게 된 경로를 떠올려, 그 홍보 방식이 왜 효과적이었는지 말해 주세요.",유입 경로 이해 · 분석력,,,Q0173
마케팅,게임,직무,새 게임 출시 전 사전 예약자를 모으는 캠페인을 어떻게 기획하겠어요?,캠페인 기획 · 타깃 설정,,,Q0174
마케팅,게임,직무,출시 뒤 설치 수는 많은데 일주일 뒤 남는 이용자가 적다면 어떤 지표를 보겠어요?,리텐션 지표 · 원인 가설,,,Q0175
마케팅,게임,상황,업데이트 뒤 커뮤니티에 불만 글이 쏟아진다면 마케팅팀은 무엇을 해야 할까요?,커뮤니티 소통 · 협업,,,Q0176
마케팅,게임,상황,떠난 이용자를 다시 부르는 이벤트에 기존 이용자가 차별받는다고 느낀다면 어떻게 하겠어요?,이해관계 균형 · 이벤트 설계,,,Q0177
마케팅,게임,경험,"해 본 게임 중 이벤트나 광고 때문에 다시 접속했던 경험을 떠올려, 효과가 있었던 이유를 분석해 주세요.",이용자 동기 이해 · 분석력,,,Q0178
마케팅,에듀테크,직무,학생과 학부모처럼 쓰는 사람과 결제하는 사람이 다를 때 메시지를 어떻게 나눠 전하겠어요?,타깃 구분 · 메시지 설계,,,Q0179
마케팅,에듀테크,직무,무료 체험 신청자를 유료 수강생으로 바꾸려면 체험 기간에 무엇을 하겠어요?,전환 설계 · 단계별 커뮤니케이션,,,Q0180
마케팅,에듀테크,상황,시험 시즌이 끝나자 신규 가입이 크게 줄었다면 다음 분기 계획을 어떻게 세우겠어요?,시즌성 이해 · 계획 수립,,,Q0181
마케팅,에듀테크,상황,'단기간 성적 향상'처럼 과장된 광고 문구를 쓰자는 의견이 나온다면 어떻게 하겠어요?,광고 윤리 · 대안 제시,,,Q0182
마케팅,에듀테크,경험,"공부 관련 서비스나 강의를 고를 때 결정에 영향을 준 정보를 떠올려, 마케터 관점에서 분석해 주세요.",의사 결정 요인 이해 · 분석력,,,Q0183
마케팅,핀테크 · 금융,직무,금융 상품을 홍보할 때 광고 문구에서 특히 조심해야 할 점은 무엇인가요?,규제 · 소비자 보호 감수성,,,Q0184
마케팅,핀테크 · 금융,직무,가입 혜택만 받고 바로 떠나는 고객을 줄이려면 혜택을 어떻게 설계하겠어요?,혜택 설계 · 장기 고객 가치,,,Q0185
마케팅,핀테크 · 금융,상황,경쟁사가 더 큰 가입 혜택을 내놓아 가입자가 줄었다면 어떻게 대응하겠어요?,경쟁 대응 · 차별점 찾기,,,Q0186
마케팅,핀테크 · 금융,상황,보안 사고가 났다는 소문이 SNS에 퍼져 이탈이 늘고 있다면 마케팅팀은 무엇을 해야 할까요?,위기 커뮤니케이션 · 신뢰 회복,,,Q0187
마케팅,핀테크 · 금융,경험,"금융 앱을 처음 설치하게 된 계기를 떠올려, 어떤 메시지나 혜택이 결정에 영향을 줬는지 분석해 주세요.",고객 여정 이해 · 분석력,,,Q0188
마케팅,헬스케어,직무,건강 관리 앱을 알릴 때 효과를 부풀리지 않으면서도 매력적으로 전하려면 어떻게 하겠어요?,신뢰 기반 메시지 · 표현 기준,,,Q0189
마케팅,헬스케어,직무,건강 관리 앱의 새 사용자를 모을 때 타깃을 어떻게 나누고 각각 어떤 메시지를 쓰겠어요?,타깃 세분화 · 메시지 설계,,,Q0190
마케팅,헬스케어,상황,의료진 인터뷰 콘텐츠의 반응은 좋은데 앱 설치로 이어지지 않는다면 무엇을 바꾸겠어요?,콘텐츠와 전환 연결,,,Q0191
마케팅,헬스케어,상황,제휴한 병원이나 약국이 우리 홍보 방식에 이견을 보인다면 어떻게 조율하겠어요?,제휴처 협업 · 조율,,,Q0192
마케팅,헬스케어,경험,"운동 · 식단 · 수면 같은 건강 관리 서비스를 시작하거나 그만둔 경험을 떠올려, 그 이유를 마케팅 관점에서 분석해 주세요.",동기와 이탈 이해 · 분석력,,,Q0193
```

---

## 부록 D — 모의 AI 응답 `tests/fixtures/ai/*.json` (그대로 저장)

### `tests/fixtures/ai/interviewer.json`

```json
{
 "_note": "면접관 응답 (INTERVIEWER_SCHEMA · ask_json name 'interviewer'). cases 는 응답 하나, sequences 는 5문항 면접을 끝까지 진행하는 응답 순서. edge_cases 는 스키마는 맞지만 값이 범위 밖인 응답 (앱이 잘라 쓴다).",
 "cases": {
  "follow_up": {"reply": "결과는 이해했습니다. 그 수치는 어떤 방법으로, 몇 명을 대상으로 확인하셨나요?", "follow_up": true, "understanding": 55},
  "enough": {"reply": "네, 이해했습니다.", "follow_up": false, "understanding": 62},
  "wants_more": {"reply": "그때 팀에서 반대 의견은 없었나요?", "follow_up": true, "understanding": 64},
  "feedback_follow_up": {"reply": "그 화면을 바꾸기로 결정한 근거는 무엇이었나요?", "follow_up": true, "understanding": 58},
  "feedback_review": {"reply": "강점은 문제를 사용자 관찰로 찾은 점이에요. 보완점은 결과를 숫자로 확인한 과정이 빠진 점이에요. 다음에는 측정 방법을 한 문장 더해 보세요.", "follow_up": false, "understanding": 66},
  "feedback_review_flag_true": {"reply": "강점은 협업 과정을 구체적으로 말한 점이에요. 보완점은 본인 역할이 흐린 점이에요.", "follow_up": true, "understanding": 67}
 },
 "edge_cases": {
  "understanding_out_of_range": {"reply": "네, 이해했습니다.", "follow_up": false, "understanding": 150}
 },
 "sequences": {
  "probe_one_follow_up": ["follow_up", "enough", "enough", "enough", "enough", "enough"],
  "probe_follow_up_limit": ["follow_up", "wants_more", "enough", "enough", "enough", "enough"],
  "feedback_every_question": ["feedback_follow_up", "feedback_review", "feedback_follow_up", "feedback_review", "feedback_follow_up", "feedback_review", "feedback_follow_up", "feedback_review", "feedback_follow_up", "feedback_review_flag_true"]
 }
}
```

### `tests/fixtures/ai/evaluation.json`

```json
{
 "_note": "평가 위원회 응답 (EVAL_SCHEMA · ask_json name 'evaluation'). cases 는 정상 응답. edge_cases 는 스키마는 맞지만 지금 코드가 잘못 처리하는 응답 (test_engine KnownBehaviorTest #3 · #4) — 1차 평가 응답 검증 작업에서 쓴다.",
 "cases": {
  "mixed": {
   "panel": [
    {"role": "실무 전문가", "against": "툴 사용 근거가 한 가지 사례에 그쳐요.", "good": "프로토타입으로 바로 검증한 점이 좋아요.", "score": 7},
    {"role": "논리 분석가", "against": "원인과 결과의 연결이 일부 비어 있어요.", "good": "문제 정의가 분명해요.", "score": 6},
    {"role": "커뮤니케이션 전문가", "against": "결론이 답 끝에 나와요.", "good": "질문 의도에 맞게 답했어요.", "score": 8},
    {"role": "채용 담당자", "against": "회사 서비스와의 연결이 약해요.", "good": "협업 태도가 보여요.", "score": 7}
   ],
   "conflict": "근거의 충분함은 위원마다 판단이 갈렸어요.",
   "agree": "문제를 사용자 관찰로 찾는 태도는 모두 좋게 봤어요.",
   "answers": [
    {"no": 1, "specific": 5, "relevance": 5, "structure": 5, "evidence": 5, "weak": "마무리 한 문장이 있으면 더 좋아요.", "rewrite": "", "check": []},
    {"no": 2, "specific": 2, "relevance": 3, "structure": 1, "evidence": 4, "weak": "답의 순서가 흐려요.", "rewrite": "결론부터 말하고, 문제 → 행동 → 결과 순서로 이어 주세요.", "check": ["[확인 필요: 프로젝트 기간]"]},
    {"no": 3, "specific": 3, "relevance": 3, "structure": 3, "evidence": 3, "weak": "본인 역할이 흐려요.", "rewrite": "제가 맡은 부분은 ○○이었고, 이렇게 해결했습니다.", "check": []},
    {"no": 4, "specific": 4, "relevance": 4, "structure": 3, "evidence": 4, "weak": "결과 다음 배운 점이 빠졌어요.", "rewrite": "", "check": []},
    {"no": 5, "specific": 2, "relevance": 1, "structure": 2, "evidence": 3, "weak": "질문과 다른 경험을 말했어요.", "rewrite": "질문의 상황에 맞는 경험 하나로 다시 답해 보세요.", "check": ["[확인 필요: 사용자 수]", "[확인 필요: 개선 전후 수치]"]}
   ],
   "next": ["결론부터 말하기", "본인 역할을 한 문장으로 먼저", "결과 뒤에 배운 점 붙이기"]
  },
  "perfect": {
   "panel": [
    {"role": "실무 전문가", "against": "뽑지 않을 이유를 찾기 어려워요.", "good": "실무 적용이 바로 보여요.", "score": 10},
    {"role": "논리 분석가", "against": "뽑지 않을 이유를 찾기 어려워요.", "good": "흐름이 분명해요.", "score": 10},
    {"role": "커뮤니케이션 전문가", "against": "뽑지 않을 이유를 찾기 어려워요.", "good": "간결해요.", "score": 10},
    {"role": "채용 담당자", "against": "뽑지 않을 이유를 찾기 어려워요.", "good": "회사와 잘 맞아요.", "score": 10}
   ],
   "conflict": "판단이 갈린 곳이 없어요.",
   "agree": "모든 답이 구체적이에요.",
   "answers": [
    {"no": 1, "specific": 5, "relevance": 5, "structure": 5, "evidence": 5, "weak": "", "rewrite": "", "check": []},
    {"no": 2, "specific": 5, "relevance": 5, "structure": 5, "evidence": 5, "weak": "", "rewrite": "", "check": []},
    {"no": 3, "specific": 5, "relevance": 5, "structure": 5, "evidence": 5, "weak": "", "rewrite": "", "check": []},
    {"no": 4, "specific": 5, "relevance": 5, "structure": 5, "evidence": 5, "weak": "", "rewrite": "", "check": []},
    {"no": 5, "specific": 5, "relevance": 5, "structure": 5, "evidence": 5, "weak": "", "rewrite": "", "check": []}
   ],
   "next": ["실전처럼 소리 내어 연습하기"]
  }
 },
 "edge_cases": {
  "missing_role": {
   "panel": [
    {"role": "실무 전문가", "against": "근거가 약해요.", "good": "실무 감각이 있어요.", "score": 8}
   ],
   "conflict": "", "agree": "",
   "answers": [
    {"no": 1, "specific": 4, "relevance": 4, "structure": 4, "evidence": 4, "weak": "", "rewrite": "", "check": []},
    {"no": 2, "specific": 4, "relevance": 4, "structure": 4, "evidence": 4, "weak": "", "rewrite": "", "check": []},
    {"no": 3, "specific": 4, "relevance": 4, "structure": 4, "evidence": 4, "weak": "", "rewrite": "", "check": []},
    {"no": 4, "specific": 4, "relevance": 4, "structure": 4, "evidence": 4, "weak": "", "rewrite": "", "check": []},
    {"no": 5, "specific": 4, "relevance": 4, "structure": 4, "evidence": 4, "weak": "", "rewrite": "", "check": []}
   ],
   "next": []
  },
  "zero_based_numbers": {
   "panel": [
    {"role": "실무 전문가", "against": "", "good": "", "score": 7},
    {"role": "논리 분석가", "against": "", "good": "", "score": 7},
    {"role": "커뮤니케이션 전문가", "against": "", "good": "", "score": 7},
    {"role": "채용 담당자", "against": "", "good": "", "score": 7}
   ],
   "conflict": "", "agree": "",
   "answers": [
    {"no": 0, "specific": 1, "relevance": 1, "structure": 1, "evidence": 1, "weak": "답 1", "rewrite": "", "check": []},
    {"no": 1, "specific": 2, "relevance": 2, "structure": 2, "evidence": 2, "weak": "답 2", "rewrite": "", "check": []},
    {"no": 2, "specific": 3, "relevance": 3, "structure": 3, "evidence": 3, "weak": "답 3", "rewrite": "", "check": []},
    {"no": 3, "specific": 4, "relevance": 4, "structure": 4, "evidence": 4, "weak": "답 4", "rewrite": "", "check": []},
    {"no": 4, "specific": 5, "relevance": 5, "structure": 5, "evidence": 5, "weak": "답 5", "rewrite": "", "check": []}
   ],
   "next": []
  }
 }
}
```

### `tests/fixtures/ai/retry.json`

```json
{
 "_note": "재도전 채점 응답 (RETRY_SCHEMA · ask_json name 'retry'). 점수는 evaluation.json 의 mixed 와 비교하도록 골랐다 (mixed 2번 10점 · 5번 8점). edge_cases 는 범위 밖 점수 (앱이 0~5 로 자른다).",
 "cases": {
  "improved": {"specific": 4, "relevance": 4, "structure": 4, "evidence": 4, "weak": "결과 수치의 출처를 한 번 더 밝혀 주세요."},
  "same": {"specific": 2, "relevance": 3, "structure": 1, "evidence": 4, "weak": "순서는 그대로 흐려요."},
  "lower": {"specific": 1, "relevance": 1, "structure": 1, "evidence": 1, "weak": "질문과 다른 이야기를 했어요."},
  "perfect": {"specific": 5, "relevance": 5, "structure": 5, "evidence": 5, "weak": ""}
 },
 "edge_cases": {
  "out_of_range": {"specific": 7, "relevance": -1, "structure": 5, "evidence": 5, "weak": "범위 밖 점수"}
 }
}
```

---

## 부록 E — `data/평가기준_근거.md` (그대로 저장)

````markdown
#### 왜 위원 4명이 같은 기준으로 보나요?

이 앱의 평가는 **구조화 면접(structured interview)** 방식을 따라요. 같은 직무의 지원자에게 같은 질문을 하고, **미리 정한 기준과 같은 척도**로 답을 채점하는 방식이에요.

- Google re:Work는 구조화 면접을 "같은 직무에 지원한 사람을 같은 방법으로 평가하는 것"이라고 설명해요. 구성 요소로 직무와 관련된 질문, 표준화된 채점 기준(rubric), 상세한 피드백, 면접관 교육과 기준 맞추기(calibration)를 들어요. 또 구조화 면접이 예측력을 높이고 집단 간 점수 차이를 줄인다는 연구 결과를 소개해요. [1]
- 인사 선발 방법 85년치 연구를 종합한 메타분석(Schmidt & Hunter, 1998)에서 구조화 면접의 직무 성과 예측 타당도는 약 .51로, 비구조화 면접보다 높은 편이었어요. [2] 2016년 개정 분석에서도 구조화 면접은 예측력이 높은 선발 방법 조합에 들어가요. [3]
- 국내 공공기관의 NCS(국가직무능력표준) 기반 채용과 블라인드 채용도 학력 · 외모처럼 직무와 무관한 정보를 빼고 **직무 수행 능력**으로 평가하는 구조화 면접을 써요. [4][5]

그래서 위원마다 **보는 관점(기준)을 미리 글로 정하고**, 화면과 AI 채점에 **같은 기준**을 써요.

#### 위원별 기준은 어디서 왔나요?

| 위원 | 평가 기준 | 근거 |
| --- | --- | --- |
| 실무 전문가 | 직무 지식 · 툴 숙련도, 실제 업무에 바로 쓸 수 있는 경험인가 | Google re:Work의 평가 항목 **직무 관련 지식(role-related knowledge)**: 그 역할에 필요한 전문성을 갖췄는지 [1] · NCS 직무수행능력(직무별 지식 · 기술 · 태도) [5] |
| 논리 분석가 | 문제 → 원인 → 해결 → 결과 흐름이 맞고, 주장과 근거가 연결되는가 | Google re:Work의 평가 항목 **문제 해결(problem solving)**: 복잡한 상황을 어떻게 분석해 해결에 이르는지 [1] |
| 커뮤니케이션 전문가 | 결론부터 간결하게 말하고, 질문 의도에 맞게 답하는가 | NCS 직업기초능력의 **의사소통능력** (예: 상대가 이해하지 못할 때 어떻게 다시 설명하는지 묻는 문항) [5] |
| 채용 담당자 | 회사 · 직무 적합성, 협업 태도, 성장 가능성 | Google re:Work의 평가 항목 **리더십**: 직책이 없어도 주도하는 모습(emergent leadership) [1] · 블라인드 채용의 원칙: 직무와 관련된 근거로만 판단 [4] |

#### 알아 둘 점

- 이 평가는 **연습용 AI 모의 평가**예요. 실제 회사의 평가표와 배점은 회사마다 달라요. 지원하는 회사의 채용 공고와 직무기술서를 꼭 함께 보세요.
- [2][3]의 수치는 논문 요약 자료를 기준으로 적었어요.

#### 출처

1. Google re:Work, *A guide to structured interviewing for better hiring practices* — https://rework.withgoogle.com/intl/en/guides/a-guide-to-structured-interviewing-for-better-hiring-practices
2. Schmidt, F. L., & Hunter, J. E. (1998). The validity and utility of selection methods in personnel psychology. *Psychological Bulletin*, 124(2) — https://stafforini.com/works/schmidt-1998-validity-and-utility/
3. Schmidt, F. L., Oh, I.-S., & Shaffer, J. A. (2016). The validity and utility of selection methods in personnel psychology: Practical and theoretical implications of 100 years of research findings (working paper) — https://home.ubalt.edu/tmitch/645/session%204/Schmidt%20&%20Oh%20validity%20and%20util%20100%20yrs%20of%20research%20Wk%20PPR%202016.pdf
4. 대한민국 정책브리핑, 블라인드 채용 관련 보도 — https://www.korea.kr/news/policyNewsView.do?newsId=148793769
5. 캐치(CATCH), NCS 채용 가이드 — https://www.catch.co.kr/Guide/NCSGuideAtoZ5 · 공식 기준은 NCS 종합정보망 https://www.ncs.go.kr 에서 확인할 수 있어요.
````

