# 오류 기록 모듈 테스트 (E-1). 외부 API · 프로젝트 logs/ 를 쓰지 않는다 — 파일은 임시 폴더에서만 만든다.
# 실행: d10-interview 폴더에서  python -m unittest discover tests
import io
import json
import logging
import logging.handlers
import os
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import error_log

SESSION = error_log.new_session_id()
FIELDS = {"error_id", "session_id", "timestamp", "error_type", "source", "attempt", "status", "codes", "meta", "dropped"}


class LogCase(unittest.TestCase):
    """테스트마다 stderr 대신 메모리 버퍼로 기록하고, 끝나면 기본 설정(파일 꺼짐 · stderr)으로 되돌린다."""

    def setUp(self):
        self.buffer = io.StringIO()
        self.tmp = tempfile.TemporaryDirectory()
        error_log.configure(force=True, file_enabled=False, stream=self.buffer)

    def tearDown(self):
        error_log.configure(force=True, file_enabled=False)  # 파일 핸들러를 닫아 임시 폴더를 지울 수 있게
        self.tmp.cleanup()

    def lines(self) -> list[dict]:
        return [json.loads(line) for line in self.buffer.getvalue().splitlines() if line.strip()]

    def handlers(self):
        return logging.getLogger(error_log.LOGGER_NAME).handlers


class StructureTest(LogCase):

    def test_fields_and_values(self):
        eid = error_log.record_error("eval_validation", "evaluation", session_id=SESSION, attempt=1, status="retrying",
                                     codes=["panel_missing:panel[2]", "score_out_of_range:answers[3].specific=7"],
                                     meta={"model": "gpt-6-luna", "question_no": 3})
        [event] = self.lines()
        self.assertEqual(set(event), FIELDS)
        self.assertEqual(event["error_id"], eid)
        self.assertRegex(eid, r"^[0-9a-f]{32}$")
        self.assertEqual(event["session_id"], SESSION)
        self.assertTrue(event["timestamp"].endswith("Z"))
        datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))  # 파싱되는 UTC 시각
        self.assertEqual((event["error_type"], event["source"], event["attempt"], event["status"]),
                         ("eval_validation", "evaluation", 1, "retrying"))
        self.assertEqual(event["codes"], ["panel_missing:panel[2]", "score_out_of_range:answers[3].specific=7"])
        self.assertEqual(event["meta"], {"model": "gpt-6-luna", "question_no": 3})
        self.assertEqual(event["dropped"], 0)

    def test_one_json_object_per_line(self):
        for status in ("retrying", "recovered", "failed"):
            error_log.record_error("api_timeout", "interviewer", session_id=SESSION, status=status)
        raw = self.buffer.getvalue().splitlines()
        self.assertEqual(len(raw), 3)
        self.assertEqual([json.loads(r)["status"] for r in raw], ["retrying", "recovered", "failed"])

    def test_all_d9_codes_accepted(self):
        for t in sorted(error_log.ERROR_TYPES):
            with self.subTest(error_type=t):
                self.assertIsNotNone(error_log.record_error(t, "restore", session_id=SESSION))
        self.assertEqual(len(error_log.ERROR_TYPES), 13)

    def test_bad_session_id_replaced(self):
        error_log.record_error("api_other", "strategy", session_id="김예시 세션")
        self.assertEqual(self.lines()[0]["session_id"], "unknown")


class SensitiveDataTest(LogCase):
    ANSWER = "저는 김예시입니다. 예약 앱의 결제 단계를 5개에서 3개로 줄였습니다."
    SECRETS = ["sk-proj-abcdefghijklmnop1234", "Bearer abc.def.ghi", "eyJhbGciOiJIUzI1NiJ9abcdef", "api_key=xyz",
               "user@example.com", "my_token_123"]

    def test_free_text_and_secrets_never_written(self):
        meta = {"model": self.ANSWER, "exception": self.SECRETS[0], "round_id": self.SECRETS[2],
                "question_id": "user@example.com", "criteria_version": "my_token_123", "http_status": 500}
        codes = [self.ANSWER, "invalid_answer:" + self.SECRETS[0], "x:Bearer abc", "api_key:abc", "ok_code"]
        error_log.record_error("api_server", "evaluation", session_id=SESSION, codes=codes, meta=meta)
        text = self.buffer.getvalue()
        for s in [self.ANSWER, "김예시", *self.SECRETS, "sk-proj"]:
            self.assertNotIn(s, text)
        [event] = self.lines()
        self.assertEqual(event["meta"], {"http_status": 500})
        self.assertEqual(event["codes"], ["ok_code"])
        self.assertEqual(event["dropped"], 9)

    def test_unknown_meta_fields_dropped(self):
        meta = {"answer": "답", "reply": "응답 원문", "prompt": "요청", "api_key": "x", "name": "김예시", "company": "토스"}
        error_log.record_error("response_parse", "interviewer", session_id=SESSION, meta=meta)
        [event] = self.lines()
        self.assertEqual((event["meta"], event["dropped"]), ({}, 6))
        for s in ("응답 원문", "김예시", "토스", "요청"):
            self.assertNotIn(s, self.buffer.getvalue())

    def test_wrong_value_types_dropped(self):
        meta = {"http_status": "500", "question_no": True, "item_count": 10**9, "model": 123}
        error_log.record_error("api_other", "retry", session_id=SESSION, meta=meta, codes="not_a_list_but_ok")
        [event] = self.lines()
        self.assertEqual(event["meta"], {})
        self.assertEqual(event["codes"], ["not_a_list_but_ok"])
        self.assertEqual(event["dropped"], 4)

    def test_codes_capped(self):
        error_log.record_error("eval_validation", "evaluation", session_id=SESSION,
                               codes=[f"code_{i}" for i in range(25)])
        [event] = self.lines()
        self.assertEqual((len(event["codes"]), event["dropped"]), (error_log.MAX_CODES, 5))


