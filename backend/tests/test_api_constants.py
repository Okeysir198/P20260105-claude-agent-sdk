"""Tests for API constants."""

import pytest

from api.constants import (
    ASK_USER_QUESTION_TIMEOUT,
    ErrorCode,
    EventType,
    FIRST_MESSAGE_TRUNCATE_LENGTH,
    MessageRole,
    WSCloseCode,
)


class TestEventType:
    """Test cases for EventType enum."""

    def test_session_id_value(self):
        """Test SESSION_ID has correct value."""
        assert EventType.SESSION_ID == "session_id"

    def test_text_delta_value(self):
        """Test TEXT_DELTA has correct value."""
        assert EventType.TEXT_DELTA == "text_delta"

    def test_tool_use_value(self):
        """Test TOOL_USE has correct value."""
        assert EventType.TOOL_USE == "tool_use"

    def test_tool_result_value(self):
        """Test TOOL_RESULT has correct value."""
        assert EventType.TOOL_RESULT == "tool_result"

    def test_done_value(self):
        """Test DONE has correct value."""
        assert EventType.DONE == "done"

    def test_error_value(self):
        """Test ERROR has correct value."""
        assert EventType.ERROR == "error"

    def test_ready_value(self):
        """Test READY has correct value."""
        assert EventType.READY == "ready"

    def test_ask_user_question_value(self):
        """Test ASK_USER_QUESTION has correct value."""
        assert EventType.ASK_USER_QUESTION == "ask_user_question"

    def test_user_answer_value(self):
        """Test USER_ANSWER has correct value."""
        assert EventType.USER_ANSWER == "user_answer"

    def test_plan_approval_value(self):
        """Test PLAN_APPROVAL has correct value."""
        assert EventType.PLAN_APPROVAL == "plan_approval"

    def test_plan_approval_response_value(self):
        """Test PLAN_APPROVAL_RESPONSE has correct value."""
        assert EventType.PLAN_APPROVAL_RESPONSE == "plan_approval_response"

    def test_auth_value(self):
        """Test AUTH has correct value."""
        assert EventType.AUTH == "auth"

    def test_authenticated_value(self):
        """Test AUTHENTICATED has correct value."""
        assert EventType.AUTHENTICATED == "authenticated"

    def test_enum_is_string_enum(self):
        """Test EventType values are strings."""
        for event in EventType:
            assert isinstance(event.value, str)

    def test_enum_equality(self):
        """Test enum equality."""
        assert EventType.TEXT_DELTA == EventType.TEXT_DELTA
        assert EventType.TEXT_DELTA == "text_delta"
        assert EventType.TEXT_DELTA != EventType.DONE

    def test_enum_membership(self):
        """Test enum membership."""
        assert EventType.TEXT_DELTA in EventType
        assert "text_delta" in EventType
        assert "unknown_event" not in EventType

    def test_all_event_types(self):
        """Test all expected event types exist."""
        expected_types = {
            "session_id",
            "text_delta",
            "tool_use",
            "tool_result",
            "done",
            "error",
            "ready",
            "ask_user_question",
            "user_answer",
            "plan_approval",
            "plan_approval_response",
            "auth",
            "authenticated",
        }
        actual_types = {event.value for event in EventType}
        assert actual_types == expected_types


class TestMessageRole:
    """Test cases for MessageRole enum."""

    def test_user_value(self):
        """Test USER has correct value."""
        assert MessageRole.USER == "user"

    def test_assistant_value(self):
        """Test ASSISTANT has correct value."""
        assert MessageRole.ASSISTANT == "assistant"

    def test_tool_use_value(self):
        """Test TOOL_USE has correct value."""
        assert MessageRole.TOOL_USE == "tool_use"

    def test_tool_result_value(self):
        """Test TOOL_RESULT has correct value."""
        assert MessageRole.TOOL_RESULT == "tool_result"

    def test_enum_is_string_enum(self):
        """Test MessageRole values are strings."""
        for role in MessageRole:
            assert isinstance(role.value, str)

    def test_enum_equality(self):
        """Test enum equality."""
        assert MessageRole.USER == MessageRole.USER
        assert MessageRole.USER == "user"
        assert MessageRole.USER != MessageRole.ASSISTANT

    def test_enum_membership(self):
        """Test enum membership."""
        assert MessageRole.USER in MessageRole
        assert "user" in MessageRole
        assert "unknown_role" not in MessageRole

    def test_all_message_roles(self):
        """Test all expected message roles exist."""
        expected_roles = {"user", "assistant", "tool_use", "tool_result"}
        actual_roles = {role.value for role in MessageRole}
        assert actual_roles == expected_roles


