# 역전 취업 코칭 — 프롬프트 목록 (PROMPT_INVENTORY)

> 기준 시점: 2026-11-04 · `main` 브랜치 (`d10-interview/` 기준 경로)
> 대화 기록 시각은 한국 시간(KST)으로 적었다.
> 조사 범위: `prompts.py` · `coach.py` · `app.py` · `llm.py` 의 실제 코드, `prompts.py` Git 이력 10개 커밋 (2026-10-27 ~ 11-03), `CLAUDE.md` · `prd/` 문서, Claude Code 대화 기록 6개 세션 (2026-10-29 ~ 11-04)
> 원본 파일은 수정하지 않았다. 이 목록은 제출 문서 `PROMPT_SUBMISSION.md` 에 무엇을 넣고 뺐는지 기록한다.

상태 표기
- **사용 중**: 화면에서 실제로 호출된다.
- **코드만 있음**: 함수는 있지만 현재 화면에서 부르지 않는다.
- **도달 불가**: 코드 경로는 있지만 현재 설정으로는 실행되지 않는다.

작성자 표기 (코드 주석 · 대화 기록 기준)
- **사용자**: 사용자가 직접 쓴 문장 (대화 기록 또는 `CLAUDE.md` 의 "프롬프트는 내가 쓴다" 규칙)
- **Claude 초안**: `prompts.py` 주석에 "Claude Code 초안 — 사용자 확인 필요" 로 표시된 문장
- **확인 불가**: 첫 작성 대화(10-27 ~ 10-28)가 대화 기록에 없어 누가 썼는지 확인할 수 없음

---

## 1. AI 기능 프롬프트 (OpenAI 에 실제로 보내는 지시문)

모든 호출은 `llm.ask_json(instructions, user_input, schema, name)` 한 곳을 지난다 (OpenAI Responses API · `json_schema` · `strict: true`).

| ID | 이름 (`prompts.py`) | 기능 | 지시문을 만드는 곳 → 호출하는 곳 | user_input | 응답 스키마 | 상태 | 작성자 | 제출 문서 |
|---|---|---|---|---|---|---|---|---|
| P-01 | `INTERVIEWER` | 면접관 반응 · 꼬리 질문 판단 · 이해도 | `coach.build_interviewer` → `app.send_answer` | 지금까지 대화 기록 (`coach.format_transcript`) | `INTERVIEWER_SCHEMA` | 사용 중 | 확인 불가 (첫 작성) · 11-02 개선은 사용자 승인 문구 반영 | **원문 포함** |
| P-02 | `EVALUATOR` | 평가 위원 4명 채점 · 답변별 기준 점수 · 다듬은 답 | `coach.build_evaluator` → `app.request_evaluation` | 면접 기록 + 질문별 [보는 점] (`coach.format_record`) | `EVAL_SCHEMA` | 사용 중 | 확인 불가 (첫 작성) · 11-03 추가 문장은 사용자 권장 문구 그대로 | **원문 포함** |
| P-03 | `RETRY` | 재도전 답 채점 | `coach.build_retry` → `app.show_retry` | 다시 쓴 답 | `RETRY_SCHEMA` | 사용 중 | 확인 불가 | **원문 포함** |
| P-04 | `HIGHLIGHT` | 답 문장마다 평가 기준 표시 (형광펜) | `coach.build_highlight` → `app.get_highlight` | 번호 붙인 문장 + 질문 · 보는 점 | `HIGHLIGHT_SCHEMA` | 사용 중 (사용자가 누를 때만) | Claude 초안 | **원문 포함** |
| P-05 | `STRATEGY` | 약한 기준을 올리는 전략 가이드 | `coach.build_strategy` → `app.show_strategy` | 지원자 답 | `STRATEGY_SCHEMA` | 사용 중 (사용자가 누를 때만) | Claude 초안 | **원문 포함** |
| P-06 | `INTERVIEWER_FEEDBACK` (+ `FEEDBACK_STAGES`) | 꼬리 질문 뒤 강점 · 보완점 피드백형 면접관 | `coach.build_interviewer` (style `"feedback"` 일 때) | 대화 기록 | `INTERVIEWER_SCHEMA` | 도달 불가 — `feedback` 방식 면접관(프로덕트 디자인 리드)을 검토 끝에 필요 없다고 판단해 11-02 MVP1 에서 삭제 (사용자 결정) | Claude 초안 (사용자가 준 '면접 진행 방식' 1~5 를 옮김) | 원문 제외 · 개선 과정(04장)에 이력만 |
| P-07 | `LAST_QUESTION` | 지원자의 마지막 질문 다듬기 | `coach.build_last_question` (화면 호출 없음) | 지원자 원래 질문 | `LAST_QUESTION_SCHEMA` | 코드만 있음 — MVP1 화면에서 뺌 (`prd/MIGRATION.md`: 유지 여부 결정 필요) | 확인 불가 | 원문 제외 · 미구현 목록(06장)에 |
| P-08 | `LAST_SUGGEST` (+ `LAST_SUGGEST_INPUT`) | 마지막 질문 추천 | `coach.build_last_suggest` (화면 호출 없음) | 고정 한 줄 "추천 질문 3개를 만들어 줘." | `LAST_SUGGEST_SCHEMA` | 코드만 있음 — 위와 같음 | Claude 초안 | 원문 제외 · 미구현 목록(06장)에 |

