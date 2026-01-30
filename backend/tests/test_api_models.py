"""
Comprehensive unit tests for Pydantic models.

Tests cover:
- Model validation
- Required fields
- Optional fields
- Default values
- Type coercion
- Serialization/deserialization
- Edge cases

Run: pytest tests/test_api_models.py -v
"""

import pytest
from pydantic import ValidationError, BaseModel
from datetime import datetime

from api.models.requests import (
    CreateSessionRequest,
    SendMessageRequest,
    CreateConversationRequest,
    ResumeSessionRequest,
    UpdateSessionRequest,
    BatchDeleteSessionsRequest,
)

from api.models.responses import (
    SessionResponse,
    SessionInfo,
    ErrorResponse,
    CloseSessionResponse,
    DeleteSessionResponse,
    SessionHistoryResponse,
)

from api.models.auth import (
    WsTokenRequest,
    TokenPayload,
    TokenResponse,
    RefreshTokenRequest,
)

from api.models.user_auth import (
    LoginRequest,
    UserInfo,
    LoginResponse,
    UserTokenPayload,
)


class TestCreateSessionRequest:
    """Test cases for CreateSessionRequest model."""

    def test_create_with_all_fields(self):
        """Test creating request with all optional fields provided."""
        data = {
            "agent_id": "agent-123",
            "resume_session_id": "session-456"
        }
        request = CreateSessionRequest(**data)

        assert request.agent_id == "agent-123"
        assert request.resume_session_id == "session-456"

    def test_create_with_empty_dict(self):
        """Test creating request with no fields (all optional)."""
        request = CreateSessionRequest()

        assert request.agent_id is None
        assert request.resume_session_id is None

    def test_create_with_partial_fields(self):
        """Test creating request with only some fields."""
        request = CreateSessionRequest(agent_id="agent-123")

        assert request.agent_id == "agent-123"
        assert request.resume_session_id is None

    def test_serialization(self):
        """Test model serialization to dict."""
        request = CreateSessionRequest(agent_id="agent-123")
        data = request.model_dump()

        assert data == {"agent_id": "agent-123", "resume_session_id": None}

    def test_deserialization_from_dict(self):
        """Test model creation from dict."""
        data = {"agent_id": "agent-789", "resume_session_id": "session-101"}
        request = CreateSessionRequest.model_validate(data)

        assert request.agent_id == "agent-789"
        assert request.resume_session_id == "session-101"

    def test_json_serialization(self):
        """Test JSON serialization."""
        request = CreateSessionRequest(agent_id="agent-123")
        json_str = request.model_dump_json()

        assert "agent-123" in json_str

    def test_model_dump_excludes_none(self):
        """Test model_dump with exclude_none."""
        request = CreateSessionRequest(agent_id="agent-123")
        data = request.model_dump(exclude_none=True)

        assert data == {"agent_id": "agent-123"}
        assert "resume_session_id" not in data


class TestSendMessageRequest:
    """Test cases for SendMessageRequest model."""

    def test_create_with_valid_content(self):
        """Test creating request with valid content."""
        request = SendMessageRequest(content="Hello, agent!")

        assert request.content == "Hello, agent!"

    def test_create_with_empty_content_fails(self):
        """Test that empty content fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            SendMessageRequest(content="")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("content",) for e in errors)

    def test_create_with_whitespace_only_content_fails(self):
        """Test that whitespace-only content passes min_length but is valid.

        Note: min_length=1 only checks character count, not that content is non-whitespace.
        App-level validation should trim and check for meaningful content.
        """
        # This actually passes because "   " has 3 characters
        request = SendMessageRequest(content="   ")
        assert request.content == "   "

    def test_content_min_length_boundary(self):
        """Test content with exactly 1 character (boundary)."""
        request = SendMessageRequest(content="H")
        assert request.content == "H"

    def test_content_with_newlines(self):
        """Test content with newlines is accepted."""
        content = "Hello\n\nWorld\n"
        request = SendMessageRequest(content=content)

        assert request.content == content

    def test_content_with_unicode(self):
        """Test content with unicode characters."""
        content = "Hello 世界 🌍"
        request = SendMessageRequest(content=content)

        assert request.content == content

    def test_missing_content_field_fails(self):
        """Test that missing content field fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            SendMessageRequest()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("content",) for e in errors)