class TestErrorCode:
    """Test cases for ErrorCode enum."""

    def test_token_expired_value(self):
        """Test TOKEN_EXPIRED has correct value."""
        assert ErrorCode.TOKEN_EXPIRED == "TOKEN_EXPIRED"

    def test_token_invalid_value(self):
        """Test TOKEN_INVALID has correct value."""
        assert ErrorCode.TOKEN_INVALID == "TOKEN_INVALID"

    def test_session_not_found_value(self):
        """Test SESSION_NOT_FOUND has correct value."""
        assert ErrorCode.SESSION_NOT_FOUND == "SESSION_NOT_FOUND"

    def test_rate_limited_value(self):
        """Test RATE_LIMITED has correct value."""
        assert ErrorCode.RATE_LIMITED == "RATE_LIMITED"

    def test_agent_not_found_value(self):
        """Test AGENT_NOT_FOUND has correct value."""
        assert ErrorCode.AGENT_NOT_FOUND == "AGENT_NOT_FOUND"

    def test_unknown_value(self):
        """Test UNKNOWN has correct value."""
        assert ErrorCode.UNKNOWN == "UNKNOWN"

    def test_enum_is_string_enum(self):
        """Test ErrorCode values are strings."""
        for code in ErrorCode:
            assert isinstance(code.value, str)

    def test_enum_equality(self):
        """Test enum equality."""
        assert ErrorCode.TOKEN_EXPIRED == ErrorCode.TOKEN_EXPIRED
        assert ErrorCode.TOKEN_EXPIRED == "TOKEN_EXPIRED"
        assert ErrorCode.TOKEN_EXPIRED != ErrorCode.UNKNOWN

    def test_enum_membership(self):
        """Test enum membership."""
        assert ErrorCode.TOKEN_EXPIRED in ErrorCode
        assert "TOKEN_EXPIRED" in ErrorCode
        assert "UNKNOWN_CODE" not in ErrorCode

    def test_all_error_codes(self):
        """Test all expected error codes exist."""
        expected_codes = {
            "TOKEN_EXPIRED",
            "TOKEN_INVALID",
            "SESSION_NOT_FOUND",
            "RATE_LIMITED",
            "AGENT_NOT_FOUND",
            "UNKNOWN",
        }
        actual_codes = {code.value for code in ErrorCode}
        assert actual_codes == expected_codes


class TestWSCloseCode:
    """Test cases for WSCloseCode enum."""

    def test_auth_failed_value(self):
        """Test AUTH_FAILED has correct value."""
        assert WSCloseCode.AUTH_FAILED == 4001

    def test_sdk_connection_failed_value(self):
        """Test SDK_CONNECTION_FAILED has correct value."""
        assert WSCloseCode.SDK_CONNECTION_FAILED == 4002

    def test_token_expired_value(self):
        """Test TOKEN_EXPIRED has correct value."""
        assert WSCloseCode.TOKEN_EXPIRED == 4005

    def test_token_invalid_value(self):
        """Test TOKEN_INVALID has correct value."""
        assert WSCloseCode.TOKEN_INVALID == 4006

    def test_rate_limited_value(self):
        """Test RATE_LIMITED has correct value."""
        assert WSCloseCode.RATE_LIMITED == 4007

    def test_agent_not_found_value(self):
        """Test AGENT_NOT_FOUND has correct value."""
        assert WSCloseCode.AGENT_NOT_FOUND == 4008

    def test_session_not_found_value(self):
        """Test SESSION_NOT_FOUND has correct value."""
        assert WSCloseCode.SESSION_NOT_FOUND == 4004

    def test_enum_is_int_enum(self):
        """Test WSCloseCode values are integers."""
        for code in WSCloseCode:
            assert isinstance(code.value, int)

    def test_enum_equality(self):
        """Test enum equality."""
        assert WSCloseCode.AUTH_FAILED == WSCloseCode.AUTH_FAILED
        assert WSCloseCode.AUTH_FAILED == 4001
        assert WSCloseCode.AUTH_FAILED != WSCloseCode.SDK_CONNECTION_FAILED

    def test_enum_membership(self):
        """Test enum membership."""
        assert WSCloseCode.AUTH_FAILED in WSCloseCode
        assert 4001 in WSCloseCode
        assert 9999 not in WSCloseCode

    def test_all_codes_in_application_range(self):
        """Test all close codes are in application range (4000-4999)."""
        for code in WSCloseCode:
            assert 4000 <= code.value <= 4999

    def test_all_close_codes(self):
        """Test all expected close codes exist."""
        expected_codes = {
            4001,  # AUTH_FAILED
            4002,  # SDK_CONNECTION_FAILED
            4005,  # TOKEN_EXPIRED
            4006,  # TOKEN_INVALID
            4007,  # RATE_LIMITED
            4008,  # AGENT_NOT_FOUND
            4004,  # SESSION_NOT_FOUND
        }
        actual_codes = {code.value for code in WSCloseCode}
        assert actual_codes == expected_codes


