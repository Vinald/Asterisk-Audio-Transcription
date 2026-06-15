"""Pure unit tests — no HTTP, no DB, no external I/O."""

import os
import tempfile

import pytest

from app.api.dashboard._shared import _caller_colors


# ── _caller_colors ─────────────────────────────────────────────────────────────


class TestCallerColors:
    def test_empty_list_returns_empty_dict(self):
        assert _caller_colors([]) == {}

    def test_single_caller_gets_index_zero(self):
        result = _caller_colors(["256700000001"])
        assert result["256700000001"] == 0

    def test_two_callers_get_different_indices(self):
        result = _caller_colors(["A", "B"])
        assert result["A"] != result["B"]

    def test_indices_start_at_zero_and_increment(self):
        result = _caller_colors(["A", "B", "C"])
        assert result == {"A": 0, "B": 1, "C": 2}

    def test_duplicate_caller_keeps_first_index(self):
        result = _caller_colors(["A", "B", "A"])
        assert result["A"] == 0
        assert result["B"] == 1
        assert len(result) == 2

    def test_indices_wrap_at_eight(self):
        callers = [str(i) for i in range(9)]
        result = _caller_colors(callers)
        assert result["8"] == 0  # index 8 wraps back to 0

    def test_none_caller_id_mapped_to_unknown(self):
        result = _caller_colors([None])
        assert "unknown" in result

    def test_none_and_string_unknown_are_same_key(self):
        result = _caller_colors([None, "unknown"])
        assert len(result) == 1
        assert "unknown" in result

    def test_preserves_insertion_order(self):
        callers = ["X", "Y", "Z"]
        result = _caller_colors(callers)
        assert list(result.keys()) == ["X", "Y", "Z"]


# ── resolve_language ────────────────────────────────────────────────────────────


class TestResolveLanguage:
    """Test the 3-letter-code → full-name mapping used by ai_assistant.py."""

    def setup_method(self):
        # Import here to avoid triggering AGI env checks at module level
        from asterisk.ai_assistant import resolve_language
        self.resolve = resolve_language

    def test_eng_maps_to_english(self):
        assert self.resolve("eng") == "English"

    def test_lug_maps_to_luganda(self):
        assert self.resolve("lug") == "Luganda"

    def test_unknown_code_returned_as_is(self):
        assert self.resolve("xyz") == "xyz"

    def test_empty_string_returned_as_is(self):
        assert self.resolve("") == ""

    def test_all_known_codes_map_to_strings(self):
        from asterisk.ai_assistant import LANGUAGE_NAMES
        for code, name in LANGUAGE_NAMES.items():
            assert self.resolve(code) == name

    def test_case_sensitive(self):
        # Codes are lowercase; uppercase should not match
        assert self.resolve("ENG") == "ENG"


# ── settings.speaker_for ────────────────────────────────────────────────────────


class TestSpeakerFor:
    """speaker_for() must resolve both full names and language codes correctly.

    The Sunbird language-ID API returns full names ("Swahili", "Luganda") and
    the Asterisk dialplan also passes full names via ${LANGUAGE}. The speakers
    dict is keyed by ISO codes, so without this resolution every non-default
    language would silently fall back to speaker 248.
    """

    def setup_method(self):
        from app.core.config import settings
        self.speaker_for = settings.speaker_for

    def test_full_name_english_returns_248(self):
        assert self.speaker_for("English") == 248

    def test_full_name_luganda_returns_248(self):
        assert self.speaker_for("Luganda") == 248

    def test_full_name_acholi_returns_241(self):
        assert self.speaker_for("Acholi") == 241

    def test_full_name_ateso_returns_242(self):
        assert self.speaker_for("Ateso") == 242

    def test_full_name_runyankore_returns_243(self):
        assert self.speaker_for("Runyankore") == 243

    def test_full_name_lugbara_returns_245(self):
        assert self.speaker_for("Lugbara") == 245

    def test_full_name_swahili_returns_246(self):
        assert self.speaker_for("Swahili") == 246

    def test_code_eng_returns_248(self):
        assert self.speaker_for("eng") == 248

    def test_code_swa_returns_246(self):
        assert self.speaker_for("swa") == 246

    def test_unknown_language_returns_default_248(self):
        assert self.speaker_for("xyz") == 248

    def test_empty_string_returns_default_248(self):
        assert self.speaker_for("") == 248