class ApprovedCodeTest(LogCase):
    """승인된 세부 코드(missing_api_key · json_decode)는 이름이 정확히 같을 때만 기록. 다른 차단 규칙은 그대로."""

    def test_approved_codes_recorded(self):
        error_log.record_error("api_auth", "interviewer", session_id=SESSION, codes=["missing_api_key"])
        error_log.record_error("response_parse", "evaluation", session_id=SESSION, codes=["json_decode"])
        first, second = self.lines()
        self.assertEqual((first["codes"], first["dropped"]), (["missing_api_key"], 0))
        self.assertEqual((second["codes"], second["dropped"]), (["json_decode"], 0))

    def test_only_exact_names_pass(self):
        codes = ["missing_api_key:sk-proj-abcdefghijkl", "missing_api_key_2", "api_key", "my_api_key",
                 "missing_token", "x:Bearer abc", "MISSING_API_KEY", " missing_api_key", "missing_api_key"]
        error_log.record_error("api_auth", "interviewer", session_id=SESSION, codes=codes)
        [event] = self.lines()
        self.assertEqual(event["codes"], ["missing_api_key"])
        self.assertEqual(event["dropped"], len(codes) - 1)
        self.assertNotIn("sk-proj", self.buffer.getvalue())

    def test_meta_rules_unchanged(self):
        """승인 코드와 같은 글자라도 meta 칸에서는 기존 비밀값 검사를 그대로 받는다."""
        meta = {"model": "missing_api_key", "exception": "json_decode", "round_id": "api_key",
                "question_id": "sk-proj-abcdefghijkl"}
        error_log.record_error("api_other", "retry", session_id=SESSION, meta=meta)
        [event] = self.lines()
        self.assertEqual(event["meta"], {"exception": "json_decode"})  # json_decode 는 원래 비밀값 패턴이 아님
        self.assertEqual(event["dropped"], 3)


class RejectedEventTest(LogCase):
    """필수 칸이 정해진 값이 아니면 기록하지 않고 None (예외 없음)."""

    def test_rejected(self):
        cases = [
            dict(error_type="eval_range", source="evaluation"),        # D9 에 없는 유형
            dict(error_type="api_auth", source="unknown_feature"),     # 없는 기능
            dict(error_type="api_auth", source="evaluation", status="done"),
            dict(error_type="api_auth", source="evaluation", attempt=0),
            dict(error_type="api_auth", source="evaluation", attempt=10),
            dict(error_type="api_auth", source="evaluation", attempt="1"),
            dict(error_type="api_auth", source="evaluation", attempt=True),
        ]
        for c in cases:
            with self.subTest(c=c):
                kw = {k: v for k, v in c.items() if k not in ("error_type", "source")}
                self.assertIsNone(error_log.record_error(c["error_type"], c["source"], session_id=SESSION, **kw))
        self.assertEqual(self.buffer.getvalue(), "")


