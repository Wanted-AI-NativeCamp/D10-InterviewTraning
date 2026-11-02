# 오류 기록 한 곳 (E-1). CLAUDE.md 파일 구조의 승인된 예외(C2) — 근거는 prd/technical/AI_RULES.md · DATA_MODEL.md.
# 정상 면접 · 평가 데이터(session_state · Markdown)와 분리해, 표준 logging 으로 JSON 한 줄씩 남긴다.
#   - 항상 stderr · ERROR_LOG_FILE_ENABLED=true 일 때만 logs/errors.jsonl (5MB × 백업 3개)
#   - 허용된 칸 · 값만 기록한다: 사용자 답변 · 개인정보 · API 키 · 토큰 · AI 응답 원문 · 예외 메시지는 받지 않는다
#   - 기록이 실패해도 예외를 밖으로 내보내지 않는다 (면접 진행 · 데이터 저장을 막지 않는다)
import json
import logging
import logging.handlers
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOGGER_NAME = "yeokjeon.errors"
LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE_NAME = "errors.jsonl"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3
FILE_ENV = "ERROR_LOG_FILE_ENABLED"
TRUE_VALUES = {"true", "1", "yes", "on"}

# D9 오류 코드
ERROR_TYPES = {
    "eval_validation",
    "api_connection", "api_timeout", "api_auth", "api_quota", "api_rate_limit", "api_server", "api_other",
    "response_parse",
    "markdown_build", "markdown_parse", "restore_parse", "restore_validation",
}
# 오류가 난 기능 (ask_json 의 name · 저장 · 복원)
SOURCES = {
    "interviewer", "evaluation", "retry", "highlight", "strategy", "last_question", "last_suggest",
    "report_download", "next_round", "restore",
}
STATUSES = {"retrying", "recovered", "failed"}  # 재시도 예정 · 재시도로 복구 · 최종 실패
MAX_ATTEMPT = 9

# meta 는 이 칸만, 이 모양만 받는다. 글 칸은 식별자 모양(영문 · 숫자 · . _ : -)만이라 답변 · 이름 같은 글이 들어갈 수 없다.
IDENT = re.compile(r"^[A-Za-z0-9._:\-]{1,64}$")
META_FIELDS = {
    "model": "ident", "exception": "ident", "round_id": "ident", "question_id": "ident",
    "criteria_version": "ident", "http_status": "int", "question_no": "int", "file_version": "int", "item_count": "int",
}
# 검증 세부 코드: 'snake_case' 또는 'snake_case:경로' (경로는 영문 · 숫자 · [ ] . _ = - 만, 예: score_out_of_range:answers[3].specific=7)
CODE = re.compile(r"^[a-z][a-z0-9_]{0,39}(:[A-Za-z0-9_.\[\]=\-]{1,48})?$")
MAX_CODES = 20
# 승인된 세부 코드: 이름이 정확히 같을 때만 아래 비밀값 검사(SECRET)를 거치지 않는다 (codes 칸에만 적용)
APPROVED_CODES = {"missing_api_key", "json_decode"}
# 식별자 모양이어도 비밀값처럼 보이면 버린다
SECRET = re.compile(r"(sk-[A-Za-z0-9_\-]{6,}|bearer|^eyJ[A-Za-z0-9_\-]{10,}|api[_-]?key|token|secret|password)", re.IGNORECASE)
SESSION = re.compile(r"^[A-Za-z0-9\-]{8,64}$")


class _QuietStreamHandler(logging.StreamHandler):
    """쓰기 실패 시 traceback 을 찍지 않고 넘어간다 (handleError 기본 동작 대신)."""

    def handleError(self, record):
        pass


class _QuietRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def handleError(self, record):
        pass


def file_enabled_from_env() -> bool:
    return str(os.getenv(FILE_ENV, "false")).strip().lower() in TRUE_VALUES