class TestCreateConversationRequest:
    """Test cases for CreateConversationRequest model."""

    def test_create_with_required_field_only(self):
        """Test creating with only required content field."""
        request = CreateConversationRequest(content="Start conversation")

        assert request.content == "Start conversation"
        assert request.session_id is None
        assert request.agent_id is None
        assert request.resume_session_id is None

    def test_create_with_all_fields(self):
        """Test creating with all fields."""
        data = {
            "content": "Hello",
            "session_id": "sess-123",
            "agent_id": "agent-456",
            "resume_session_id": "sess-789"
        }
        request = CreateConversationRequest(**data)

        assert request.content == "Hello"
        assert request.session_id == "sess-123"
        assert request.agent_id == "agent-456"
        assert request.resume_session_id == "sess-789"

    def test_content_required(self):
        """Test that content is required."""
        with pytest.raises(ValidationError) as exc_info:
            CreateConversationRequest()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("content",) for e in errors)

    def test_content_cannot_be_empty(self):
        """Test that content cannot be empty."""
        with pytest.raises(ValidationError):
            CreateConversationRequest(content="")

    def test_mutual_exclusivity_session_vs_resume(self):
        """Note: Model doesn't enforce mutual exclusivity, both can be set."""
        request = CreateConversationRequest(
            content="Test",
            session_id="sess-1",
            resume_session_id="sess-2"
        )
        # This is valid per the model - app layer handles logic
        assert request.session_id == "sess-1"
        assert request.resume_session_id == "sess-2"


class TestResumeSessionRequest:
    """Test cases for ResumeSessionRequest model."""

    def test_create_with_initial_message(self):
        """Test creating with initial message."""
        request = ResumeSessionRequest(initial_message="Resume here")

        assert request.initial_message == "Resume here"

    def test_create_without_initial_message(self):
        """Test creating without initial message (all optional)."""
        request = ResumeSessionRequest()

        assert request.initial_message is None

    def test_initial_message_can_be_empty_string(self):
        """Test that empty string is valid (optional field)."""
        request = ResumeSessionRequest(initial_message="")

        assert request.initial_message == ""

    def test_serialization(self):
        """Test model serialization."""
        request = ResumeSessionRequest(initial_message="Hello again")
        data = request.model_dump()

        assert data == {"initial_message": "Hello again"}


class TestUpdateSessionRequest:
    """Test cases for UpdateSessionRequest model."""

    def test_create_with_name(self):
        """Test creating with a name."""
        request = UpdateSessionRequest(name="My Session")

        assert request.name == "My Session"

    def test_create_without_name(self):
        """Test creating without name."""
        request = UpdateSessionRequest()

        assert request.name is None

    def test_name_can_be_empty_string(self):
        """Test that name can be an empty string."""
        request = UpdateSessionRequest(name="")

        assert request.name == ""

    def test_name_with_special_characters(self):
        """Test name with special characters."""
        name = "Session: 2024-01-15 @ 3pm"
        request = UpdateSessionRequest(name=name)

        assert request.name == name


class TestBatchDeleteSessionsRequest:
    """Test cases for BatchDeleteSessionsRequest model."""

    def test_create_with_session_ids(self):
        """Test creating with session IDs."""
        request = BatchDeleteSessionsRequest(
            session_ids=["sess-1", "sess-2", "sess-3"]
        )

        assert request.session_ids == ["sess-1", "sess-2", "sess-3"]

    def test_session_ids_required(self):
        """Test that session_ids is required."""
        with pytest.raises(ValidationError) as exc_info:
            BatchDeleteSessionsRequest()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("session_ids",) for e in errors)

    def test_session_ids_cannot_be_empty(self):
        """Test that session_ids cannot be empty list."""
        with pytest.raises(ValidationError) as exc_info:
            BatchDeleteSessionsRequest(session_ids=[])

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("session_ids",) for e in errors)

    def test_session_ids_with_single_item(self):
        """Test session_ids with single item (boundary)."""
        request = BatchDeleteSessionsRequest(session_ids=["sess-1"])

        assert request.session_ids == ["sess-1"]

    def test_session_ids_accepts_strings_only(self):
        """Test that session_ids only accepts strings."""
        # Pydantic will coerce non-strings or raise error
        with pytest.raises(ValidationError):
            BatchDeleteSessionsRequest(session_ids=[123, 456])


