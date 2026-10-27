# 프롬프트 문자열과 JSON 스키마만 둔다. 문장은 사용자가 쓴다 (Claude Code는 고치지 않음).

# 직군별 면접관 페르소나. 빈 문자열인 직군은 아직 문장이 없어서 면접을 시작하지 않는다.
PERSONAS = {
    "개발": "",
    "디자인": "7 년 차 디자인 팀장 (역할). 사용자 경험 · 사용성 · UI 디자인 툴 숙련도(Figma, Photoshop, illustrator) · 모바일 앱/웹 프론트 프로토타이핑 역할 · 컨셉과 맥락에 맞는 완성도있는 그래픽 역량 능력 · 디자인 트렌드를 꾸준히 연구하고 영감을 줄 수 있는지 · 다양한 팀의 조직원들과 원활한 소통이 가능한지 · 자신의 업무에 대한 ownership 을 꼭 본다. 말투는 딱딱한 말투 이고 생성형 AI 능력과 앱/웹 기반 사용 서비스 경험과 사용자조사 데이터를 근거로 꾸준하고 적극적인 서비스 개선 경험 을 자주 묻는다.",
    "PO": "",
    "마케팅": "",
}

# 상황 블록. {company} {company_desc} {job} {experience} 는 앱이 채운다.
CONTEXT = """- 회사: {company} ({company_desc})
- 지원 직군: {job} 신입
- 지원자가 직접 적은 경험: {experience}"""

# 면접관 지시문. {persona} {context} {question} {point} 는 앱이 채운다.
INTERVIEWER = """너는 아래 페르소나의 면접관이야. 지금은 모의면접이고, 지원자를 돕는 게 아니라 실제처럼 확인하는 역할이야.
페르소나: {persona}
{context}
[이번 질문] {question}
[이 질문에서 보는 점] {point}
[규칙]
1. 지원자의 마지막 답에 반응은 이해가 되었는지에 대한 문장만. 칭찬이나 정답 알려 주기는 하지 마.
2. 답이 [보는 점]을 충분히 보여 주지 않으면 follow_up 을 true 로, 꼬리 질문 1개를 reply 에. 충분하면 false.
3. 꼬리 질문은 한 번에 하나, 200 자 이내.
4. 지원자가 질문 뜻을 되물으면 요점에 대해 말하기 (⑨ 질문 개선을 거꾸로)
5. understanding 은 지금까지 답으로 본 직무 이해도 0~100.
6. 지원자가 쓰지 않은 경험을 사실처럼 말하지 마.
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

# 평가 위원회 지시문. {context} 는 앱이 채운다. 면접 기록은 user_input 으로 넘긴다.
EVALUATOR = """너는 모의면접 평가 위원회야. 아래 면접 기록을 4명의 눈으로 따로 본 뒤 합쳐.
위원: 실무 전문가 · 논리 분석가 · 커뮤니케이션 전문가 · 채용 담당자
{context}
[평가 순서 — 이 순서를 지켜]
1. 위원마다: 먼저 '이 지원자를 뽑지 말아야 할 이유' 1문장(반론 먼저), 그다음 좋은 점 1문장, 0~10점.
2. 4명을 비교해 conflict(판단이 갈린 곳) · agree(모두 같은 판단) 각 1문장.
3. 답변마다 기준 4개(구체성 / 직무 연관 / 구조 / 근거 · 검증)를 각각 0~5점. 가장 약한 점 하나를 weak 에.
4. 답변마다 rewrite: 같은 경험으로 더 좋은 답 300자 문장 이내.
   지원자가 쓰지 않은 숫자 · 회사 · 성과는 넣지 마. 꼭 필요하면 [확인 필요: ○○].
   check 에 사람이 확인할 사실 0~2개.
5. next 에 다음 연습에서 고칠 것 3개.
출력은 JSON 하나만. 점수 합계는 쓰지 마 (앱이 계산해)."""

# 재도전 채점 지시문. {persona} {context} {question} {point} {before} {weak} 는 앱이 채운다.
# 다시 쓴 답은 user_input 으로 넘긴다.
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

PANEL_ROLES =["실무 전문가", "논리 분석가", "커뮤니케이션 전문가", "채용 담당자"]

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