class FileOutputTest(LogCase):

    def test_default_is_stderr_only(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(error_log.FILE_ENV, None)
            self.assertFalse(error_log.file_enabled_from_env())
            error_log.configure(force=True)
            self.assertEqual([type(h).__name__ for h in self.handlers()], ["_QuietStreamHandler"])
        for value, expected in (("false", False), ("0", False), ("", False), ("true", True), ("TRUE", True), ("1", True)):
            with self.subTest(value=value), mock.patch.dict(os.environ, {error_log.FILE_ENV: value}):
                self.assertEqual(error_log.file_enabled_from_env(), expected)

    def test_rotation_settings_and_jsonl(self):
        error_log.configure(force=True, file_enabled=True, log_dir=self.tmp.name, stream=self.buffer)
        files = [h for h in self.handlers() if isinstance(h, logging.handlers.RotatingFileHandler)]
        self.assertEqual(len(files), 1)
        fh = files[0]
        self.assertEqual((fh.maxBytes, fh.backupCount), (5 * 1024 * 1024, 3))
        self.assertEqual(Path(fh.baseFilename), Path(self.tmp.name) / "errors.jsonl")
        error_log.record_error("markdown_build", "report_download", session_id=SESSION, meta={"exception": "KeyError"})
        error_log.record_error("restore_parse", "restore", session_id=SESSION)
        fh.flush()
        rows = [json.loads(l) for l in (Path(self.tmp.name) / "errors.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["error_type"] for r in rows], ["markdown_build", "restore_parse"])
        self.assertEqual(len(self.lines()), 2)  # stderr 쪽에도 같은 기록

    def test_rotation_actually_rolls(self):
        error_log.configure(force=True, file_enabled=True, log_dir=self.tmp.name, stream=self.buffer)
        fh = [h for h in self.handlers() if isinstance(h, logging.handlers.RotatingFileHandler)][0]
        fh.maxBytes = 400  # 순환 동작만 확인 (설정값은 위 테스트에서 5MB 확인)
        for _ in range(20):
            error_log.record_error("api_server", "evaluation", session_id=SESSION)
        names = sorted(p.name for p in Path(self.tmp.name).iterdir())
        self.assertEqual(names, ["errors.jsonl", "errors.jsonl.1", "errors.jsonl.2", "errors.jsonl.3"])

    def test_unwritable_dir_falls_back_to_stderr(self):
        blocker = Path(self.tmp.name) / "not_a_dir"
        blocker.write_text("x", encoding="utf-8")
        error_log.configure(force=True, file_enabled=True, log_dir=blocker / "logs", stream=self.buffer)
        self.assertEqual(len(self.handlers()), 1)
        self.assertIsNotNone(error_log.record_error("api_other", "highlight", session_id=SESSION))
        self.assertEqual(len(self.lines()), 1)

    def test_project_logs_folder_untouched(self):
        before = error_log.LOG_DIR.exists()
        error_log.record_error("api_other", "highlight", session_id=SESSION)
        self.assertEqual(error_log.LOG_DIR.exists(), before)


class FailureSafetyTest(LogCase):

    def test_handler_failure_does_not_raise(self):
        class Broken(logging.Handler):
            def emit(self, record):
                raise OSError("disk full")

        logger = logging.getLogger(error_log.LOGGER_NAME)
        logger.handlers.insert(0, Broken())  # 실패하는 핸들러가 먼저 불려도
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            eid = error_log.record_error("api_connection", "interviewer", session_id=SESSION)
        self.assertIsNotNone(eid)
        self.assertEqual(len(self.lines()), 1)  # 뒤의 핸들러(버퍼)에는 그대로 기록됨
        self.assertEqual(stderr.getvalue(), "")  # traceback 도 찍지 않음

    def test_broken_stream_does_not_raise(self):
        class BrokenStream(io.StringIO):
            def write(self, s):
                raise OSError("closed")

        error_log.configure(force=True, file_enabled=False, stream=BrokenStream())
        error_log.record_error("api_connection", "interviewer", session_id=SESSION)  # 예외가 나면 테스트 실패

    def test_internal_error_returns_none(self):
        with mock.patch.object(error_log, "configure", side_effect=RuntimeError("boom")):
            self.assertIsNone(error_log.record_error("api_other", "retry", session_id=SESSION))

    def test_unserializable_input_returns_none_or_drops(self):
        self.assertIsNotNone(error_log.record_error("api_other", "retry", session_id=SESSION,
                                                    meta={"model": object()}, codes=[object()]))
        [event] = self.lines()
        self.assertEqual((event["meta"], event["codes"], event["dropped"]), ({}, [], 2))


class DuplicateSetupTest(LogCase):

    def test_configure_is_idempotent(self):
        error_log.configure(force=True, file_enabled=True, log_dir=self.tmp.name, stream=self.buffer)
        count = len(self.handlers())
        for _ in range(5):  # Streamlit 재실행처럼 여러 번 불러도
            error_log.configure()
            error_log.record_error("api_other", "strategy", session_id=SESSION)
        self.assertEqual(len(self.handlers()), count)
        self.assertEqual(len(self.lines()), 5)  # 한 번에 한 줄 (중복 출력 없음)

    def test_not_propagated_to_root(self):
        self.assertFalse(logging.getLogger(error_log.LOGGER_NAME).propagate)


if __name__ == "__main__":
    unittest.main()