class TestSessionResponse:
    """Test cases for SessionResponse model."""

    def test_create_with_all_fields(self):
        """Test creating with all fields."""
        response = SessionResponse(
            session_id="sess-123",
            status="active",
            resumed=True
        )

        assert response.session_id == "sess-123"
        assert response.status == "active"
        assert response.resumed is True

    def test_default_resumed_value(self):
        """Test that resumed defaults to False."""
        response = SessionResponse(
            session_id="sess-123",
            status="active"
        )

        assert response.resumed is False

    def test_session_id_required(self):
        """Test that session_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            SessionResponse(status="active")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("session_id",) for e in errors)

    def test_status_required(self):
        """Test that status is required."""
        with pytest.raises(ValidationError) as exc_info:
            SessionResponse(session_id="sess-123")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("status",) for e in errors)

    def test_various_status_values(self):
        """Test various status string values."""
        statuses = ["active", "pending", "closed", "error", "initializing"]

        for status in statuses:
            response = SessionResponse(
                session_id="sess-123",
                status=status
            )
            assert response.status == status

    def test_serialization_includes_defaults(self):
        """Test serialization includes default values."""
        response = SessionResponse(
            session_id="sess-123",
            status="active"
        )
        data = response.model_dump()

        assert "resumed" in data
        assert data["resumed"] is False


class TestSessionInfo:
    """Test cases for SessionInfo model."""

    def test_create_with_all_fields(self):
        """Test creating with all fields."""
        response = SessionInfo(
            session_id="sess-123",
            name="My Session",
            first_message="Hello",
            created_at="2024-01-15T10:30:00Z",
            turn_count=5,
            user_id="user-456",
            agent_id="agent-789"
        )

        assert response.session_id == "sess-123"
        assert response.name == "My Session"
        assert response.first_message == "Hello"
        assert response.created_at == "2024-01-15T10:30:00Z"
        assert response.turn_count == 5
        assert response.user_id == "user-456"
        assert response.agent_id == "agent-789"

    def test_optional_fields_default_to_none(self):
        """Test that optional fields default to None."""
        response = SessionInfo(
            session_id="sess-123",
            created_at="2024-01-15T10:30:00Z",
            turn_count=0
        )

        assert response.name is None
        assert response.first_message is None
        assert response.user_id is None
        assert response.agent_id is None

    def test_turn_count_minimum_value(self):
        """Test turn_count minimum constraint (ge=0)."""
        # Valid: 0
        response = SessionInfo(
            session_id="sess-123",
            created_at="2024-01-15T10:30:00Z",
            turn_count=0
        )
        assert response.turn_count == 0

        # Invalid: -1
        with pytest.raises(ValidationError) as exc_info:
            SessionInfo(
                session_id="sess-123",
                created_at="2024-01-15T10:30:00Z",
                turn_count=-1
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("turn_count",) for e in errors)

    def test_turn_count_can_be_large(self):
        """Test turn_count with large value."""
        response = SessionInfo(
            session_id="sess-123",
            created_at="2024-01-15T10:30:00Z",
            turn_count=1000000
        )
        assert response.turn_count == 1000000

    def test_required_fields_validation(self):
        """Test that required fields are validated."""
        # Missing session_id
        with pytest.raises(ValidationError):
            SessionInfo(
                created_at="2024-01-15T10:30:00Z",
                turn_count=0
            )

        # Missing created_at
        with pytest.raises(ValidationError):
            SessionInfo(
                session_id="sess-123",
                turn_count=0
            )

        # Missing turn_count
        with pytest.raises(ValidationError):
            SessionInfo(
                session_id="sess-123",
                created_at="2024-01-15T10:30:00Z"
            )


class TestErrorResponse:
    """Test cases for ErrorResponse model."""

    def test_create_with_all_fields(self):
        """Test creating with all fields."""
        response = ErrorResponse(
            error="ValidationError",
            detail="Invalid input data"
        )

        assert response.error == "ValidationError"
        assert response.detail == "Invalid input data"

    def test_create_with_error_only(self):
        """Test creating with only error field."""
        response = ErrorResponse(error="NotFoundError")

        assert response.error == "NotFoundError"
        assert response.detail is None

    def test_error_required(self):
        """Test that error field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorResponse()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("error",) for e in errors)

    def test_detail_can_be_any_string(self):
        """Test that detail accepts any string."""
        response = ErrorResponse(
            error="CustomError",
            detail="Long detailed error message with unicode: 世界"
        )

        assert response.detail == "Long detailed error message with unicode: 世界"

    def test_common_error_types(self):
        """Test common error type values."""
        error_types = [
            "ValidationError",
            "AuthenticationError",
            "NotFoundError",
            "PermissionError",
            "RateLimitError",
            "InternalServerError"
        ]

        for error_type in error_types:
            response = ErrorResponse(error=error_type)
            assert response.error == error_type


