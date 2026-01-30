"""Tests for API error exceptions."""
import pytest

from api.core.errors import (
    APIError,
    InvalidRequestError,
    SessionNotFoundError,
    SessionStateError,
)


class TestAPIError:
    """Test cases for APIError base exception."""

    def test_construction_with_all_parameters(self):
        """Test constructing APIError with all parameters."""
        error = APIError(
            status_code=500,
            message="Internal server error",
            details={"trace_id": "abc123"}
        )

        assert error.status_code == 500
        assert error.message == "Internal server error"
        assert error.details == {"trace_id": "abc123"}

    def test_construction_without_details(self):
        """Test constructing APIError without details defaults to empty dict."""
        error = APIError(status_code=404, message="Not found")

        assert error.status_code == 404
        assert error.message == "Not found"
        assert error.details == {}

    def test_construction_with_none_details(self):
        """Test constructing APIError with None details defaults to empty dict."""
        error = APIError(status_code=404, message="Not found", details=None)

        assert error.details == {}

    def test_is_exception_subclass(self):
        """Test that APIError is an Exception subclass."""
        error = APIError(status_code=500, message="Error")

        assert isinstance(error, Exception)
        assert isinstance(error, APIError)

    def test_string_representation(self):
        """Test that exception string representation is the message."""
        error = APIError(status_code=404, message="Resource not found")

        assert str(error) == "Resource not found"
        assert repr(error) == "APIError('Resource not found')"

    def test_can_raise_and_catch(self):
        """Test that exception can be raised and caught."""
        with pytest.raises(APIError) as exc_info:
            raise APIError(status_code=400, message="Bad request")

        assert exc_info.value.status_code == 400
        assert exc_info.value.message == "Bad request"
        assert exc_info.value.details == {}

    def test_catch_as_base_exception(self):
        """Test that APIError can be caught as base Exception."""
        with pytest.raises(Exception) as exc_info:
            raise APIError(status_code=500, message="Server error")

        assert isinstance(exc_info.value, APIError)

    def test_details_mutation_does_not_affect_other_instances(self):
        """Test that details dict is independent per instance."""
        error1 = APIError(status_code=400, message="Error 1", details={"key": "value1"})
        error2 = APIError(status_code=400, message="Error 2", details={"key": "value2"})

        error1.details["key"] = "modified"
        error1.details["new_key"] = "new_value"

        assert error1.details == {"key": "modified", "new_key": "new_value"}
        assert error2.details == {"key": "value2"}

    def test_complex_details_structure(self):
        """Test APIError with complex nested details structure."""
        details = {
            "errors": [
                {"field": "email", "message": "Invalid email format"},
                {"field": "age", "message": "Must be positive"}
            ],
            "request_id": "req-123",
            "timestamp": "2024-01-01T00:00:00Z"
        }

        error = APIError(status_code=422, message="Validation failed", details=details)

        assert error.details == details
        assert len(error.details["errors"]) == 2


class TestSessionNotFoundError:
    """Test cases for SessionNotFoundError exception."""

    def test_construction_with_session_id(self):
        """Test constructing SessionNotFoundError with session_id."""
        error = SessionNotFoundError(session_id="session-abc-123")

        assert error.status_code == 404
        assert error.session_id == "session-abc-123"
        assert error.message == "Session 'session-abc-123' not found"
        assert error.details == {}

    def test_construction_with_details(self):
        """Test constructing SessionNotFoundError with details."""
        details = {"hint": "Session may have expired"}
        error = SessionNotFoundError(
            session_id="session-xyz-789",
            details=details
        )

        assert error.status_code == 404
        assert error.session_id == "session-xyz-789"
        assert error.details == details

    def test_message_formatting(self):
        """Test that session_id is properly formatted in message."""
        error1 = SessionNotFoundError(session_id="test-1")
        error2 = SessionNotFoundError(session_id="abc-def-ghi")

        assert error1.message == "Session 'test-1' not found"
        assert error2.message == "Session 'abc-def-ghi' not found"

    def test_inheritance_from_api_error(self):
        """Test that SessionNotFoundError is an APIError subclass."""
        error = SessionNotFoundError(session_id="session-123")

        assert isinstance(error, APIError)
        assert isinstance(error, Exception)

    def test_can_catch_as_api_error(self):
        """Test that SessionNotFoundError can be caught as APIError."""
        with pytest.raises(APIError) as exc_info:
            raise SessionNotFoundError(session_id="missing-session")

        assert exc_info.value.status_code == 404
        assert exc_info.value.session_id == "missing-session"

    def test_special_attributes(self):
        """Test that session_id attribute is accessible."""
        error = SessionNotFoundError(session_id="my-session-id")

        assert hasattr(error, "session_id")
        assert hasattr(error, "status_code")
        assert hasattr(error, "message")
        assert hasattr(error, "details")

    def test_empty_session_id(self):
        """Test SessionNotFoundError with empty session_id."""
        error = SessionNotFoundError(session_id="")

        assert error.message == "Session '' not found"
        assert error.session_id == ""

    def test_session_id_with_special_characters(self):
        """Test SessionNotFoundError with special characters in session_id."""
        error = SessionNotFoundError(session_id="session/with/slashes-and.dots")

        assert error.session_id == "session/with/slashes-and.dots"
        assert error.message == "Session 'session/with/slashes-and.dots' not found"