class TestErrorCodeToWSCloseCodeMapping:
    """Test cases verifying ErrorCode maps to correct WSCloseCode."""

    def test_token_expired_mapping(self):
        """Test TOKEN_EXPIRED error code matches close code."""
        error_code = ErrorCode.TOKEN_EXPIRED.value
        close_code = WSCloseCode.TOKEN_EXPIRED.value
        assert error_code == "TOKEN_EXPIRED"
        assert close_code == 4005

    def test_token_invalid_mapping(self):
        """Test TOKEN_INVALID error code matches close code."""
        error_code = ErrorCode.TOKEN_INVALID.value
        close_code = WSCloseCode.TOKEN_INVALID.value
        assert error_code == "TOKEN_INVALID"
        assert close_code == 4006

    def test_session_not_found_mapping(self):
        """Test SESSION_NOT_FOUND error code matches close code."""
        error_code = ErrorCode.SESSION_NOT_FOUND.value
        close_code = WSCloseCode.SESSION_NOT_FOUND.value
        assert error_code == "SESSION_NOT_FOUND"
        assert close_code == 4004

    def test_rate_limited_mapping(self):
        """Test RATE_LIMITED error code matches close code."""
        error_code = ErrorCode.RATE_LIMITED.value
        close_code = WSCloseCode.RATE_LIMITED.value
        assert error_code == "RATE_LIMITED"
        assert close_code == 4007

    def test_agent_not_found_mapping(self):
        """Test AGENT_NOT_FOUND error code matches close code."""
        error_code = ErrorCode.AGENT_NOT_FOUND.value
        close_code = WSCloseCode.AGENT_NOT_FOUND.value
        assert error_code == "AGENT_NOT_FOUND"
        assert close_code == 4008


class TestConfigurationConstants:
    """Test cases for configuration constants."""

    def test_ask_user_question_timeout_value(self):
        """Test ASK_USER_QUESTION_TIMEOUT has correct value."""
        assert ASK_USER_QUESTION_TIMEOUT == 60

    def test_ask_user_question_timeout_is_int(self):
        """Test ASK_USER_QUESTION_TIMEOUT is an integer."""
        assert isinstance(ASK_USER_QUESTION_TIMEOUT, int)

    def test_ask_user_question_timeout_positive(self):
        """Test ASK_USER_QUESTION_TIMEOUT is positive."""
        assert ASK_USER_QUESTION_TIMEOUT > 0

    def test_first_message_truncate_length_value(self):
        """Test FIRST_MESSAGE_TRUNCATE_LENGTH has correct value."""
        assert FIRST_MESSAGE_TRUNCATE_LENGTH == 100

    def test_first_message_truncate_length_is_int(self):
        """Test FIRST_MESSAGE_TRUNCATE_LENGTH is an integer."""
        assert isinstance(FIRST_MESSAGE_TRUNCATE_LENGTH, int)

    def test_first_message_truncate_length_positive(self):
        """Test FIRST_MESSAGE_TRUNCATE_LENGTH is positive."""
        assert FIRST_MESSAGE_TRUNCATE_LENGTH > 0