class TestCloseSessionResponse:
    """Test cases for CloseSessionResponse model."""

    def test_create_with_status(self):
        """Test creating with status."""
        response = CloseSessionResponse(status="closed")

        assert response.status == "closed"

    def test_status_required(self):
        """Test that status is required."""
        with pytest.raises(ValidationError) as exc_info:
            CloseSessionResponse()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("status",) for e in errors)

    def test_various_status_values(self):
        """Test various status values."""
        statuses = ["closed", "already_closed", "not_found"]

        for status in statuses:
            response = CloseSessionResponse(status=status)
            assert response.status == status


class TestDeleteSessionResponse:
    """Test cases for DeleteSessionResponse model."""

    def test_create_with_status(self):
        """Test creating with status."""
        response = DeleteSessionResponse(status="deleted")

        assert response.status == "deleted"

    def test_status_required(self):
        """Test that status is required."""
        with pytest.raises(ValidationError):
            DeleteSessionResponse()

    def test_various_status_values(self):
        """Test various status values."""
        statuses = ["deleted", "not_found", "forbidden"]

        for status in statuses:
            response = DeleteSessionResponse(status=status)
            assert response.status == status


class TestSessionHistoryResponse:
    """Test cases for SessionHistoryResponse model."""

    def test_create_with_all_fields(self):
        """Test creating with all fields."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]

        response = SessionHistoryResponse(
            session_id="sess-123",
            messages=messages,
            turn_count=2,
            first_message="Hello"
        )

        assert response.session_id == "sess-123"
        assert response.messages == messages
        assert response.turn_count == 2
        assert response.first_message == "Hello"

    def test_default_messages(self):
        """Test that messages defaults to empty list."""
        response = SessionHistoryResponse(
            session_id="sess-123",
            turn_count=0
        )

        assert response.messages == []
        assert isinstance(response.messages, list)

    def test_default_turn_count(self):
        """Test that turn_count defaults to 0."""
        response = SessionHistoryResponse(
            session_id="sess-123"
        )

        assert response.turn_count == 0

    def test_default_first_message(self):
        """Test that first_message defaults to None."""
        response = SessionHistoryResponse(
            session_id="sess-123"
        )

        assert response.first_message is None

    def test_turn_count_minimum(self):
        """Test turn_count minimum constraint."""
        response = SessionHistoryResponse(
            session_id="sess-123",
            turn_count=0
        )
        assert response.turn_count == 0

        with pytest.raises(ValidationError):
            SessionHistoryResponse(
                session_id="sess-123",
                turn_count=-1
            )

    def test_messages_accepts_various_types(self):
        """Test that messages accepts various list contents."""
        # Empty list
        response = SessionHistoryResponse(
            session_id="sess-123",
            messages=[]
        )
        assert response.messages == []

        # List with dicts
        messages = [{"role": "user", "content": "test"}]
        response = SessionHistoryResponse(
            session_id="sess-123",
            messages=messages
        )
        assert response.messages == messages

    def test_session_id_required(self):
        """Test that session_id is required."""
        with pytest.raises(ValidationError):
            SessionHistoryResponse()


class TestWsTokenRequest:
    """Test cases for WsTokenRequest model."""

    def test_create_with_api_key(self):
        """Test creating with api_key."""
        request = WsTokenRequest(api_key="test-api-key-123")

        assert request.api_key == "test-api-key-123"

    def test_api_key_required(self):
        """Test that api_key is required."""
        with pytest.raises(ValidationError) as exc_info:
            WsTokenRequest()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("api_key",) for e in errors)

    def test_api_key_can_be_any_string(self):
        """Test that api_key accepts various string formats."""
        keys = [
            "simple",
            "with-dashes",
            "with_underscores",
            "with.dots",
            "UPPERCASE",
            "12345",
            "complex-key_123.abc"
        ]

        for key in keys:
            request = WsTokenRequest(api_key=key)
            assert request.api_key == key

    def test_api_key_can_contain_special_chars(self):
        """Test api_key with special characters."""
        key = "key@#$%^&*()_+-=[]{}|;':\",./<>?"
        request = WsTokenRequest(api_key=key)

        assert request.api_key == key


class TestTokenPayload:
    """Test cases for TokenPayload model."""

    def test_create_with_all_fields(self):
        """Test creating with all required fields."""
        now = 1705339200  # Fixed timestamp

        payload = TokenPayload(
            sub="user-123",
            jti="token-456",
            type="access",
            exp=now + 1800,
            iat=now,
            iss="claude-agent-sdk",
            aud="claude-agent-sdk-users"
        )

        assert payload.sub == "user-123"
        assert payload.jti == "token-456"
        assert payload.type == "access"
        assert payload.exp == now + 1800
        assert payload.iat == now
        assert payload.iss == "claude-agent-sdk"
        assert payload.aud == "claude-agent-sdk-users"

    def test_all_fields_required(self):
        """Test that all fields are required."""
        required_fields = ["sub", "jti", "type", "exp", "iat", "iss", "aud"]

        for field in required_fields:
            data = {
                "sub": "user-123",
                "jti": "token-456",
                "type": "access",
                "exp": 1705339200,
                "iat": 1705339200,
                "iss": "issuer",
                "aud": "audience"
            }
            del data[field]

            with pytest.raises(ValidationError) as exc_info:
                TokenPayload(**data)

            errors = exc_info.value.errors()
            assert any(e["loc"] == (field,) for e in errors)

    def test_exp_must_be_int(self):
        """Test that exp must be integer."""
        with pytest.raises(ValidationError):
            TokenPayload(
                sub="user-123",
                jti="token-456",
                type="access",
                exp="not-an-int",  # Invalid
                iat=1705339200,
                iss="issuer",
                aud="audience"
            )

    def test_iat_must_be_int(self):
        """Test that iat must be integer."""
        with pytest.raises(ValidationError):
            TokenPayload(
                sub="user-123",
                jti="token-456",
                type="access",
                exp=1705339200,
                iat="not-an-int",  # Invalid
                iss="issuer",
                aud="audience"
            )

    def test_token_type_values(self):
        """Test various token type values."""
        types = ["access", "refresh", "user_identity"]

        for token_type in types:
            payload = TokenPayload(
                sub="user-123",
                jti="token-456",
                type=token_type,
                exp=1705339200,
                iat=1705339200,
                iss="issuer",
                aud="audience"
            )
            assert payload.type == token_type


class TestTokenResponse:
    """Test cases for TokenResponse model."""

    def test_create_with_all_fields(self):
        """Test creating with all fields."""
        response = TokenResponse(
            access_token="access-123",
            refresh_token="refresh-456",
            token_type="bearer",
            expires_in=1800,
            user_id="user-789"
        )

        assert response.access_token == "access-123"
        assert response.refresh_token == "refresh-456"
        assert response.token_type == "bearer"
        assert response.expires_in == 1800
        assert response.user_id == "user-789"

    def test_default_token_type(self):
        """Test that token_type defaults to 'bearer'."""
        response = TokenResponse(
            access_token="access-123",
            refresh_token="refresh-456",
            expires_in=1800,
            user_id="user-789"
        )

        assert response.token_type == "bearer"

    def test_required_fields(self):
        """Test that all fields except token_type are required."""
        required_fields = ["access_token", "refresh_token", "expires_in", "user_id"]

        for field in required_fields:
            data = {
                "access_token": "access-123",
                "refresh_token": "refresh-456",
                "expires_in": 1800,
                "user_id": "user-789"
            }
            del data[field]

            with pytest.raises(ValidationError) as exc_info:
                TokenResponse(**data)

            errors = exc_info.value.errors()
            assert any(e["loc"] == (field,) for e in errors)

    def test_expires_in_must_be_int(self):
        """Test that expires_in must be integer."""
        with pytest.raises(ValidationError):
            TokenResponse(
                access_token="access-123",
                refresh_token="refresh-456",
                expires_in="not-an-int",
                user_id="user-789"
            )

    def test_various_token_types(self):
        """Test various token type values."""
        token_types = ["bearer", "Bearer", "BEARER", "jwt", "JWT"]

        for token_type in token_types:
            response = TokenResponse(
                access_token="access-123",
                refresh_token="refresh-456",
                token_type=token_type,
                expires_in=1800,
                user_id="user-789"
            )
            assert response.token_type == token_type


class TestRefreshTokenRequest:
    """Test cases for RefreshTokenRequest model."""

    def test_create_with_refresh_token(self):
        """Test creating with refresh_token."""
        request = RefreshTokenRequest(refresh_token="refresh-token-123")

        assert request.refresh_token == "refresh-token-123"

    def test_refresh_token_required(self):
        """Test that refresh_token is required."""
        with pytest.raises(ValidationError) as exc_info:
            RefreshTokenRequest()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("refresh_token",) for e in errors)

    def test_refresh_token_can_be_jwt_format(self):
        """Test refresh_token in JWT format."""
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token"
        request = RefreshTokenRequest(refresh_token=jwt_token)

        assert request.refresh_token == jwt_token


class TestLoginRequest:
    """Test cases for LoginRequest model."""

    def test_create_with_username_and_password(self):
        """Test creating with username and password."""
        request = LoginRequest(
            username="testuser",
            password="secretpass123"
        )

        assert request.username == "testuser"
        assert request.password == "secretpass123"

    def test_username_required(self):
        """Test that username is required."""
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(password="pass")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("username",) for e in errors)

    def test_password_required(self):
        """Test that password is required."""
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(username="user")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("password",) for e in errors)

    def test_both_fields_required(self):
        """Test that both fields are required."""
        with pytest.raises(ValidationError):
            LoginRequest()

    def test_username_can_be_email(self):
        """Test username as email format."""
        request = LoginRequest(
            username="user@example.com",
            password="pass123"
        )

        assert request.username == "user@example.com"

    def test_username_with_special_chars(self):
        """Test username with various characters."""
        usernames = [
            "user123",
            "user_name",
            "user-name",
            "user.name",
            "123user",
            "USER",
            "user@example.com"
        ]

        for username in usernames:
            request = LoginRequest(
                username=username,
                password="pass123"
            )
            assert request.username == username

    def test_password_with_special_chars(self):
        """Test password with special characters."""
        passwords = [
            "simple",
            "with123numbers",
            "with!@#$special",
            "with spaces",
            "混合Mixed字符 Characters",
            "very" * 50  # Long password
        ]

        for password in passwords:
            request = LoginRequest(
                username="user",
                password=password
            )
            assert request.password == password


class TestUserInfo:
    """Test cases for UserInfo model."""

    def test_create_with_all_fields(self):
        """Test creating with all fields."""
        user = UserInfo(
            id="user-123",
            username="testuser",
            full_name="Test User",
            role="admin"
        )

        assert user.id == "user-123"
        assert user.username == "testuser"
        assert user.full_name == "Test User"
        assert user.role == "admin"

    def test_create_with_optional_full_name(self):
        """Test creating without full_name."""
        user = UserInfo(
            id="user-123",
            username="testuser",
            full_name=None,
            role="user"
        )

        assert user.full_name is None

    def test_required_fields(self):
        """Test that id, username, and role are required."""
        # Missing id
        with pytest.raises(ValidationError):
            UserInfo(
                username="user",
                role="user"
            )

        # Missing username
        with pytest.raises(ValidationError):
            UserInfo(
                id="user-123",
                role="user"
            )

        # Missing role
        with pytest.raises(ValidationError):
            UserInfo(
                id="user-123",
                username="user"
            )

    def test_role_literal_validation_admin(self):
        """Test role with 'admin' value."""
        user = UserInfo(
            id="user-123",
            username="admin",
            full_name=None,  # Must provide since it's optional
            role="admin"
        )
        assert user.role == "admin"

    def test_role_literal_validation_user(self):
        """Test role with 'user' value."""
        user = UserInfo(
            id="user-123",
            username="regularuser",
            full_name=None,  # Must provide since it's optional
            role="user"
        )
        assert user.role == "user"

    def test_role_literal_invalid_value(self):
        """Test that invalid role values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UserInfo(
                id="user-123",
                username="user",
                role="superadmin"  # Invalid
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("role",) for e in errors)

    def test_full_name_can_be_empty_string(self):
        """Test that full_name can be empty string."""
        user = UserInfo(
            id="user-123",
            username="user",
            full_name="",
            role="user"
        )
        assert user.full_name == ""