class TestSessionStateError:
    """Test cases for SessionStateError exception."""

    def test_construction_with_session_id_and_state(self):
        """Test constructing SessionStateError with session_id and state."""
        error = SessionStateError(
            session_id="session-123",
            state="completed"
        )

        assert error.status_code == 409
        assert error.session_id == "session-123"
        assert error.state == "completed"
        assert error.message == "Session 'session-123' is in invalid state 'completed' for this operation"
        assert error.details == {}

    def test_construction_with_details(self):
        """Test constructing SessionStateError with details."""
        details = {"current_state": "completed", "allowed_states": ["pending", "active"]}
        error = SessionStateError(
            session_id="session-456",
            state="completed",
            details=details
        )

        assert error.status_code == 409
        assert error.session_id == "session-456"
        assert error.state == "completed"
        assert error.details == details

    def test_message_formatting(self):
        """Test that session_id and state are properly formatted in message."""
        error1 = SessionStateError(session_id="s1", state="active")
        error2 = SessionStateError(session_id="s2", state="terminated")

        assert error1.message == "Session 's1' is in invalid state 'active' for this operation"
        assert error2.message == "Session 's2' is in invalid state 'terminated' for this operation"

    def test_inheritance_from_api_error(self):
        """Test that SessionStateError is an APIError subclass."""
        error = SessionStateError(session_id="session-123", state="active")

        assert isinstance(error, APIError)
        assert isinstance(error, Exception)

    def test_can_catch_as_api_error(self):
        """Test that SessionStateError can be caught as APIError."""
        with pytest.raises(APIError) as exc_info:
            raise SessionStateError(session_id="session-789", state="locked")

        assert exc_info.value.status_code == 409
        assert exc_info.value.session_id == "session-789"
        assert exc_info.value.state == "locked"

    def test_special_attributes(self):
        """Test that session_id and state attributes are accessible."""
        error = SessionStateError(session_id="my-session", state="processing")

        assert hasattr(error, "session_id")
        assert hasattr(error, "state")
        assert hasattr(error, "status_code")
        assert hasattr(error, "message")
        assert hasattr(error, "details")

    def test_various_state_values(self):
        """Test SessionStateError with various state values."""
        states = ["pending", "active", "completed", "failed", "terminated"]

        for state in states:
            error = SessionStateError(session_id=f"session-{state}", state=state)
            assert error.state == state
            assert state in error.message

    def test_empty_session_id_and_state(self):
        """Test SessionStateError with empty session_id and state."""
        error = SessionStateError(session_id="", state="")

        assert error.session_id == ""
        assert error.state == ""
        assert error.message == "Session '' is in invalid state '' for this operation"


class TestInvalidRequestError:
    """Test cases for InvalidRequestError exception."""

    def test_construction_with_message(self):
        """Test constructing InvalidRequestError with message."""
        error = InvalidRequestError(message="Invalid input data")

        assert error.status_code == 400
        assert error.message == "Invalid input data"
        assert error.details == {}

    def test_construction_with_details(self):
        """Test constructing InvalidRequestError with details."""
        details = {"field": "email", "reason": "Invalid format"}
        error = InvalidRequestError(
            message="Validation failed",
            details=details
        )

        assert error.status_code == 400
        assert error.message == "Validation failed"
        assert error.details == details

    def test_inheritance_from_api_error(self):
        """Test that InvalidRequestError is an APIError subclass."""
        error = InvalidRequestError(message="Bad request")

        assert isinstance(error, APIError)
        assert isinstance(error, Exception)

    def test_can_catch_as_api_error(self):
        """Test that InvalidRequestError can be caught as APIError."""
        with pytest.raises(APIError) as exc_info:
            raise InvalidRequestError(message="Invalid request")

        assert exc_info.value.status_code == 400
        assert exc_info.value.message == "Invalid request"

    def test_status_code_always_400(self):
        """Test that InvalidRequestError always has status code 400."""
        errors = [
            InvalidRequestError(message="Error 1"),
            InvalidRequestError(message="Error 2", details={"key": "value"}),
        ]

        for error in errors:
            assert error.status_code == 400

    def test_message_variations(self):
        """Test InvalidRequestError with various message types."""
        messages = [
            "Missing required field",
            "Invalid JSON format",
            "Parameter out of range",
            "Authentication required"
        ]

        for message in messages:
            error = InvalidRequestError(message=message)
            assert error.message == message

    def test_complex_validation_details(self):
        """Test InvalidRequestError with validation error details."""
        details = {
            "validation_errors": {
                "email": ["Invalid format", "Already registered"],
                "password": ["Too short", "Missing uppercase letter"]
            },
            "fields_count": 2
        }

        error = InvalidRequestError(
            message="Multiple validation errors",
            details=details
        )

        assert error.details == details
        assert "validation_errors" in error.details