def configure(*, file_enabled: bool | None = None, log_dir: Path | str | None = None, stream=None,
              force: bool = False) -> logging.Logger:
    """로거를 한 번만 설정한다 (Streamlit 재실행마다 핸들러가 늘지 않게). force=True 는 테스트 · 설정 변경용.
    파일 폴더를 만들 수 없으면 파일 기록 없이 stderr 만 쓴다. 어떤 경우에도 예외를 내지 않는다."""
    logger = logging.getLogger(LOGGER_NAME)
    try:
        if getattr(logger, "_yeokjeon_configured", False) and not force:
            return logger
        for h in list(logger.handlers):
            logger.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass
        logger.setLevel(logging.WARNING)
        logger.propagate = False  # 다른 로그 설정(Streamlit 등)으로 퍼지지 않게
        formatter = logging.Formatter("%(message)s")
        out = _QuietStreamHandler(stream if stream is not None else sys.stderr)
        out.setFormatter(formatter)
        logger.addHandler(out)
        if file_enabled if file_enabled is not None else file_enabled_from_env():
            try:
                folder = Path(log_dir) if log_dir is not None else LOG_DIR
                folder.mkdir(parents=True, exist_ok=True)
                fh = _QuietRotatingFileHandler(folder / LOG_FILE_NAME, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT,
                                               encoding="utf-8", delay=True)
                fh.setFormatter(formatter)
                logger.addHandler(fh)
            except Exception:
                pass  # 파일 기록을 못 해도 stderr 기록은 계속한다
        logger._yeokjeon_configured = True
    except Exception:
        pass
    return logger


def new_session_id() -> str:
    """개인정보와 무관한 임의 세션 표시 (화면 세션마다 하나)."""
    return uuid.uuid4().hex


def _clean_meta(meta) -> tuple[dict, int]:
    clean, dropped = {}, 0
    for key, value in (meta or {}).items() if isinstance(meta, dict) else []:
        kind = META_FIELDS.get(key)
        if kind == "int" and isinstance(value, int) and not isinstance(value, bool) and -1_000_000 < value < 1_000_000:
            clean[key] = value
        elif kind == "ident" and isinstance(value, str) and IDENT.match(value) and not SECRET.search(value):
            clean[key] = value
        else:
            dropped += 1
    if meta is not None and not isinstance(meta, dict):
        dropped += 1
    return clean, dropped


def _clean_codes(codes) -> tuple[list, int]:
    clean, dropped = [], 0
    items = list(codes) if isinstance(codes, (list, tuple)) else ([] if codes is None else [codes])
    for c in items:
        allowed = isinstance(c, str) and (c in APPROVED_CODES or (CODE.match(c) and not SECRET.search(c)))
        if allowed and len(clean) < MAX_CODES:
            clean.append(c)
        else:
            dropped += 1
    return clean, dropped


def build_event(error_type: str, source: str, *, session_id: str, attempt: int = 1, status: str = "failed",
                codes=None, meta=None) -> dict | None:
    """기록할 한 줄. 필수 칸(유형 · 기능 · 상태 · 시도 번호)이 정해진 값이 아니면 None (기록하지 않음).
    허용되지 않은 세부 코드 · meta 는 버리고 버린 개수만 dropped 에 남긴다."""
    if error_type not in ERROR_TYPES or source not in SOURCES or status not in STATUSES:
        return None
    if not (isinstance(attempt, int) and not isinstance(attempt, bool) and 1 <= attempt <= MAX_ATTEMPT):
        return None
    clean_codes, dropped_codes = _clean_codes(codes)
    clean_meta, dropped_meta = _clean_meta(meta)
    return {
        "error_id": uuid.uuid4().hex,
        "session_id": session_id if isinstance(session_id, str) and SESSION.match(session_id) else "unknown",
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "error_type": error_type,
        "source": source,
        "attempt": attempt,
        "status": status,
        "codes": clean_codes,
        "meta": clean_meta,
        "dropped": dropped_codes + dropped_meta,
    }


def record_error(error_type: str, source: str, *, session_id: str, attempt: int = 1, status: str = "failed",
                 codes=None, meta=None) -> str | None:
    """오류 한 건을 기록하고 error_id 를 돌려준다. 필수 칸이 맞지 않거나 기록에 실패하면 None.
    어떤 경우에도 예외를 내지 않는다 — 부르는 쪽은 정상 데이터를 먼저 저장하고, 이 결과로 흐름을 바꾸지 않는다."""
    try:
        event = build_event(error_type, source, session_id=session_id, attempt=attempt, status=status,
                            codes=codes, meta=meta)
        if event is None:
            return None
        logger = configure()
        level = logging.ERROR if status == "failed" else logging.WARNING
        record = logger.makeRecord(LOGGER_NAME, level, __file__, 0,
                                   json.dumps(event, ensure_ascii=False, separators=(",", ":")), None, None)
        # 핸들러마다 따로 보호한다: 한 곳(예: 파일)이 실패해도 다른 곳(stderr) 기록은 계속된다
        for handler in list(logger.handlers):
            try:
                if record.levelno >= handler.level:
                    handler.handle(record)
            except Exception:
                pass
        return event["error_id"]
    except Exception:
        return None