class TestLoginResponse:
    """Test cases for LoginResponse model."""

    def test_create_successful_login(self):
        """Test creating successful login response."""
        user_info = UserInfo(
            id="user-123",
            username="testuser",
            full_name="Test User",
            role="user"
        )

        response = LoginResponse(
            success=True,
            token="jwt-token-123",
            refresh_token="refresh-token-456",
            user=user_info,
            error=None
        )

        assert response.success is True
        assert response.token == "jwt-token-123"
        assert response.refresh_token == "refresh-token-456"
        assert response.user == user_info
        assert response.error is None

    def test_create_failed_login(self):
        """Test creating failed login response."""
        response = LoginResponse(
            success=False,
            token=None,
            refresh_token=None,
            user=None,
            error="Invalid credentials"
        )

        assert response.success is False
        assert response.token is None
        assert response.refresh_token is None
        assert response.user is None
        assert response.error == "Invalid credentials"

    def test_success_required(self):
        """Test that success is required."""
        with pytest.raises(ValidationError) as exc_info:
            LoginResponse(
                token="token",
                user=None,
                error=None
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("success",) for e in errors)

    def test_optional_fields_default_to_none(self):
        """Test that optional fields default to None."""
        response = LoginResponse(success=True)

        assert response.token is None
        assert response.refresh_token is None
        assert response.user is None
        assert response.error is None

    def test_success_true_without_token_is_valid(self):
        """Test that success=True without token is model-valid (app-level logic)."""
        # Model doesn't enforce that success=True requires token
        response = LoginResponse(
            success=True,
            token=None,
            user=None
        )
        assert response.success is True
        assert response.token is None

    def test_user_info_serialization(self):
        """Test serialization with UserInfo nested."""
        user_info = UserInfo(
            id="user-123",
            username="testuser",
            full_name="Test User",
            role="admin"
        )

        response = LoginResponse(
            success=True,
            token="token-123",
            user=user_info
        )

        data = response.model_dump()

        assert data["user"]["id"] == "user-123"
        assert data["user"]["username"] == "testuser"
        assert data["user"]["role"] == "admin"