## 2. 프롬프트에 끼워 넣는 구성 데이터

| ID | 이름 | 들어가는 자리 | 내용 | 상태 | 작성자 | 제출 문서 |
|---|---|---|---|---|---|---|
| D-01 | `CONTEXT` | 모든 지시문의 `{context}` | 회사 · 회사 설명 · 분야 · 직군 · 지원자 경험. 평가 · 재도전 채점에는 경험 대신 "(평가에는 쓰지 않음)" (`coach.build_context(with_experience=False)`) | 사용 중 | 확인 불가 | **원문 포함** |
| D-02 | `PERSONAS` | `{persona}` (면접관 · 재도전) | 직군 4개의 면접관 글 | 사용 중 | 디자인: 사용자 · 개발 / PO / 마케팅: Claude 초안 (11-02) | 디자인 원문 포함 · 나머지 3개는 초안으로 표시하고 한 줄 요약 |
| D-03 | `PERSONA_TYPES` | 면접관 글 · 진행 방식 고르기 | 디자인: "디자인 팀장"(probe) 1명 | 사용 중 | — (구성) | 설명만 |
| D-04 | `FIELDS` | `{field_desc}` | 산업 분야 9개 설명 | 사용 중 | Claude 초안 | 표로 요약 |
| D-05 | `PANEL_CRITERIA` (+ `PANEL_ROLES`) | `EVALUATOR` 의 `{panel_criteria}` · 화면 · 리포트 | 위원 4명의 평가 기준 (근거: `data/평가기준_근거.md`) | 사용 중 | 확인 불가 | **원문 포함** |
| D-06 | `data/questions.csv` 의 '질문' · '보는 점' 칸 | `{question}` `{point}`, 평가 입력의 `[보는 점]` | 질문 193개 (공통 4 · 디자인 75 · 개발 38 · PO 38 · 마케팅 38) | 사용 중 | 질문 은행 (산업 분야 90문항은 11-03 새벽 사용자 승인 후 반영) | 구조만 설명 · 질문 전문은 제외 |
| D-07 | 대화 · 기록 서식 (`coach.format_transcript` · `format_record` · `build_highlight_input`) | user_input | `[질문 n · 유형]` · `[보는 점]` · `[면접관]` · `[지원자]` 줄 서식 | 사용 중 | — (코드) | 서식만 설명 |

## 3. 응답 스키마 (`prompts.py`)

| ID | 이름 | 쓰는 곳 | 제출 문서 |
|---|---|---|---|
| S-01 | `INTERVIEWER_SCHEMA` | P-01 · P-06 | 칸 목록으로 요약 |
| S-02 | `EVAL_SCHEMA` | P-02 | 칸 목록으로 요약 |
| S-03 | `RETRY_SCHEMA` | P-03 | 칸 목록으로 요약 |
| S-04 | `HIGHLIGHT_SCHEMA` | P-04 | 칸 목록으로 요약 |
| S-05 | `STRATEGY_SCHEMA` | P-05 | 칸 목록으로 요약 |
| S-06 | `LAST_QUESTION_SCHEMA` · `LAST_SUGGEST_SCHEMA` | P-07 · P-08 | 제외 (화면 미사용) |

JSON 스키마 전문은 코드 그대로 길어서 싣지 않고 칸 이름 · 타입만 정리했다 (원본: `d10-interview/prompts.py`).

## 4. AI 에 들어가지 않는 화면 표시용 데이터

| 이름 | 용도 | 제출 문서 |
|---|---|---|
| `PERSONA_CARDS` | 면접 설정 화면의 '면접관 자세히 보기' 카드 (사용자가 쓴 문장) | 제외 — AI 지시문이 아님 (01장에서 한 줄 언급) |
| `PERSONA_TAGS` | 면접관 옆 정보 태그 ("빠른 면접 진행") | 제외 — AI 지시문이 아님 |
| `tests/fixtures/ai/*.json` | 테스트 · 시연용 가짜 AI 응답 | 제외 — 프롬프트가 아님 (05장 테스트 설명에서 언급) |

## 5. 프로젝트 지침 · 기획 문서 (AI 기능 프롬프트와 구분)