# ── validate_audio ──────────────────────────────────────────────────────────────


class TestValidateAudio:
    def setup_method(self):
        from asterisk.ai_assistant import validate_audio
        self.validate = validate_audio

    def test_missing_path_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            self.validate("/nonexistent/path/audio.wav")

    def test_none_path_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            self.validate(None)

    def test_empty_string_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            self.validate("")

    def test_small_file_raises_value_error(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"x" * 500)  # below 1000-byte threshold
            path = f.name
        try:
            with pytest.raises(ValueError, match="too small"):
                self.validate(path)
        finally:
            os.unlink(path)

    def test_valid_file_passes(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"x" * 2000)  # above 1000-byte threshold
            path = f.name
        try:
            self.validate(path)  # should not raise
        finally:
            os.unlink(path)


# ── Call / CallMetrics DB round-trip ─────────────────────────────────────────


class TestCallRoundTrip:
    """Verify the two-step write pattern works with the SQLite test DB."""

    CALL_ID = "HASH-20260611-999999-9"

    def teardown_method(self):
        from app.core.database import SessionLocal
        from app.models import Call, CallMetrics
        db = SessionLocal()
        db.query(CallMetrics).filter(CallMetrics.call_id == self.CALL_ID).delete()
        db.query(Call).filter(Call.call_id == self.CALL_ID).delete()
        db.commit()
        db.close()

    def test_q1_inserts_row(self):
        from app.core.database import SessionLocal
        from app.models.call import Call
        db = SessionLocal()
        db.add(Call(
            call_id=self.CALL_ID,
            caller_id="256700000099",
            extension="8446",
            language="English",
            status="in_progress",
            q1_input_text="test question",
            q1_output_text="test answer",
            q1_detected_language="English",
        ))
        db.commit()
        row = db.query(Call).filter(Call.call_id == self.CALL_ID).first()
        db.close()
        assert row is not None
        assert row.q1_input_text == "test question"
        assert row.status == "in_progress"

    def test_q2_updates_existing_row(self):
        from app.core.database import SessionLocal
        from app.models.call import Call
        db = SessionLocal()
        db.add(Call(call_id=self.CALL_ID, q1_input_text="q1", q1_output_text="a1", q1_detected_language="English"))
        db.commit()
        row = db.query(Call).filter(Call.call_id == self.CALL_ID).first()
        row.q2_input_text = "q2"
        row.q2_output_text = "a2"
        row.q2_detected_language = "Luganda"
        row.status = "completed"
        db.commit()
        db.close()
        db = SessionLocal()
        row = db.query(Call).filter(Call.call_id == self.CALL_ID).first()
        db.close()
        assert row.q2_input_text == "q2"
        assert row.status == "completed"

    def test_metrics_inserts_row(self):
        from app.core.database import SessionLocal
        from app.models.call import Call
        from app.models.call_metrics import CallMetrics
        db = SessionLocal()
        db.add(Call(call_id=self.CALL_ID, q1_input_text="q", q1_output_text="a", q1_detected_language="English"))
        db.add(CallMetrics(call_id=self.CALL_ID, question_number=1, stt_duration=1.0, agent_duration=2.0, tts_duration=0.5, total_duration=3.5))
        db.commit()
        m = db.query(CallMetrics).filter(CallMetrics.call_id == self.CALL_ID, CallMetrics.question_number == 1).first()
        db.close()
        assert m is not None
        assert m.total_duration == pytest.approx(3.5)

    def test_metrics_none_values_stored_as_null(self):
        from app.core.database import SessionLocal
        from app.models.call import Call
        from app.models.call_metrics import CallMetrics
        db = SessionLocal()
        db.add(Call(call_id=self.CALL_ID, q1_input_text="q", q1_output_text="a", q1_detected_language="English"))
        db.add(CallMetrics(call_id=self.CALL_ID, question_number=1))
        db.commit()
        m = db.query(CallMetrics).filter(CallMetrics.call_id == self.CALL_ID).first()
        db.close()
        assert m.stt_duration is None
        assert m.total_duration is None
