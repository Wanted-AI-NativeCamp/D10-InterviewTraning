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

# 마지막 질문 다듬기 지시문. {context} 는 앱이 채운다. 지원자의 원래 질문은 user_input 으로 넘긴다.
# '___' 이 남아 있으면 앱은 이 기능을 쓰지 않고 안내만 보여 준다.
LAST_QUESTION = """지원자가 면접 마지막에 면접관에게 할 질문을 더 좋은 질문으로 고쳐 줘.
{context}
- 고친 질문 3개: 회사 · 직무 · 성장 관점 하나씩, 각 300 자 이내
- 원래 질문에서 빠진 것(대상 · 목적 · 구체성)을 why 에 1문장
- 회사에 대해 확인되지 않은 사실을 전제로 하지 마
출력은 JSON 하나만: questions(목록), why(글)"""

LAST_QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {"type": "array", "items": {"type": "string"}},
        "why": {"type": "string"},
    },
    "required": ["questions", "why"],
    "additionalProperties": False,
}

# 마지막 질문 추천 지시문. {context} 는 앱이 채운다. (Claude Code 초안 — 사용자 확인 필요)
LAST_SUGGEST = """지원자가 면접 마지막 "마지막으로 할 질문 있나요?" 에 할 질문을 추천해 줘.
{context}
- 추천 질문 3개: 회사 · 직무 · 성장 관점 하나씩, 각 300 자 이내
- 지원 직군과 지원자가 적은 경험에 맞춘 질문으로
- 회사에 대해 확인되지 않은 사실을 전제로 하지 마
출력은 JSON 하나만: questions(목록)"""
LAST_SUGGEST_INPUT = "추천 질문 3개를 만들어 줘."  # 추천은 입력할 글이 없어서 이 한 줄을 user_input 으로 넘긴다

LAST_SUGGEST_SCHEMA = {
    "type": "object",
    "properties": {"questions": {"type": "array", "items": {"type": "string"}}},
    "required": ["questions"],
    "additionalProperties": False,
}

# 형광펜 지시문. {context} 는 앱이 채운다. 번호 붙은 문장은 user_input 으로 넘긴다.
# (Claude Code 초안 — 사용자 확인 필요)
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

# 점수 전략 가이드 지시문. 칸은 앱이 채운다. (Claude Code 초안 — 사용자 확인 필요)
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

# 위원별 평가 기준. EVALUATOR 의 {panel_criteria} 와 화면 · 리포트가 같이 쓴다.
# 근거는 data/평가기준_근거.md
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