class TestExceptionHierarchy:
    """Test cases for exception hierarchy and polymorphism."""

    def test_all_exceptions_inherit_from_api_error(self):
        """Test that all custom exceptions inherit from APIError."""
        exceptions = [
            SessionNotFoundError(session_id="test"),
            SessionStateError(session_id="test", state="active"),
            InvalidRequestError(message="test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, APIError)

    def test_catch_all_errors_as_api_error(self):
        """Test catching all custom errors as APIError."""
        exceptions = [
            SessionNotFoundError(session_id="test"),
            SessionStateError(session_id="test", state="active"),
            InvalidRequestError(message="test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, APIError)

    def test_specific_exception_catch(self):
        """Test catching specific exceptions while letting others pass."""
        with pytest.raises(SessionNotFoundError):
            raise SessionNotFoundError(session_id="test")

        with pytest.raises(SessionStateError):
            raise SessionStateError(session_id="test", state="active")

        with pytest.raises(InvalidRequestError):
            raise InvalidRequestError(message="test")

    def test_exception_chain(self):
        """Test exception chaining behavior."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise SessionNotFoundError(session_id="test-123") from e
        except SessionNotFoundError as exc:
            assert exc.__cause__ is not None
            assert isinstance(exc.__cause__, ValueError)
            assert str(exc.__cause__) == "Original error"

    def test_polymorphic_status_code_access(self):
        """Test accessing status_code polymorphically across all exceptions."""
        errors = [
            APIError(status_code=418, message="Teapot"),
            SessionNotFoundError(session_id="test"),  # 404
            SessionStateError(session_id="test", state="active"),  # 409
            InvalidRequestError(message="test"),  # 400
        ]

        expected_codes = [418, 404, 409, 400]

        for error, expected_code in zip(errors, expected_codes):
            assert error.status_code == expected_code


class TestExceptionInRealWorldScenarios:
    """Test cases simulating real-world usage patterns."""

    def test_http_response_mapping(self):
        """Test that status codes map correctly to HTTP responses."""
        status_code_map = {
            SessionNotFoundError(session_id="test"): 404,
            SessionStateError(session_id="test", state="active"): 409,
            InvalidRequestError(message="test"): 400,
        }

        for error, expected_code in status_code_map.items():
            assert error.status_code == expected_code

    def test_error_logging_scenario(self):
        """Test extracting error information for logging purposes."""
        error = SessionNotFoundError(
            session_id="session-123",
            details={"user": "john", "timestamp": "2024-01-01"}
        )

        log_info = {
            "status_code": error.status_code,
            "message": error.message,
            "session_id": error.session_id,
            "details": error.details
        }

        assert log_info == {
            "status_code": 404,
            "message": "Session 'session-123' not found",
            "session_id": "session-123",
            "details": {"user": "john", "timestamp": "2024-01-01"}
        }

    def test_api_response_format(self):
        """Test formatting error for API response."""
        error = InvalidRequestError(
            message="Validation failed",
            details={"fields": ["email", "password"]}
        )

        response = {
            "error": {
                "code": error.status_code,
                "message": error.message,
                "details": error.details
            }
        }

        assert response == {
            "error": {
                "code": 400,
                "message": "Validation failed",
                "details": {"fields": ["email", "password"]}
            }
        }

    def test_retryable_error_detection(self):
        """Test detecting retryable vs non-retryable errors."""
        client_errors = [
            InvalidRequestError(message="Bad data"),
            SessionNotFoundError(session_id="missing"),
        ]

        server_errors = [
            APIError(status_code=503, message="Service unavailable"),
            APIError(status_code=500, message="Internal error"),
        ]

        for error in client_errors:
            assert 400 <= error.status_code < 500

        for error in server_errors:
            assert 500 <= error.status_code < 600