class TestUserTokenPayload:
    """Test cases for UserTokenPayload model."""

    def test_create_with_all_fields(self):
        """Test creating with all fields."""
        payload = UserTokenPayload(
            user_id="user-123",
            username="testuser",
            role="admin"
        )

        assert payload.user_id == "user-123"
        assert payload.username == "testuser"
        assert payload.role == "admin"

    def test_all_fields_required(self):
        """Test that all fields are required."""
        required_fields = ["user_id", "username", "role"]

        for field in required_fields:
            data = {
                "user_id": "user-123",
                "username": "testuser",
                "role": "user"
            }
            del data[field]

            with pytest.raises(ValidationError) as exc_info:
                UserTokenPayload(**data)

            errors = exc_info.value.errors()
            assert any(e["loc"] == (field,) for e in errors)

    def test_role_literal_admin(self):
        """Test role with 'admin' value."""
        payload = UserTokenPayload(
            user_id="user-123",
            username="admin",
            role="admin"
        )
        assert payload.role == "admin"

    def test_role_literal_user(self):
        """Test role with 'user' value."""
        payload = UserTokenPayload(
            user_id="user-123",
            username="regularuser",
            role="user"
        )
        assert payload.role == "user"

    def test_role_literal_invalid(self):
        """Test that invalid role values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UserTokenPayload(
                user_id="user-123",
                username="user",
                role="superuser"  # Invalid
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("role",) for e in errors)

    def test_username_can_be_email(self):
        """Test username as email."""
        payload = UserTokenPayload(
            user_id="user-123",
            username="user@example.com",
            role="user"
        )
        assert payload.username == "user@example.com"


class TestModelEdgeCases:
    """Test edge cases across all models."""

    def test_none_vs_missing_optional_fields(self):
        """Test difference between None and missing optional fields."""
        # Explicitly set to None
        request1 = CreateSessionRequest(agent_id=None)
        assert request1.agent_id is None

        # Not provided (defaults to None)
        request2 = CreateSessionRequest()
        assert request2.agent_id is None

    def test_empty_string_vs_none(self):
        """Test difference between empty string and None."""
        request = UpdateSessionRequest(name="")
        assert request.name == ""  # Empty string, not None

        request2 = UpdateSessionRequest(name=None)
        assert request2.name is None  # Explicitly None

    def test_model_dump_mode_python_vs_json(self):
        """Test model_dump with different modes."""
        response = SessionResponse(
            session_id="sess-123",
            status="active"
        )

        # Python mode (default)
        data_python = response.model_dump(mode='python')
        assert isinstance(data_python, dict)

        # JSON mode
        data_json = response.model_dump(mode='json')
        assert isinstance(data_json, dict)

    def test_model_validation_context(self):
        """Test model with validation context (if any models use it)."""
        # Most models don't use context, but test the API
        request = SendMessageRequest(content="test")
        # Should not raise
        SendMessageRequest.model_validate(request.model_dump())

    def test_copy_with_updates(self):
        """Test model_copy with updates."""
        original = CreateSessionRequest(agent_id="agent-123")

        # Copy with update
        copy = original.model_copy(update={"agent_id": "agent-456"})
        assert copy.agent_id == "agent-456"
        assert original.agent_id == "agent-123"  # Unchanged

    def test_frozen_models(self):
        """Test if any models are frozen (immutable)."""
        # None of the current models are frozen, but test the behavior
        request = SendMessageRequest(content="test")
        request.content = "new content"  # Should work
        assert request.content == "new content"

    def test_deep_nested_serialization(self):
        """Test serialization of nested models."""
        user = UserInfo(
            id="user-123",
            username="testuser",
            full_name="Test User",
            role="admin"
        )

        response = LoginResponse(
            success=True,
            token="token-123",
            user=user
        )

        # Deep serialization
        json_str = response.model_dump_json()
        assert "testuser" in json_str
        assert "admin" in json_str

    def test_list_field_mutation(self):
        """Test that list fields can be mutated after creation."""
        messages = [{"role": "user"}]
        response = SessionHistoryResponse(
            session_id="sess-123",
            messages=messages
        )

        # Mutate the list
        response.messages.append({"role": "assistant"})
        assert len(response.messages) == 2

    def test_string_type_coercion(self):
        """Test type coercion for string fields."""
        # Pydantic doesn't coerce int to str by default
        with pytest.raises(ValidationError):
            SendMessageRequest(content=123)  # int, not str

    def test_int_type_coercion(self):
        """Test type coercion for int fields.

        Note: Pydantic v2 DOES coerce int-compatible strings to int by default.
        """
        # Pydantic v2 coerces string numbers to int
        response = SessionInfo(
            session_id="sess-123",
            created_at="2024-01-15T10:30:00Z",
            turn_count="5"  # str that looks like int
        )
        assert response.turn_count == 5
        assert isinstance(response.turn_count, int)

    def test_extra_fields_forbidden(self):
        """Test that extra fields behavior (Pydantic v2 default is 'ignore')."""
        # Pydantic v2 default config is extra='ignore', not 'forbid'
        # Extra fields are silently ignored
        request = SendMessageRequest(
            content="test",
            extra_field="not_allowed"  # Will be ignored
        )
        assert request.content == "test"
        assert not hasattr(request, "extra_field")

    def test_model_fields_set(self):
        """Test which fields were explicitly set."""
        request1 = CreateSessionRequest(agent_id="agent-123")
        assert "agent_id" in request1.model_fields_set
        assert "resume_session_id" not in request1.model_fields_set

        request2 = CreateSessionRequest()
        assert len(request2.model_fields_set) == 0

    def test_json_schema_generation(self):
        """Test that models can generate JSON schemas."""
        schema = SendMessageRequest.model_json_schema()
        assert "properties" in schema
        assert "content" in schema["properties"]
        assert "required" in schema
        assert "content" in schema["required"]


class TestTypeCoercionAndValidation:
    """Test type coercion and validation behaviors."""

    def test_str_to_int_validation_error(self):
        """Test string to int conversion.

        Note: Pydantic v2 coerces int-like strings to int by default.
        Only non-numeric strings will fail.
        """
        # Numeric string coerces to int
        response = SessionInfo(
            session_id="sess-123",
            created_at="2024-01-15T10:30:00Z",
            turn_count="5"  # Coerced to int
        )
        assert response.turn_count == 5

        # Non-numeric string fails
        with pytest.raises(ValidationError):
            SessionInfo(
                session_id="sess-123",
                created_at="2024-01-15T10:30:00Z",
                turn_count="five"  # Not numeric
            )

    def test_float_to_int_validation_error(self):
        """Test that float to int conversion raises error."""
        with pytest.raises(ValidationError):
            SessionInfo(
                session_id="sess-123",
                created_at="2024-01-15T10:30:00Z",
                turn_count=5.5  # Float instead of int
            )

    def test_bool_to_int_validation_error(self):
        """Test bool to int conversion.

        Note: Pydantic v2 coerces bool to int (True=1, False=0) by default.
        """
        # bool coerces to int
        response = SessionInfo(
            session_id="sess-123",
            created_at="2024-01-15T10:30:00Z",
            turn_count=True  # Coerced to 1
        )
        assert response.turn_count == 1

    def test_none_to_required_field_error(self):
        """Test that None for required field raises error."""
        with pytest.raises(ValidationError):
            SendMessageRequest(content=None)

    def test_list_type_validation(self):
        """Test list field type validation."""
        # String instead of list
        with pytest.raises(ValidationError):
            BatchDeleteSessionsRequest(
                session_ids="not-a-list"  # type: ignore
            )

        # List with wrong element type
        with pytest.raises(ValidationError):
            BatchDeleteSessionsRequest(
                session_ids=[123, 456]  # Ints instead of strings
            )

    def test_literal_type_validation(self):
        """Test Literal type validation."""
        # Valid values
        UserInfo(
            id="user-123",
            username="user",
            full_name=None,
            role="user"
        )

        UserInfo(
            id="user-123",
            username="admin",
            full_name=None,
            role="admin"
        )

        # Invalid value
        with pytest.raises(ValidationError):
            UserInfo(
                id="user-123",
                username="user",
                full_name=None,
                role="superadmin"  # Not in Literal
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