| 파일 | 성격 | 제출 문서 |
|---|---|---|
| `d10-interview/CLAUDE.md` | Claude Code 작업 지침 (교육 과정에서 제공된 파일 · 수정 금지). 파일 구조 · 프롬프트 규칙 · "AI는 판단, 코드는 계산" · 보안 | 05장에 **AI 기능 프롬프트와 구분해** 요약 |
| `prd/technical/AI_RULES.md` | 1차 MVP AI 평가 명세 (면접관 · 평가 · 응답 검증 · 재도전 · 비용 통제) | 02장 제약 조건의 근거로 인용 |
| `prd/MIGRATION.md` | 목표 정책과 현재 코드의 차이 | 04 · 06장 근거로 인용 |
| `data/평가기준_근거.md` | 위원 4명 평가 기준의 출처 (구조화 면접 · NCS 등) | 02장에서 언급 |
| `tests/manual_checklist.md` §11 | 실제 AI 응답 품질 점검 항목 A-1 ~ A-6 | 05장에서 언급 (점검 결과 기록은 없음) |
| `prd/PRD.md` · `IA_UserFlow.md` · `README.md` · `design.md` · `features/*` · `DATA_MODEL.md` | 서비스 기획 · 화면 · 데이터 문서 | 제외 — 프롬프트 관련 내용은 위 문서에 이미 반영 |

## 6. Claude Code 개발 지시 프롬프트 (사용자 → Claude Code)

출처: Claude Code 대화 기록 6개 세션. 2개는 중복 세션(같은 메시지 반복 · IDE 선택 1건)이라 실제 작업 세션은 4개.

| 기간 (KST) | 세션 | 주요 지시 | 제출 문서 |
|---|---|---|---|
| 10-29 | 환경 설정 (중복 세션 포함) | camp 가상환경 · Streamlit 실행 문의 | 제외 — 개발 지시 아님 |
| 10-29 | UI 컨셉 | 게임형 시작 화면 · 스플래시 · 로고 · 다크 모드 · 디자인 면접관 문구 직접 작성 · 면접관 2종 전환 | 05장 요약 (면접관 문구 작성은 04장) |
| 10-30 | GitHub | 저장소 연결 · README · 변경 전/후 비교 | 05장 요약 |
| 11-01 ~ 11-04 | 메인 개발 | 브랜치 전략 · MVP 범위(C안) · P0 기준 테스트 · PRD v2.3 · 오류 관리 E-1~E-5 · MVP1 구현 · 꼬리 질문 프롬프트 개선 · 산업 분야 90문항 · 평가 지시문 보완 · 복원 수정 · 배포 · 시연 영상 | 05장 요약 · 프롬프트 관련 지시는 04장에 원문 인용 |

프롬프트에 직접 관련된 사용자 지시 (원문 인용 · 04장에 수록)
- 2026-11-03 03:14 (KST) "면접관 프롬프트 개선 (A 승인)" — `INTERVIEWER` 규칙 보강
- 2026-11-03 04:11 (KST) "4인 평가 지시문 개선 승인" — `EVALUATOR` 에 [보는 점] 문장 추가
- 2026-11-02 15:42 ~ 21:46 (KST) 반복 제약 — "`prompts.py` 수정 금지" → 11-02 22:33 "prompts.py 수정은 사용자 승인 필요"

## 7. 원본 확인이 불가능한 항목

| 항목 | 이유 | 문서 표기 |
|---|---|---|
| 10-27 ~ 10-28 첫 작성 대화 (`INTERVIEWER` · `EVALUATOR` · `RETRY` · `HIGHLIGHT` · `STRATEGY` · `LAST_*` 첫 버전) | 이 기간 Claude Code 대화 기록이 남아 있지 않음. Git 커밋으로 문장만 확인 | "작성 대화 확인 불가 · Git 이력으로 문장 확인" |
| 위 프롬프트들의 작성 이유 · 비교 실험 | 기록 없음 | "확인 불가" |
| 꼬리 질문 개선 뒤 실제 API 결과 | 11-03 03:25 (KST) 실제 API 모드로 서버를 열고 사용자가 디자인 5문항을 직접 입력해 확인하기로 했지만, 그 결과는 대화 기록 · 파일에 남아 있지 않음 (응답 원문은 저장하지 않는 규칙) | "정량 결과 확인 불가" |
| `manual_checklist.md` §11 실제 AI 품질 점검 결과 | 점검 항목만 있고 결과 기록이 없음 | "점검 결과 기록 없음" |
| 11-02 18:13 (KST) 실제 API 사전 테스트(승인 3회) 결과 | 결과는 화면에만 출력하고 파일로 저장하지 않음 | "확인 불가" |

## 8. 민감정보 점검

- API 키 · 토큰 · 이메일: 제출 문서에 없음. 대화 기록의 사용자 메시지에도 키가 없음.
- 개인 면접 답변: 싣지 않음. 대화 기록의 답변 요약 1건은 생략.
- 질문 은행 질문 · 지원자 경험 예시: 프롬프트 원문의 변수(`{experience}` 등)로만 표시.
